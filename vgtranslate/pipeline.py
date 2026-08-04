"""Pipeline orchestration: profile-driven stages for one frame.

Quality path:  frame-capable VLM reads + translates the whole (upscaled) frame in
               one shot; detected boxes are scaled back to native resolution.
Fast path:     OCR (preprocess → detect → recognize) then per-block text MT.
Both paths:    overlay rendering happens in the HTTP layer via ``OverlayRenderer``.
"""

from __future__ import annotations

import logging

from PIL import Image

from .blocks import Block, sort_blocks_top_down
from .config import Config
from .glossary import Glossary
from .imaging import isolate_text_color, upscale_nearest
from .mt import get_provider as get_mt_provider
from .ocr import get_provider as get_ocr_provider

log = logging.getLogger("vgtranslate.pipeline")


class Pipeline:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._ocr: dict[tuple, object] = {}
        self._mt: dict[tuple, object] = {}

    def glossary(self) -> Glossary:
        return Glossary(self.config.glossary())

    def profile(self):
        return self.config.active()

    def translator(self):
        profile = self.config.active()
        key = ("mt", profile.translator)
        if key not in self._mt:
            self._mt[key] = get_mt_provider(profile.translator, settings=self.config.llm)
        return self._mt[key]

    def ocr(self):
        profile = self.config.active()
        key = ("ocr", profile.ocr, profile.source_lang)
        if key not in self._ocr:
            self._ocr[key] = get_ocr_provider(profile.ocr, source_lang=profile.source_lang)
        return self._ocr[key]

    def translate_frame(
        self,
        frame: Image.Image,
        source_lang: str | None = None,
        target_lang: str | None = None,
    ) -> list[Block]:
        profile = self.profile()
        source_lang = source_lang or profile.source_lang
        target_lang = target_lang or profile.target_lang
        glossary = self.glossary()
        upscale = max(1, profile.upscale)

        native_w, native_h = frame.size
        work = upscale_nearest(frame, upscale)
        if profile.color_isolation:
            work = isolate_text_color(work)

        translator = self.translator()
        blocks: list[Block]
        if profile.mode == "quality" and getattr(translator, "frame_capable", False):
            log.info("quality path: VLM translate_frame (%s)", translator.name)
            blocks = translator.translate_frame(work, source_lang, target_lang, glossary)
        else:
            log.info("fast path: OCR '%s' + MT '%s'", profile.ocr, profile.translator)
            ocr = self.ocr()
            blocks = ocr.ocr(work)
            blocks = sort_blocks_top_down(blocks)
            self._translate_blocks(blocks, source_lang, target_lang, glossary)

        # Boxes from providers are in upscaled coordinates; map back to native.
        factor = 1.0 / upscale
        for block in blocks:
            if block.box:
                block.box = block.box.scaled(factor).clamped(native_w, native_h)
                block.source_lang = source_lang
                block.target_lang = target_lang
        return blocks

    def _translate_blocks(
        self,
        blocks: list[Block],
        source_lang: str,
        target_lang: str,
        glossary: Glossary,
    ) -> None:
        translator = self.translator()
        texts = [b.source_text for b in blocks]
        if not texts:
            return
        if getattr(translator, "translate_batch", None) and len(texts) > 1:
            try:
                translated = translator.translate_batch(texts, source_lang, target_lang, glossary)
                for block, text in zip(blocks, translated):
                    block.translation = (text or "").strip()
                    block.target_lang = target_lang
                return
            except Exception as exc:  # noqa: BLE001
                log.warning("batch translation failed, falling back to per-line: %s", exc)
        for block in blocks:
            try:
                block.translation = translator.translate(
                    block.source_text, source_lang, target_lang, glossary
                ).strip()
            except Exception as exc:  # noqa: BLE001
                log.warning("translate failed for %r: %s", block.source_text, exc)
                block.translation = ""
            block.target_lang = target_lang
