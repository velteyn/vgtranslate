"""Translation provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image

from ..blocks import Block


class TranslateProvider(ABC):
    name: str = "base"
    description: str = ""
    frame_capable: bool = False

    @classmethod
    @abstractmethod
    def available(cls) -> bool:
        """Whether the underlying engine/package is installed on this machine."""

    @abstractmethod
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        glossary=None,
    ) -> str:
        """Translate a single text snippet."""

    def translate_frame(
        self,
        image: Image.Image,
        source_lang: str,
        target_lang: str,
        glossary=None,
    ) -> list[Block]:
        """Optional: translate an entire frame at once (VLM path)."""
        raise NotImplementedError(f"provider '{self.name}' cannot translate frames")

    def check(self) -> None:
        """Raise if the provider is not usable right now (no model loaded, etc.)."""
