"""Benchmark harness: dataset, metrics, evaluation and headless CLI."""

from .cli import main as cli_main
from .dataset import Dataset, load_dataset
from .evaluate import run_evaluation, write_report
from .metrics import Report

__all__ = [
    "Dataset",
    "Report",
    "cli_main",
    "load_dataset",
    "run_evaluation",
    "write_report",
]
