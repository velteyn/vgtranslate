"""RapidOCR provider — default fast OCR engine (ONNX, CPU-only)."""

from __future__ import annotations

from PIL import Image

from ..blocks import Block, Box
from .base import OCRProvider

try:
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR

    _RAPID_INSTALLED = True
except Exception:  # pragma: no cover - import failure means unavailable
    _RAPID_INSTALLED = False


class RapidOCRProvider(OCRProvider):
    name = "rapid"
    description = "RapidOCR (ONNX, CPU) — default OCR engine"

    def __init__(self, source_lang: str = "ja") -> None:
        self.source_lang = source_lang
        self._engine = None

    @classmethod
    def available(cls) -> bool:
        return _RAPID_INSTALLED

    def _get_engine(self) -> "RapidOCR":
        if not _RAPID_INSTALLED:
            raise RuntimeError(
                "RapidOCR is not installed; run `pip install vgtranslate[ocr]`"
            )
        if self._engine is None:
            self._engine = RapidOCR()
        return self._engine

    def detect(self, image: Image.Image) -> list[Box]:
        result = self._ocr_result(image)
        boxes = []
        for item in result:
            if not item:
                continue
            points, _text, _score = item
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            box = Box.from_xyxy(min(xs), min(ys), max(xs), max(ys))
            if box:
                boxes.append(box)
        return boxes

    def ocr(self, image: Image.Image) -> list[Block]:
        engine = self._get_engine()
        result = self._ocr_result(image, engine=engine)
        blocks: list[Block] = []
        for item in result:
            if not item:
                continue
            points, text, score = item
            text = (text or "").strip()
            if not text:
                continue
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            box = Box.from_xyxy(min(xs), min(ys), max(xs), max(ys))
            if not box:
                continue
            blocks.append(
                Block(
                    box=box,
                    source_text=text,
                    confidence=float(score) if score is not None else None,
                    source_lang=self.source_lang,
                )
            )
        return blocks

    def _ocr_result(self, image: Image.Image, engine=None):
        import numpy as np

        engine = engine or self._get_engine()
        array = np.array(image)
        result, _elapse = engine(array)
        return result or []
