"""Core data model: text regions detected in a game frame."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Box:
    """Axis-aligned rectangle in native frame coordinates (integer pixels)."""

    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0

    @classmethod
    def from_xyxy(cls, x1: float, y1: float, x2: float, y2: float) -> "Box":
        return cls(x=int(x1), y=int(y1), w=int(x2 - x1), h=int(y2 - y1))

    def xyxy(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.w, self.y + self.h)

    def scaled(self, factor: float) -> "Box":
        """Scale box coordinates by a uniform factor (for upscaled input)."""
        return Box(
            x=int(round(self.x * factor)),
            y=int(round(self.y * factor)),
            w=int(round(self.w * factor)),
            h=int(round(self.h * factor)),
        )

    def clamped(self, width: int, height: int) -> "Box":
        x1, y1, x2, y2 = self.xyxy()
        x1 = max(0, min(x1, width))
        y1 = max(0, min(y1, height))
        x2 = max(x1, min(x2, width))
        y2 = max(y1, min(y2, height))
        return Box(x=x1, y=y1, w=x2 - x1, h=y2 - y1)

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}

    @classmethod
    def from_dict(cls, data: dict) -> "Box":
        return cls(x=int(data["x"]), y=int(data["y"]), w=int(data["w"]), h=int(data["h"]))

    def __bool__(self) -> bool:
        return self.w > 0 and self.h > 0


@dataclass
class Block:
    """One region of game text with its recognized source and translation."""

    box: Box
    source_text: str = ""
    translation: str = ""
    confidence: Optional[float] = None
    target_lang: str = ""
    source_lang: str = ""
    order: int = 0

    def to_dict(self) -> dict:
        return {
            "box": self.box.to_dict(),
            "source_text": self.source_text,
            "translation": self.translation,
            "confidence": self.confidence,
            "target_lang": self.target_lang,
            "source_lang": self.source_lang,
            "order": self.order,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        return cls(
            box=Box.from_dict(data["box"]),
            source_text=data.get("source_text", ""),
            translation=data.get("translation", ""),
            confidence=data.get("confidence"),
            target_lang=data.get("target_lang", ""),
            source_lang=data.get("source_lang", ""),
            order=data.get("order", 0),
        )


def sort_blocks_top_down(blocks: list[Block]) -> list[Block]:
    """Sort text regions in natural reading order (top-to-bottom, left-to-right)."""
    ordered = []
    remaining = [b for b in blocks if b.box]
    y_rows: list[list[Block]] = []

    for block in sorted(remaining, key=lambda b: b.box.y):
        placed = False
        for row in y_rows:
            anchor = row[0].box
            center = block.box.y + block.box.h / 2
            row_top = anchor.y - max(8, anchor.h // 2)
            row_bottom = anchor.y + anchor.h + max(8, anchor.h // 2)
            if row_top <= center <= row_bottom:
                row.append(block)
                placed = True
                break
        if not placed:
            y_rows.append([block])

    for row in sorted(y_rows, key=lambda r: min(b.box.y for b in r)):
        ordered.extend(sorted(row, key=lambda b: b.box.x))

    for index, block in enumerate(ordered):
        block.order = index
    return ordered
