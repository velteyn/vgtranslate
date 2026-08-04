"""RapidOCR provider — default fast OCR engine (ONNX, CPU-only).

Supports both the modern ``rapidocr>=3.0`` package (returns a
``RapidOCROutput`` object) and the legacy ``rapidocr-onnxruntime<1.4``
package (returns ``(result, elapse)``).
"""

from __future__ import annotations

from PIL import Image

from ..blocks import Block, Box
from .base import OCRProvider

_RAPID_INSTALLED = False
_RAPID_V2 = False
try:  # pragma: no cover - import failure means unavailable
    import numpy as np
    from rapidocr import RapidOCR

    _RAPID_INSTALLED = True
    _RAPID_V2 = True
except Exception:  # pragma: no cover - import failure means unavailable
    try:
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR

        _RAPID_INSTALLED = True
    except Exception:
        pass

_LANG_MAP = {
    "ja": "japan",
    "jp": "japan",
    "ko": "korean",
    "zh": "ch",
    "zh-hans": "ch",
    "zh-cn": "ch",
    "zh-hant": "ch",
    "zh-tw": "ch",
    "en": "en",
}


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
            if _RAPID_V2:
                lang = _LANG_MAP.get(self.source_lang.lower())
                if lang:
                    self._engine = RapidOCR(params={"Rec.lang_type": lang})
                else:
                    self._engine = RapidOCR()
            else:
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
        """Normalize the engine output to a list of (points, text, score)."""
        engine = engine or self._get_engine()
        array = np.array(image)
        if _RAPID_V2:
            out = engine(array)
            if out is None or out.txts is None:
                return []
            boxes = list(out.boxes) if out.boxes is not None else []
            txts = list(out.txts)
            scores = list(out.scores) if out.scores is not None else []
            return [
                (points, text, score)
                for points, text, score in zip(boxes, txts, scores)
            ]
        result, _elapse = engine(array)
        return result or []
