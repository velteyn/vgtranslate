"""OpenAI-compatible LLM/VLM client for the quality path.

Talks to any local server exposing ``/v1/chat/completions`` (LM Studio, Ollama,
vLLM, ...). The frame-capable path sends the whole (upscaled) screenshot and asks
for JSON regions: ``[{text, box:[x,y,w,h], translation}]``. The text path
translates snippets for the fast pipeline.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
from typing import Optional

import httpx
from PIL import Image

from ..blocks import Block, Box
from ..config import LLMSettings
from .base import TranslateProvider

log = logging.getLogger("vgtranslate.mt.openai")

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _extract_content(message: dict) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                parts.append(part.get("text", "") if part.get("type") == "text" else "")
        return "".join(parts)
    return str(content)


class OpenAICompatTranslator(TranslateProvider):
    name = "openai"
    description = "OpenAI-compatible vision LLM (LM Studio / Ollama) — quality path"
    frame_capable = True

    def __init__(
        self,
        settings: Optional[LLMSettings] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        settings = settings or LLMSettings()
        self.settings = settings
        self._transport = transport
        self._client: Optional[httpx.Client] = None

    @classmethod
    def available(cls) -> bool:
        try:
            import httpx  # noqa: F401

            return True
        except ImportError:
            return False

    @property
    def base_url(self) -> str:
        return self.settings.base_url.rstrip("/")

    @property
    def model(self) -> str:
        return self.settings.model

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.settings.timeout,
                transport=self._transport,
            )
        return self._client

    # -- connection / models -------------------------------------------------

    def list_models(self) -> list[str]:
        """GET /v1/models, returns model ids (empty list if unavailable)."""
        if not self.base_url:
            return []
        try:
            resp = self._http().get("/models")
            resp.raise_for_status()
            data = resp.json().get("data", [])
            return [str(m.get("id", "")) for m in data if m.get("id")]
        except Exception as exc:  # noqa: BLE001
            log.warning("model listing failed: %s", exc)
            return []

    def check_connection(self) -> tuple[bool, str]:
        """Return (ok, detail). ``ok`` is True when a model is reachable."""
        if not self.base_url:
            return False, "no LLM base_url configured"
        models = self.list_models()
        if not models:
            return False, f"no models reachable at {self.base_url}"
        return True, f"{len(models)} model(s) at {self.base_url}"

    # -- chat ----------------------------------------------------------------

    def _chat(self, messages: list[dict]) -> str:
        if not self.base_url or not self.model:
            raise RuntimeError(
                "LLM not configured: set base_url and model in config or via the tray app"
            )
        payload: dict = {
            "model": self.model,
            "messages": list(messages),
            "temperature": self.settings.temperature,
            "stream": False,
        }
        if self.settings.skip_reasoning and payload["messages"]:
            # Reasoning models (e.g. Qwen3.x) burn their whole budget on
            # chain-of-thought before answering, which times out on slow local
            # inference. A trailing empty assistant turn skips the thinking phase.
            payload["messages"].append({"role": "assistant", "content": " \n"})
            payload["continue_assistant_turn"] = True
        if self.settings.json_mode:
            payload["response_format"] = {"type": "json_object"}
        resp = None
        try:
            resp = self._http().post("/chat/completions", json=payload)
            resp.raise_for_status()
        except Exception as exc:
            if resp is not None and self.settings.json_mode and resp.status_code in (400, 422):
                # Some local servers reject response_format; retry without it.
                payload.pop("response_format", None)
                try:
                    resp = self._http().post("/chat/completions", json=payload)
                    resp.raise_for_status()
                except Exception as retry_exc:
                    raise RuntimeError(f"LLM request failed: {retry_exc}") from retry_exc
            else:
                raise RuntimeError(f"LLM request failed: {exc}") from exc
        data = resp.json()
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"unexpected LLM response: {data}") from exc
        return _extract_content(message)

    @staticmethod
    def _find_json_end(text: str, start: int) -> int:
        """Index just past the balanced JSON value starting at ``start``."""
        depth = 0
        in_str = False
        escaped = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch in "[{":
                depth += 1
            elif ch in "]}":
                depth -= 1
                if depth == 0:
                    return i + 1
        return len(text)

    @staticmethod
    def _parse_json(text: str) -> list:
        """Extract a JSON array (or object) from a model response.

        Models frequently append trailing prose or an ellipsis after the JSON;
        only the balanced JSON value is parsed so those are tolerated.
        """
        stripped = text.strip()
        if not stripped:
            raise ValueError("empty LLM response")
        fenced = _JSON_FENCE.search(stripped)
        if fenced:
            stripped = fenced.group(1).strip()
        # Strip any leading prose, find the first '[' or '{'.
        start = len(stripped)
        for marker in ("[", "{"):
            idx = stripped.find(marker)
            if idx != -1 and idx < start:
                start = idx
        if start == len(stripped):
            raise ValueError(f"no JSON found in LLM response: {text[:200]!r}")
        end = OpenAICompatTranslator._find_json_end(stripped, start)
        try:
            data = json.loads(stripped[start:end])
        except (ValueError, json.JSONDecodeError):
            # Best-effort salvage: the model occasionally drops a malformed item
            # or stray text mid-array. Extract every well-formed JSON object.
            items: list = []
            pos = start
            while True:
                idx = stripped.find("{", pos)
                if idx == -1 or idx >= end:
                    break
                obj_end = OpenAICompatTranslator._find_json_end(stripped, idx)
                try:
                    obj = json.loads(stripped[idx:obj_end])
                except (ValueError, json.JSONDecodeError):
                    obj = None
                if isinstance(obj, dict):
                    items.append(obj)
                pos = idx + 1
            if not items:
                raise ValueError(f"no JSON found in LLM response: {text[:200]!r}")
            return items
        return data if isinstance(data, list) else [data]

    # -- text translation ----------------------------------------------------

    def translate(self, text, source_lang, target_lang, glossary=None) -> str:
        if not text.strip():
            return text
        system = "You are a professional video game translator. Translate the given text exactly."
        if glossary:
            system += "\n" + glossary.prompt_guidance()
        user = (
            f"Translate from {source_lang} to {target_lang}. "
            f"Reply with ONLY the translation, no explanations.\n\n{text}"
        )
        reply = self._chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        )
        return reply.strip()

    def translate_batch(self, texts, source_lang, target_lang, glossary=None) -> list[str]:
        """Translate a list of snippets in a single request."""
        if not texts:
            return []
        numbered = "\n".join(f"{i}: {t}" for i, t in enumerate(texts) if t.strip())
        system = "You are a professional video game translator. Translate each numbered line."
        if glossary:
            system += "\n" + glossary.prompt_guidance()
        user = (
            f"Translate each line from {source_lang} to {target_lang}. "
            "Reply ONLY with a JSON array of strings, same order and count. "
            f"Here are the lines:\n{numbered}"
        )
        reply = self._chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        )
        try:
            parsed = self._parse_json(reply)
            if isinstance(parsed[0], str):
                parsed = [str(p) for p in parsed]
            else:
                parsed = [str(item.get("translation", "")) for item in parsed]
        except Exception:
            lines = [ln for ln in reply.splitlines() if ln.strip()]
            parsed = [ln.split(":", 1)[1].strip() if ":" in ln else ln for ln in lines]
        parsed = [p for p in parsed]
        if len(parsed) < len(texts):
            parsed += [""] * (len(texts) - len(parsed))
        return parsed[: len(texts)]

    # -- frame translation (VLM) ---------------------------------------------

    def translate_frame(
        self,
        image: Image.Image,
        source_lang: str,
        target_lang: str,
        glossary=None,
    ) -> list[Block]:
        width, height = image.size
        system = (
            "You are a professional video game translator. You will be shown one game "
            "screenshot. Read EVERY region containing text, in reading order "
            "(top-to-bottom, left-to-right). Do not skip menu items, status text or "
            "dialogue.\n"
            'Reply ONLY with a JSON array, no markdown, in this exact shape:\n'
            '[{"text": "original text", "box": [x1, y1, x2, y2], '
            '"translation": "translated text"}] '
            f"where box is [top-left x, top-left y, bottom-right x, bottom-right y] "
            f"as integer pixel positions in the {width}x{height} image.\n"
            'Example: [{"text": "ダメ", "box": [10, 10, 100, 30], "translation": "No good"}]\n'
            "Use exactly the keys text, box, translation. "
            "Make each box tightly enclose a single text line (its true height), never merge lines.\n"
            f"Translate all text from {source_lang} to {target_lang}."
        )
        if glossary:
            system += "\n" + glossary.prompt_guidance()

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        user_content = [
            {
                "type": "text",
                "text": "Translate all text regions in this screenshot.",
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{encoded}"},
            },
        ]
        reply = self._chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ]
        )
        return self._blocks_from_json(reply, source_lang, target_lang)

    def _blocks_from_json(self, reply: str, source_lang: str, target_lang: str) -> list[Block]:
        try:
            items = self._parse_json(reply)
        except (ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"VLM returned unparseable JSON: {exc}") from exc
        blocks: list[Block] = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            box = item.get("box") or item.get("box_2d")
            if isinstance(box, dict):
                if "x1" in box or "x2" in box:
                    box = Box.from_xyxy(
                        int(box.get("x1", 0)),
                        int(box.get("y1", 0)),
                        int(box.get("x2", 0)),
                        int(box.get("y2", 0)),
                    )
                else:
                    box = Box(
                        x=int(box.get("x", 0)),
                        y=int(box.get("y", 0)),
                        w=int(box.get("w", 0)),
                        h=int(box.get("h", 0)),
                    )
            elif isinstance(box, (list, tuple)) and len(box) == 4:
                x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
                box = Box.from_xyxy(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            else:
                box = Box()
            if not box:
                continue
            text = str(item.get("text") or item.get("text_content") or "").strip()
            translation = str(item.get("translation", "") or "").strip()
            if not text and not translation:
                continue
            blocks.append(
                Block(
                    box=box,
                    source_text=text,
                    translation=translation,
                    confidence=None,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    order=index,
                )
            )
        return blocks
