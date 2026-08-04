"""Tesseract provider — fallback OCR engine (optional extra)."""

from __future__ import annotations

from PIL import Image

from ..blocks import Block, Box
from .base import OCRProvider

try:
    import pytesseract
    from pytesseract import Output

    _TESSERACT_INSTALLED = pytesseract.get_tesseract_version() is not None
except Exception:  # pragma: no cover
    _TESSERACT_INSTALLED = False


class TesseractProvider(OCRProvider):
    name = "tesseract"
    description = "Tesseract OCR (pytesseract) — fallback engine"

    def __init__(self, source_lang: str = "ja", lang: str = "jpn") -> None:
        self.source_lang = source_lang
        self.lang = lang

    @classmethod
    def available(cls) -> bool:
        return _TESSERACT_INSTALLED

    def detect(self, image: Image.Image) -> list[Box]:
        boxes = []
        for box, _text, _conf in self._lines(image):
            if box:
                boxes.append(box)
        return boxes

    def ocr(self, image: Image.Image) -> list[Block]:
        blocks: list[Block] = []
        for box, text, conf in self._lines(image):
            text = text.strip()
            if not text or not box:
                continue
            blocks.append(
                Block(
                    box=box,
                    source_text=text,
                    confidence=conf,
                    source_lang=self.source_lang,
                )
            )
        return blocks

    def _lines(self, image: Image.Image) -> list[tuple[Box, str, float | None]]:
        data = pytesseract.image_to_data(
            image.convert("RGB"), lang=self.lang, output_type=Output.DICT
        )
        words = []
        for i, text in enumerate(data["text"]):
            text = (text or "").strip()
            if not text:
                continue
            words.append(
                {
                    "text": text,
                    "conf": data["conf"][i],
                    "block": data["block_num"][i],
                    "par": data["par_num"][i],
                    "line": data["line_num"][i],
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "w": data["width"][i],
                    "h": data["height"][i],
                }
            )
        lines: dict[tuple[int, int, int], list[dict]] = {}
        for word in words:
            key = (word["block"], word["par"], word["line"])
            lines.setdefault(key, []).append(word)

        result: list[tuple[Box, str, float | None]] = []
        for key in sorted(lines):
            group = lines[key]
            x1 = min(w["x"] for w in group)
            y1 = min(w["y"] for w in group)
            x2 = max(w["x"] + w["w"] for w in group)
            y2 = max(w["y"] + w["h"] for w in group)
            text = " ".join(w["text"] for w in group)
            confs = [w["conf"] for w in group if w["conf"] >= 0]
            conf = sum(confs) / len(confs) if confs else None
            result.append((Box.from_xyxy(x1, y1, x2, y2), text, conf))
        return result
