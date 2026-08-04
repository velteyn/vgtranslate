"""Benchmark evaluation runner: run a pipeline over a dataset and score it."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from PIL import Image

from ..config import Config
from ..pipeline import Pipeline
from .dataset import Dataset, Sample
from .metrics import Report, SampleResult, evaluate_sample

log = logging.getLogger("vgtranslate.benchmark")


def run_evaluation(
    dataset: Dataset,
    config: Config,
    source_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
) -> Report:
    pipeline = Pipeline(config)
    profile = config.active()
    results: list[SampleResult] = []

    for sample in dataset.samples:
        result = _run_sample(pipeline, sample, dataset, source_lang, target_lang)
        results.append(result)
        log.info(
            "%s game=%s type=%s detected=%s usable=%s cer=%.3f",
            sample.image,
            sample.game,
            sample.text_type,
            result.detected,
            result.usable,
            result.recognized_cer,
        )
    return Report(profile_name=profile.name, results=results)


def _run_sample(
    pipeline: Pipeline,
    sample: Sample,
    dataset: Dataset,
    source_lang: Optional[str],
    target_lang: Optional[str],
) -> SampleResult:
    result = SampleResult(
        image=sample.image,
        game=sample.game,
        text_type=sample.text_type,
    )
    try:
        frame = dataset.image_for(sample)
        blocks = pipeline.translate_frame(frame, source_lang, target_lang)
        scored = evaluate_sample(sample.source_text, sample.translation, blocks)
        result.detected = scored.detected
        result.recognized_cer = scored.recognized_cer
        result.recognized_text = scored.recognized_text
        result.translation = scored.translation
        result.usable = scored.usable
        result.num_blocks = scored.num_blocks
        result.errors = scored.errors
    except Exception as exc:  # noqa: BLE001
        log.exception("sample %s failed", sample.image)
        result.errors.append(f"exception: {exc}")
    return result


def write_report(report: Report, out_dir: Path, extra_summary: Optional[dict] = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    md = report.to_markdown()
    md_path = out_dir / f"report_{report.profile_name}.md"
    md_path.write_text(md, encoding="utf-8")

    json_path = out_dir / f"report_{report.profile_name}.json"
    payload = {
        "summary": report.summary(),
        "results": [
            {
                "image": r.image,
                "game": r.game,
                "text_type": r.text_type,
                "detected": r.detected,
                "usable": r.usable,
                "recognized_cer": round(r.recognized_cer, 4),
                "recognized_text": r.recognized_text,
                "translation": r.translation,
                "num_blocks": r.num_blocks,
                "errors": r.errors,
            }
            for r in report.results
        ],
    }
    if extra_summary:
        payload["summary"].update(extra_summary)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return md_path
