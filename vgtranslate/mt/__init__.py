"""Translation engine providers and registry."""

from __future__ import annotations

from ..config import LLMSettings
from .argos import ArgosProvider
from .base import TranslateProvider
from .openai_compat import OpenAICompatTranslator
from .sugoi import SugoiProvider

__all__ = [
    "ArgosProvider",
    "OpenAICompatTranslator",
    "SugoiProvider",
    "get_provider",
    "list_providers",
]


def _all() -> list[type]:
    return [OpenAICompatTranslator, SugoiProvider, ArgosProvider]


def get_provider(name: str, settings: LLMSettings | None = None) -> TranslateProvider:
    if name == OpenAICompatTranslator.name:
        return OpenAICompatTranslator(settings)
    for cls in _all():
        if cls.name == name:
            return cls()
    raise KeyError(f"unknown translator '{name}'; available: {[c.name for c in _all()]}")


def list_providers() -> dict[str, dict]:
    """Availability map for the status endpoint / tray app."""
    return {
        cls.name: {
            "available": cls.available(),
            "frame_capable": cls.frame_capable,
            "description": cls.description,
        }
        for cls in _all()
    }
