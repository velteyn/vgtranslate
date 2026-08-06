"""Image utilities: frame encode/decode, upscaling, preprocessing, overlay rendering.

The overlay renderer (fitted text into detected boxes) is a port of the fitted-text
concepts from the legacy ``imaging.py``/``util.py``, using the bundled fonts.
"""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from .blocks import Block, Box

FONTS_DIR = Path(__file__).parent / "fonts"

_LATIN_FONT = "Roboto-Regular.ttf"
_LATIN_BOLD_FONT = "Roboto-Bold.ttf"
_CJK_FONT = "NotoSansCJKtc-Regular.ttf"
_CJK_BOLD_FONT = "NotoSansCJKtc-Bold.ttf"

_FONT_SIZES = (6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 40, 48)

CJK_RANGES = (
    "\u3040-\u30ff",  # hiragana + katakana
    "\u3400-\u4dbf",  # CJK ext A
    "\u4e00-\u9fff",  # CJK unified
    "\uf900-\ufaff",  # CJK compat
    "\uff00-\uffef",  # fullwidth forms
)
CJK_RE = None


def _cjk_re():
    global CJK_RE
    if CJK_RE is None:
        import re

        CJK_RE = re.compile("[" + "".join(CJK_RANGES) + "]")
    return CJK_RE


def contains_cjk(text: str) -> bool:
    return bool(_cjk_re().search(text))


# ---------------------------------------------------------------------------
# Frame encode / decode
# ---------------------------------------------------------------------------


def _data_url_prefix(data: str) -> Optional[str]:
    """Return the format of a ``data:image/...;base64,`` prefix, or None."""
    for fmt in ("png", "jpeg", "jpg", "bmp", "webp"):
        if data.startswith(f"data:image/{fmt};base64,"):
            return "png" if fmt == "jpg" else fmt
    return None


def load_frame(image_data: str) -> Image.Image:
    """Decode a base64 image string (optionally a data URL) into a PIL image."""
    fmt = _data_url_prefix(image_data)
    if fmt is not None:
        payload = image_data.split(",", 1)[1]
    else:
        payload = image_data
    raw = base64.b64decode(payload)
    img = Image.open(io.BytesIO(raw))
    img.load()
    return img.convert("RGB")


def encode_frame(image: Image.Image, fmt: str = "bmp", alpha: bool = False) -> str:
    """Encode a PIL image to base64. ``bmp`` yields 24-bit BGR (RetroArch native)."""
    out = image
    if fmt == "bmp":
        out = image.convert("RGB")
        ext = "bmp"
    elif fmt in ("png", "png-a"):
        if alpha:
            out = image.convert("RGBA")
        else:
            out = image.convert("RGB")
        ext = "png"
    else:
        raise ValueError(f"unsupported output format: {fmt}")
    buf = io.BytesIO()
    out.save(buf, format=ext.upper())
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------


def upscale_nearest(image: Image.Image, factor: int) -> Image.Image:
    """Integer nearest-neighbor upscale (retro-friendly, no blur)."""
    if factor <= 1:
        return image
    w, h = image.size
    return image.resize((w * factor, h * factor), Image.NEAREST)


def isolate_text_color(image: Image.Image) -> Image.Image:
    """High-contrast grayscale preprocessing to isolate text for OCR.

    Optional (off by default); helps some OCR engines on noisy frames.
    """
    gray = image.convert("L")
    # Two-level threshold at 40% brightness; invert so text is dark-on-light
    # is engine-dependent, so keep text dark-on-white like tesseract prefers.
    threshold = 102
    gray = gray.point(lambda p: 255 if p > threshold else 0)
    return gray.convert("RGB")


# ---------------------------------------------------------------------------
# Overlay rendering
# ---------------------------------------------------------------------------


class OverlayRenderer:
    """Renders translated text fitted into detected boxes at native resolution."""

    def __init__(
        self,
        fonts_dir: os.PathLike = FONTS_DIR,
        fill_background: bool = True,
        text_color: tuple[int, int, int] = (255, 255, 255),
        stroke_color: tuple[int, int, int] = (0, 0, 0),
        background_color: tuple[int, int, int] = (0, 0, 0),
        padding: int = 1,
        font_scale: float = 1.0,
    ) -> None:
        self.fonts_dir = Path(fonts_dir)
        self.fill_background = fill_background
        self.text_color = text_color
        self.stroke_color = stroke_color
        self.background_color = background_color
        self.padding = padding
        self.font_scale = font_scale
        self._font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}

    def _font(self, size: int, bold: bool = False, cjk: bool = False) -> ImageFont.FreeTypeFont:
        key = (str(size), bold, cjk)
        cached = self._font_cache.get(key)
        if cached is not None:
            return cached
        if cjk:
            name = _CJK_BOLD_FONT if bold else _CJK_FONT
        else:
            name = _LATIN_BOLD_FONT if bold else _LATIN_FONT
        path = self.fonts_dir / name
        font = ImageFont.truetype(str(path), size)
        self._font_cache[key] = font
        return font

    def _fit_font(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        box_w: int,
        box_h: int,
        cjk: bool,
    ) -> ImageFont.FreeTypeFont:
        inner_w = max(1, box_w - 2 * self.padding)
        inner_h = max(1, box_h - 2 * self.padding)
        for size in reversed(_FONT_SIZES):
            font = self._font(size, cjk=cjk)
            lines = self._wrap(draw, text, font, inner_w)
            line_h = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
            total_h = line_h * len(lines)
            if total_h <= inner_h:
                return font
        return self._font(_FONT_SIZES[0], cjk=cjk)

    @staticmethod
    def _wrap(
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_w: int,
    ) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if draw.textlength(candidate, font=font) <= max_w:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [text]

    def render(self, frame: Image.Image, blocks: list[Block]) -> Image.Image:
        """Return a copy of ``frame`` with translations drawn over each block."""
        out = frame.copy()
        draw = ImageDraw.Draw(out)
        for block in blocks:
            box = block.box
            if not box or not block.translation:
                continue
            if self.font_scale != 1.0:
                cx = box.x + box.w / 2
                cy = box.y + box.h / 2
                box = Box(
                    x=int(round(cx - box.w * self.font_scale / 2)),
                    y=int(round(cy - box.h * self.font_scale / 2)),
                    w=int(round(box.w * self.font_scale)),
                    h=int(round(box.h * self.font_scale)),
                ).clamped(frame.size[0], frame.size[1])
            cjk = contains_cjk(block.translation)
            font = self._fit_font(draw, block.translation, box.w, box.h, cjk)
            x, y = box.x, box.y
            w, h = box.w, box.h

            lines = self._wrap(draw, block.translation, font, w - 2 * self.padding)
            metrics = [font.getbbox(line) for line in lines]
            pitch = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
            max_ink = max((m[3] - m[1] for m in metrics), default=pitch)
            y_start = y + self.padding
            positions = []
            for i, (line, m) in enumerate(zip(lines, metrics)):
                line_w = m[2] - m[0]
                x_start = x + max(self.padding, (w - line_w) // 2)
                positions.append((x_start, y_start + i * pitch, line, line_w))

            if self.fill_background:
                fill_x1 = min(p[0] for p in positions) - self.padding
                fill_x2 = max(p[0] + p[3] for p in positions) + self.padding
                fill_y1 = y_start - self.padding
                fill_y2 = y_start + (len(lines) - 1) * pitch + max_ink + self.padding
                draw.rectangle(
                    (fill_x1, fill_y1, fill_x2, fill_y2),
                    fill=self.background_color,
                )

            stroke_w = max(1, font.size // 14)
            for x_start, ty, line, _line_w in positions:
                draw.text(
                    (x_start, ty),
                    line,
                    font=font,
                    fill=self.text_color,
                    stroke_width=stroke_w,
                    stroke_fill=self.stroke_color,
                    anchor="lt",
                )
        return out
