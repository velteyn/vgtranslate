"""Headless benchmark CLI: ``vgtranslate bench``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..config import Config, load_config
from .dataset import Dataset, load_dataset, new_dataset
from .evaluate import run_evaluation, write_report


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="path to config.json (default: user config dir)",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="profile name to evaluate (default: active profile)",
    )
    parser.add_argument(
        "--source-lang",
        default=None,
        help="override source language (e.g. ja)",
    )
    parser.add_argument(
        "--target-lang",
        default=None,
        help="override target language (e.g. en)",
    )


def _load_config_and_profile(args) -> tuple[Config, str]:
    config = load_config(args.config) if args.config else load_config()
    if args.profile:
        if args.profile not in config.profiles:
            sys.exit(f"unknown profile '{args.profile}'; available: {list(config.profiles)}")
        config.active_profile = args.profile
    return config, config.active_profile


def cmd_run(args) -> None:
    dataset = load_dataset(args.dataset)
    config, _ = _load_config_and_profile(args)
    report = run_evaluation(dataset, config, args.source_lang, args.target_lang)
    out = args.output if args.output else Path("bench-out")
    path = write_report(report, out)
    print(report.to_markdown())
    print(f"\nWrote report to {path}")


def cmd_init(args) -> None:
    samples = []
    if args.images_dir:
        images = Path(args.images_dir)
        for img in sorted(images.glob("*.png")) + sorted(images.glob("*.jpg")):
            samples.append(
                {
                    "image": img.name,
                    "game": args.game or "",
                    "text_type": "dialogue",
                    "source_text": "",
                    "translation": "",
                }
            )
    path = new_dataset(args.dataset, samples)
    print(f"Created dataset skeleton at {path}")
    print("Edit ground_truth.json to fill in source_text / translation per sample.")


def cmd_scoreboard(args) -> None:
    """Compare multiple report JSONs side by side (scoreboard)."""
    rows = []
    for report in args.reports:
        data = json.loads(Path(report).read_text(encoding="utf-8"))
        rows.append(data["summary"])
    if not rows:
        sys.exit("no reports given")
    print("| profile | samples | detection | usability | mean CER |")
    print("|---|---|---|---|---|")
    for row in sorted(rows, key=lambda r: r["usability_rate"], reverse=True):
        print(
            f"| {row['profile']} | {row['samples']} | {row['detection_rate']} | "
            f"{row['usability_rate']} | {row['mean_cer']} |"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vgtranslate bench",
        description="vgtranslate benchmark harness",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="evaluate a profile against a dataset")
    run.add_argument("dataset", type=Path, help="dataset directory (images/ + ground_truth.json)")
    run.add_argument("--output", type=Path, default=None, help="output directory for reports")
    _add_common(run)
    run.set_defaults(func=cmd_run)

    init = sub.add_parser("init", help="create a dataset skeleton")
    init.add_argument("dataset", type=Path, help="dataset directory to create")
    init.add_argument("--images-dir", type=Path, default=None, help="pre-fill from PNGs here")
    init.add_argument("--game", default=None, help="default game tag")
    init.set_defaults(func=cmd_init)

    score = sub.add_parser("scoreboard", help="compare report JSONs")
    score.add_argument("reports", nargs="+", type=Path, help="report_<profile>.json files")
    score.set_defaults(func=cmd_scoreboard)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0
