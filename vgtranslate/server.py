"""RetroArch-compatible HTTP server (FastAPI + uvicorn).

Implements the libretro AI Service wire protocol on localhost:4404:

* ``POST /`` (or any path) — translate a paused-game screenshot. Query params
  carry ``source_lang``, ``target_lang``, ``output``; the body (urlencoded form
  or JSON) carries ``image`` (base64), ``format``, ``coords``, ``viewport``,
  ``state``.
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
from .imaging import OverlayRenderer, encode_frame, load_frame
from .mt import list_providers as list_mt_providers
from .ocr import list_providers as list_ocr_providers
from .pipeline import Pipeline

log = logging.getLogger("vgtranslate.server")

VALID_OUTPUTS = ("image", "text", "both")
DEFAULT_OUTPUT = "image"


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
        except ValueError as exc:
            return JSONResponse({"status": "error", "message": str(exc)}, status_code=400)
        except Exception as exc:  # noqa: BLE001
            log.exception("service request failed")
            return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)
        return JSONResponse(result)

    return app


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
        elif content_type.startswith("application/x-www-form-urlencoded"):
            form = await _request_form(request)
            params.update({str(k): v for k, v in form.items()})
    except Exception:  # noqa: BLE001
        raw = await request.body()
        if raw:
            try:
                body = json.loads(raw.decode("utf-8"))
                if isinstance(body, dict):
                    params.update({str(k): v for k, v in body.items()})
            except (ValueError, UnicodeDecodeError):
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


def _handle_service(state, params: dict) -> dict:
    config: Config = state.config
    pipeline: Pipeline = state.pipeline
    renderer: OverlayRenderer = state.renderer

    image_data = _as_str(params.get("image"))
    if not image_data:
        raise ValueError("missing 'image' parameter")

    source_lang = _as_str(params.get("source_lang")) or config.active().source_lang
    target_lang = (
        _as_str(params.get("target_lang")) or config.active().target_lang
        or config.server.default_target
    )
    output = _as_str(params.get("output")) or DEFAULT_OUTPUT
    if output not in VALID_OUTPUTS:
        raise ValueError(f"'output' must be one of {VALID_OUTPUTS}, got '{output}'")

    frame = load_frame(image_data)
    blocks = pipeline.translate_frame(frame, source_lang, target_lang)
    blocks = [b for b in blocks if b.translation]

    response: dict = {"status": "success", "target_lang": target_lang}

    if output in ("text", "both") and blocks:
        response["text"] = "\n".join(b.translation for b in blocks)
        first = blocks[0].box
        response["text_position"] = [first.x, first.y, first.w, first.h]
        response["text_encoding"] = "utf-8"

    if output in ("image", "both"):
        overlay = renderer.render(frame, blocks)
        response["image"] = encode_frame(overlay, fmt="bmp")
        response["image_width"] = overlay.width
        response["image_height"] = overlay.height
        response["image_format"] = "bmp"
        response["image_encoding"] = "base64"

    if config.server.auto_unpause and _is_paused(params):
        response["press"] = ["unpause"]

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
