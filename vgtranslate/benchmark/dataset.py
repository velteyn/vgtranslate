"""Benchmark dataset: images + ground truth.

Layout::

    dataset/
      images/            # one PNG per sample
      ground_truth.json  # list of samples with metadata

``ground_truth.json``::

    {
      "samples": [
        {
          "image": "srw_dialogue_01.png",
          "game": "srw",
          "text_type": "dialogue",        # dialogue | menu | status
          "source_text": "…",
          "translation": "…",
          "boxes": [[x1, y1, x2, y2]]     # optional, native pixels
        }
      ]
    }
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image

from ..blocks import Box


class DatasetError(Exception):
    pass


@dataclass
class Sample:
    image: str
    game: str = ""
    text_type: str = "dialogue"
    source_text: str = ""
    translation: str = ""
    boxes: list[Box] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Sample":
        boxes = []
        for raw in data.get("boxes", []):
            if isinstance(raw, dict):
                boxes.append(Box.from_dict(raw))
            elif len(raw) == 4:
                boxes.append(Box.from_xyxy(raw[0], raw[1], raw[2], raw[3]))
        return cls(
            image=str(data["image"]),
            game=str(data.get("game", "")),
            text_type=str(data.get("text_type", "dialogue")),
            source_text=str(data.get("source_text", "")),
            translation=str(data.get("translation", "")),
            boxes=boxes,
        )

    def to_dict(self) -> dict:
        return {
            "image": self.image,
            "game": self.game,
            "text_type": self.text_type,
            "source_text": self.source_text,
            "translation": self.translation,
            "boxes": [b.to_dict() for b in self.boxes],
        }


@dataclass
class Dataset:
    root: Path
    samples: list[Sample]

    def image_for(self, sample: Sample) -> Image.Image:
        path = self.root / "images" / sample.image
        if not path.exists():
            raise DatasetError(f"image missing for sample: {path}")
        img = Image.open(path)
        img.load()
        return img.convert("RGB")

    def split(self, game: Optional[str] = None) -> list[Sample]:
        if game is None:
            return self.samples
        return [s for s in self.samples if s.game == game]


def load_dataset(path) -> Dataset:
    root = Path(path)
    gt_path = root / "ground_truth.json"
    if not gt_path.exists():
        raise DatasetError(f"no ground_truth.json in {root}")
    raw = json.loads(gt_path.read_text(encoding="utf-8"))
    samples = [Sample.from_dict(s) for s in raw.get("samples", [])]
    if not samples:
        raise DatasetError(f"dataset {root} has no samples")
    return Dataset(root=root, samples=samples)


def new_dataset(root, samples: list[dict]) -> Path:
    """Create a dataset skeleton (used by the init helper)."""
    path = Path(root)
    images = path / "images"
    images.mkdir(parents=True, exist_ok=True)
    gt = {"samples": samples}
    (path / "ground_truth.json").write_text(
        json.dumps(gt, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return path
