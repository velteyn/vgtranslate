"""OCR provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image

from ..blocks import Block, Box


class OCRProvider(ABC):
    """Detects and recognizes text regions in a frame, returning Blocks."""

    name: str = "base"
    description: str = ""

    @classmethod
    @abstractmethod
    def available(cls) -> bool:
        """Whether the underlying engine/package is installed on this machine."""

    @abstractmethod
    def ocr(self, image: Image.Image) -> list[Block]:
        """Return text blocks (boxes + recognized text + confidence)."""

    def detect(self, image: Image.Image) -> list[Box]:
        """Optional: return text boxes without recognition."""
        raise NotImplementedError


def blocks_from_lines(
    lines: list[tuple[Box, str, float | None]],
    source_lang: str,
) -> list[Block]:
    """Build Blocks from ``(box, text, confidence)`` triples, filtering empties."""
    blocks = []
    for box, text, confidence in lines:
        text = text.strip()
        if not text:
            continue
        blocks.append(
            Block(
                box=box,
                source_text=text,
                confidence=confidence,
                source_lang=source_lang,
            )
        )
    return blocks
