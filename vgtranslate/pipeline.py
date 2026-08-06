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


def _text_sim(a: str, b: str) -> float:
    """Character-multiset similarity in [0, 1]; robust to OCR/VLM typos."""
    a, b = (a or "").strip(), (b or "").strip()
    if not a or not b:
        return 0.0
    ca: dict[str, int] = {}
    cb: dict[str, int] = {}
    for ch in a:
        ca[ch] = ca.get(ch, 0) + 1
    for ch in b:
        cb[ch] = cb.get(ch, 0) + 1
    common = sum(min(ca.get(ch, 0), cb.get(ch, 0)) for ch in set(ca) | set(cb))
    return 2 * common / (len(a) + len(b))


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

        # VLM box localization is coarse/unreliable; snap translations to precise
        # OCR line boxes when OCR is available so the overlay lands on the text.
        if profile.mode == "quality" and blocks:
            ocr_boxes = self._ocr_boxes(frame, source_lang)
            if ocr_boxes:
                blocks = self._align_to_ocr(blocks, ocr_boxes)
        return blocks

    def _ocr_boxes(self, frame: Image.Image, source_lang: str) -> list[Block]:
        """Run OCR on the native frame to get precise per-line text boxes."""
        try:
            return self.ocr().ocr(frame)
        except Exception as exc:  # noqa: BLE001
            log.warning("OCR alignment unavailable, keeping VLM boxes: %s", exc)
            return []

    def _align_to_ocr(self, blocks: list[Block], ocr_boxes: list[Block]) -> list[Block]:
        """Replace VLM block boxes with OCR line boxes, keeping VLM translations.

        Pairs each OCR line (in reading order) with the best text-similarity VLM
        block that has not been used yet; unmatched lines stay untranslated and
        unmatched VLM blocks are dropped.
        """
        vlm = [b for b in blocks if b.translation]
        if not vlm:
            return blocks
        used: set[int] = set()
        aligned: list[Block] = []
        for ocr_b in sort_blocks_top_down([b for b in ocr_boxes if b.box]):
            best_idx, best_score = -1, 0.0
            for i, vb in enumerate(vlm):
                if i in used:
                    continue
                score = _text_sim(vb.source_text, ocr_b.source_text)
                if score > best_score:
                    best_idx, best_score = i, score
            if best_idx >= 0 and best_score >= 0.6:
                used.add(best_idx)
                vb = vlm[best_idx]
                aligned.append(
                    Block(
                        box=ocr_b.box,
                        source_text=ocr_b.source_text,
                        translation=vb.translation,
                        confidence=None,
                        source_lang=ocr_b.source_lang,
                        target_lang=vb.target_lang,
                        order=0,
                    )
                )
        return sort_blocks_top_down(aligned)

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
