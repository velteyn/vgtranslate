"""OCR engine providers and registry."""

from __future__ import annotations

from .manga import MangaOCRProvider
from .rapid import RapidOCRProvider
from .tesseract import TesseractProvider

__all__ = ["MangaOCRProvider", "RapidOCRProvider", "TesseractProvider", "get_provider", "list_providers"]


def _all() -> list[type]:
    return [RapidOCRProvider, MangaOCRProvider, TesseractProvider]


def get_provider(name: str, source_lang: str = "ja"):
    for cls in _all():
        if cls.name == name:
            return cls(source_lang=source_lang)
    raise KeyError(f"unknown OCR provider '{name}'; available: {[c.name for c in _all()]}")


def list_providers() -> dict[str, dict]:
    """Availability map for the status endpoint / tray app."""
    return {
        cls.name: {"available": cls.available(), "description": cls.description}
        for cls in _all()
    }
