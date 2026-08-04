"""Sugoi translator — strong offline Japanese→English text MT (optional extra)."""

from __future__ import annotations

from .base import TranslateProvider

try:
    from sugoi.SugoiTranslator import SugoiTranslator as _SugoiTranslator

    _SUGOI_INSTALLED = True
except Exception:  # pragma: no cover
    _SUGOI_INSTALLED = False


class SugoiProvider(TranslateProvider):
    name = "sugoi"
    description = "Sugoi (offline JP→EN neural MT)"
    frame_capable = False

    def __init__(self) -> None:
        self._translator = None

    @classmethod
    def available(cls) -> bool:
        return _SUGOI_INSTALLED

    def check(self) -> None:
        if not _SUGOI_INSTALLED:
            raise RuntimeError("sugoi is not installed; run `pip install vgtranslate[mt-sugoi]`")
        # Model download happens lazily on first use; surface it there.

    def _get(self) -> "_SugoiTranslator":
        if self._translator is None:
            self._translator = _SugoiTranslator()
        return self._translator

    def translate(self, text, source_lang, target_lang, glossary=None) -> str:
        self.check()
        if not text.strip():
            return text
        result = self._get().translate(text)
        if glossary:
            result = glossary.apply_post(result)
        return result
