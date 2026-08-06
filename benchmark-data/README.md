# Benchmark dataset & results

First benchmark set built from real Japanese screenshots (no Megaman assets were
available; the Megaman-only comparison was replaced by the other real captures the
user supplied, per discussion). Sugoi is no longer published on PyPI, so the fast
path is measured with **Argos Translate** as a documented stand-in.

## Dataset

`images/` — 13 cropped text regions; `ground_truth.json` — per-region source text,
expected translation, game and text type.

| Game | Type | Samples | Notes |
|---|---|---|---|
| `srw` (Super Robot Wars, WonderSwan box art) | menu | 5 | marketing/legal text, dense small lines |
| `atelier` (JRPG dialogue) | dialogue | 4 | clean dialogue box lines |
| `baseball` (menu screenshot) | menu/status | 4 | stylized menu labels, lineup rows |

## Scoreboard (13 samples)

| profile | pipeline | detection | usability | mean CER |
|---|---|---|---|---|
| bench-quality | VLM translate + RapidOCR-anchored boxes | 92.3% | 84.6% | 0.104 |
| bench-fast | RapidOCR detect/recognize + Argos MT | 76.9% | 76.9% | 0.282 |

## Decision

The measured results confirm the existing default: **quality** is the default
profile. It reads text the fast path cannot (e.g. the stylized `スタメン` label,
which RapidOCR misses) and lands far more usable translations (mean source CER
0.104 vs 0.282). Nothing to change in the default config.

Notable fast-path limits observed: Argos returns empty or token-level output for
short katakana/kanji strings (player names, `スタメン`, `投手 野手 二軍`), and
RapidOCR fails on very small/stylized menu glyphs.

## Validation notes

- **Quality path end-to-end (LM Studio, `qwen/qwen3.5-9b`)**: full server POST
  with a real screenshot returns a valid native-resolution BMP overlay with
  translations positioned over the original lines.
- **Fast path on CPU**: RapidOCR + Argos runs the whole pipeline (detect →
  recognize → translate → overlay) on full 2560×1440 / 1070×1398 screenshots.
- **Protocol bug fixed during validation**: Starlette's `request.form()` defaults
  to a 1 MB part limit, truncating base64 frames that RetroArch-style urlencoded
  POSTs send. The server now raises it to 100 MB (`server.py`).
