"""Argos Translate provider — offline MT for many languages (optional extra)."""

from __future__ import annotations

from .base import TranslateProvider

try:
    import argostranslate.translate as _argos_translate

    _ARGOS_INSTALLED = True
except Exception:  # pragma: no cover
    _ARGOS_INSTALLED = False


class ArgosProvider(TranslateProvider):
    name = "argos"
    description = "Argos Translate (offline, many languages)"
    frame_capable = False

    @classmethod
    def available(cls) -> bool:
        return _ARGOS_INSTALLED

    def check(self) -> None:
        if not _ARGOS_INSTALLED:
            raise RuntimeError("argostranslate is not installed; run `pip install vgtranslate[mt-argos]`")

    def translate(self, text, source_lang, target_lang, glossary=None) -> str:
        self.check()
        if not text.strip():
            return text
        try:
            result = _argos_translate.translate(text, source_lang, target_lang)
        except Exception as exc:
            raise RuntimeError(
                f"Argos Translate failed for {source_lang}->{target_lang}. "
                "Install language packages with `argos-translate-manage --install-from-index` "
                f"(got: {exc})"
            ) from exc
        if glossary:
            result = glossary.apply_post(result)
        return result
