"""manga-ocr provider — tuned for stylized/pixel Japanese text (optional extra).

manga-ocr is recognition-only, so it composes a text-box detector (RapidOCR or
Tesseract) to find regions and then recognizes each crop.
"""

from __future__ import annotations

from PIL import Image

from ..blocks import Block, Box
from .base import OCRProvider

try:
    from manga_ocr import MangaOcr

    _MANGA_INSTALLED = True
except Exception:  # pragma: no cover
    _MANGA_INSTALLED = False

_CROP_PAD = 4


class MangaOCRProvider(OCRProvider):
    name = "manga"
    description = "manga-ocr (stylized/pixel JP text) over RapidOCR/Tesseract detection"

    def __init__(self, source_lang: str = "ja") -> None:
        self.source_lang = source_lang
        self._model = None
        self._detector = None

    @classmethod
    def available(cls) -> bool:
        if not _MANGA_INSTALLED:
            return False
        return any(p.available() for p in (RapidOCRProvider, TesseractProvider))

    def _get_model(self) -> "MangaOcr":
        if self._model is None:
            self._model = MangaOcr()
        return self._model

    def _get_detector(self) -> OCRProvider:
        if self._detector is None:
            from .rapid import RapidOCRProvider
            from .tesseract import TesseractProvider

            if RapidOCRProvider.available():
                self._detector = RapidOCRProvider(source_lang=self.source_lang)
            else:
                self._detector = TesseractProvider(source_lang=self.source_lang)
        return self._detector

    def detect(self, image: Image.Image) -> list[Box]:
        return self._get_detector().detect(image)

    def ocr(self, image: Image.Image) -> list[Block]:
        model = self._get_model()
        width, height = image.size
        boxes = self._get_detector().detect(image)
        blocks: list[Block] = []
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy()
            crop_box = Box(
                x=max(0, x1 - _CROP_PAD),
                y=max(0, y1 - _CROP_PAD),
                w=min(width, x2 + _CROP_PAD) - max(0, x1 - _CROP_PAD),
                h=min(height, y2 + _CROP_PAD) - max(0, y1 - _CROP_PAD),
            )
            if not crop_box:
                continue
            crop = image.crop(crop_box.xyxy())
            text = (model(crop) or "").strip()
            if not text:
                continue
            blocks.append(
                Block(
                    box=box,
                    source_text=text,
                    confidence=None,
                    source_lang=self.source_lang,
                )
            )
        return blocks
