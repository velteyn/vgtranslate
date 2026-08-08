"""RetroArch-compatible HTTP server (FastAPI + uvicorn).

Implements the libretro AI Service wire protocol on localhost:4404:

* ``POST /`` (or any path) — translate a paused-game screenshot. Query params
  carry ``source_lang``, ``target_lang``, ``output`` (comma-separated formats
  plus sub-formats, e.g. ``image,png,png-a``, ``text``, or ``sound,wav``); the
  body (urlencoded form or JSON) carries ``image`` (base64), ``format``,
  ``coords``, ``viewport``, ``label``, ``state``.
* ``GET /health`` / ``GET /status`` — server state and engine availability for
  the tray app.

Responses are JSON. ``output=image`` returns a 24-bit BGR BMP overlay at native
resolution; ``output=text`` returns ``text`` + ``text_position``; ``output=both``
returns both. An optional ``press: ["unpause"]`` is appended when
``auto_unpause`` is enabled and the game reports itself paused.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from PIL import Image

from .config import Config
from .imaging import OverlayRenderer, encode_frame, load_frame, render_overlay
from .mt import list_providers as list_mt_providers
from .ocr import list_providers as list_ocr_providers
from .pipeline import Pipeline

log = logging.getLogger("vgtranslate.server")

VALID_OUTPUTS = ("image", "text", "sound", "both")
IMAGE_FORMATS = ("bmp", "png", "png-a")
SOUND_FORMATS = ("wav",)
DEFAULT_OUTPUT = "image"


class ClientError(Exception):
    """A request error with a safe, user-facing message.

    The message is set explicitly at the raise site and never derived from the
    exception's string form or traceback, so it can be returned to the client
    without leaking internal details.
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def create_app(config: Config) -> FastAPI:
    app = FastAPI(title="vgtranslate", version="2.0.0", docs_url=None, redoc_url=None)
    app.state.config = config
    app.state.pipeline = Pipeline(config)
    app.state.renderer = OverlayRenderer()

    @app.get("/health")
    @app.get("/status")
    async def status():
        llm = config.llm
        profile = config.active()
        return {
            "running": True,
            "server": config.server.to_dict(),
            "active_profile": config.active_profile,
            "profile": profile.to_dict(),
            "llm": {"base_url": llm.base_url, "model": llm.model},
            "ocr": list_ocr_providers(),
            "translators": list_mt_providers(),
        }

    @app.api_route("/{path:path}", methods=["POST"])
    async def service(path: str, request: Request):
        params = await _collect_params(request)
        try:
            result = _handle_service(app.state, params)
        except ClientError as exc:
            return JSONResponse(
                {"status": "error", "error": exc.message, "message": exc.message},
                status_code=400,
            )
        except Exception:  # noqa: BLE001
            log.exception("service request failed")
            return JSONResponse(
                {"status": "error", "message": "internal server error"}, status_code=500
            )
        return JSONResponse(result)

    return app


def _json_dict(raw: bytes) -> Optional[dict]:
    """Parse ``raw`` as a JSON object, or return None when it isn't one."""
    try:
        body = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return body if isinstance(body, dict) else None


async def _collect_params(request: Request) -> dict:
    params = {k: v for k, v in request.query_params.items()}
    content_type = request.headers.get("content-type", "").lower()
    try:
        if "application/json" in content_type:
            body = await request.json()
            if isinstance(body, dict):
                params.update({str(k): v for k, v in body.items()})
        elif content_type.startswith("multipart/form-data"):
            form = await _request_form(request)
            params.update({str(k): v for k, v in form.items()})
        else:
            # RetroArch posts its JSON payload with Content-Type
            # application/x-www-form-urlencoded (libretro's net_http.c sets
            # that for any POST without an explicit type). Try JSON first,
            # then a plain form parse, then treat the body as the image.
            raw = await request.body()
            body = _json_dict(raw)
            if body is not None:
                params.update({str(k): v for k, v in body.items()})
            elif content_type.startswith("application/x-www-form-urlencoded"):
                form = await _request_form(request)
                params.update({str(k): v for k, v in form.items()})
            elif raw:
                params["image"] = raw.decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        raw = await request.body()
        body = _json_dict(raw) if raw else None
        if body is not None:
            params.update({str(k): v for k, v in body.items()})
        elif raw:
            params["image"] = raw.decode("utf-8", errors="ignore")
    return params


async def _request_form(request: Request):
    """Parse a form body, tolerating a large frame part.

    Starlette >=0.37.2 supports ``max_part_size``; without it, base64 frames
    sent as urlencoded/multipart forms are truncated at the default 1 MB part
    limit. On older Starlette versions fall back to the default limit instead
    of crashing on the unexpected keyword.
    """
    try:
        return await request.form(max_part_size=100 * 1024 * 1024)
    except TypeError:
        return await request.form()


def _parse_output(value: str) -> set[str]:
    """Parse RetroArch's comma-separated ``output`` query parameter.

    RetroArch appends formats together with their sub-formats, e.g.
    ``image,png,png-a`` for image mode, ``text`` for text mode, or
    ``sound,wav,image,png,png-a`` for image + speech. Returns the requested
    top-level formats. Image sub-formats are validated but not honored yet
    (the server always returns a ``bmp`` overlay, which the spec permits as
    the default).
    """
    requested: set[str] = set()
    for token in value.split(","):
        token = token.strip().lower()
        if not token:
            continue
        if token == "both":
            requested.update(("image", "text"))
        elif token in VALID_OUTPUTS:
            requested.add(token)
        elif token in IMAGE_FORMATS or token in SOUND_FORMATS:
            requested.add("image" if token in IMAGE_FORMATS else "sound")
        else:
            raise ClientError(
                f"'output' must be a comma-separated list of formats, got '{value}'"
            )
    if not requested:
        raise ClientError(f"no known format in 'output' value '{value}'")
    return requested


def _handle_service(state, params: dict) -> dict:
    config: Config = state.config
    pipeline: Pipeline = state.pipeline
    renderer: OverlayRenderer = state.renderer

    image_data = _as_str(params.get("image"))
    if not image_data:
        raise ClientError("missing 'image' parameter")

    source_lang = _as_str(params.get("source_lang")) or config.active().source_lang
    target_lang = (
        _as_str(params.get("target_lang")) or config.active().target_lang
        or config.server.default_target
    )
    output = _as_str(params.get("output")) or DEFAULT_OUTPUT
    requested = _parse_output(output)

    if "sound" in requested and not ("image" in requested or "text" in requested):
        raise ClientError("sound output is not supported; use image or text mode")

    frame = load_frame(image_data)
    blocks = pipeline.translate_frame(frame, source_lang, target_lang)
    blocks = [b for b in blocks if b.translation]

    response: dict = {"status": "success", "target_lang": target_lang}

    if "text" in requested and blocks:
        response["text"] = "\n".join(b.translation for b in blocks)
        first = blocks[0].box
        response["text_position"] = [first.x, first.y, first.w, first.h]
        response["text_encoding"] = "utf-8"

    if "image" in requested:
        overlay = render_overlay(
            frame, blocks, scale=max(1, config.active().overlay_scale), renderer=renderer
        )
        response["image"] = encode_frame(overlay, fmt="bmp")
        response["image_width"] = overlay.width
        response["image_height"] = overlay.height
        response["image_format"] = "bmp"
        response["image_encoding"] = "base64"

    if config.server.auto_unpause and _is_paused(params):
        response["press"] = ["unpause"]

    if not any(k in response for k in ("image", "text", "sound", "press")):
        response["error"] = "No text found."

    return response


def _is_paused(params: dict) -> bool:
    state = params.get("state")
    if not state:
        return False
    if isinstance(state, dict):
        return bool(state.get("paused", False))
    try:
        data = json.loads(state)
        return bool(data.get("paused", False))
    except (ValueError, TypeError):
        return False


def _as_str(value) -> Optional[str]:
    if value is None:
        return None
    return str(value)


class Server:
    """Runs the FastAPI app in a background uvicorn thread."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.app = create_app(config)
        self._uvicorn = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.running:
            return
        import uvicorn

        config = self.config.server
        self._uvicorn = uvicorn.Server(
            uvicorn.Config(
                self.app,
                host=config.host,
                port=config.port,
                log_level="info",
                access_log=True,
            )
        )
        self._thread = threading.Thread(target=self._uvicorn.run, name="vgtranslate-http", daemon=True)
        self._thread.start()
        log.info("server starting on http://%s:%s", config.host, config.port)

    def stop(self) -> None:
        if not self.running:
            return
        self._uvicorn.should_exit = True
        if self._thread:
            self._thread.join(timeout=10)
        self._uvicorn = None
        self._thread = None
        log.info("server stopped")

    @property
    def running(self) -> bool:
        return self._uvicorn is not None and self._thread is not None
