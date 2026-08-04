"""Benchmark metrics: detection hit rate, CER, end-to-end usability."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..blocks import Block

# CER below this means the region was detected and read correctly.
DETECTION_CER_THRESHOLD = 0.5


def levenshtein(a: str, b: str) -> int:
    """Classic DP edit distance (no external dependency)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = curr
    return prev[-1]


def cer(reference: str, hypothesis: str) -> float:
    """Character error rate in [0, 1]; empty reference is 0 if empty hyp else 1."""
    if not reference:
        return 0.0 if not hypothesis else 1.0
    return levenshtein(reference, hypothesis) / len(reference)


@dataclass
class SampleResult:
    image: str
    game: str = ""
    text_type: str = "dialogue"
    detected: bool = False
    recognized_cer: float = 1.0
    recognized_text: str = ""
    translation: str = ""
    usable: bool = False
    num_blocks: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def good(self) -> bool:
        return self.detected and self.usable


def evaluate_sample(truth_text: str, truth_translation: str, blocks: list[Block]) -> SampleResult:
    """Score one ground-truth sample against the blocks the pipeline returned."""
    result = SampleResult(image="", detected=False, recognized_cer=1.0)
    result.num_blocks = len(blocks)

    if not blocks:
        result.errors.append("no text blocks detected")
        return result

    best = min(blocks, key=lambda b: cer(truth_text, b.source_text))
    result.recognized_cer = cer(truth_text, best.source_text)
    result.recognized_text = best.source_text
    result.detected = result.recognized_cer <= DETECTION_CER_THRESHOLD
    if not result.detected:
        result.errors.append(f"source CER {result.recognized_cer:.2f} > {DETECTION_CER_THRESHOLD}")

    if truth_translation:
        translations = [b.translation for b in blocks if b.translation]
        result.translation = translations[0] if translations else ""
        result.usable = bool(result.translation) and result.translation != best.source_text
        if not result.usable:
            result.errors.append("translation empty or identical to source")
        else:
            result.usable = result.usable and cer(truth_translation, result.translation) < 1.0
            if not result.usable:
                result.errors.append("translation CER vs truth == 1.0")
    else:
        result.usable = True
    return result


@dataclass
class Report:
    profile_name: str
    results: list[SampleResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def detection_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.detected for r in self.results) / len(self.results)

    @property
    def usability_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.usable for r in self.results) / len(self.results)

    @property
    def mean_cer(self) -> float:
        if not self.results:
            return 1.0
        return sum(r.recognized_cer for r in self.results) / len(self.results)

    def by_game(self) -> dict[str, list[SampleResult]]:
        grouped: dict[str, list[SampleResult]] = {}
        for result in self.results:
            grouped.setdefault(result.game or "?", []).append(result)
        return grouped

    def summary(self) -> dict:
        return {
            "profile": self.profile_name,
            "samples": self.total,
            "detection_rate": round(self.detection_rate, 3),
            "usability_rate": round(self.usability_rate, 3),
            "mean_cer": round(self.mean_cer, 3),
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Benchmark: {self.profile_name}",
            "",
            f"- Samples: {self.total}",
            f"- Detection hit rate: {self.detection_rate:.1%}",
            f"- Usability rate: {self.usability_rate:.1%}",
            f"- Mean source CER: {self.mean_cer:.3f}",
            "",
            "## Per-sample",
            "",
            "| sample | game | type | detected | CER | usable | num blocks |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in sorted(self.results, key=lambda r: (r.game, r.image)):
            lines.append(
                f"| {r.image} | {r.game} | {r.text_type} | {r.detected} | "
                f"{r.recognized_cer:.2f} | {r.usable} | {r.num_blocks} |"
            )
        lines.append("")
        for game, results in sorted(self.by_game().items()):
            lines.append(f"### {game}")
            lines.append(f"- samples: {len(results)}")
            lines.append(f"- detection: {sum(r.detected for r in results)}/{len(results)}")
            lines.append(f"- usable: {sum(r.usable for r in results)}/{len(results)}")
            lines.append("")
        return "\n".join(lines)
