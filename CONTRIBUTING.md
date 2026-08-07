# Contributing to VGTranslate

Thanks for wanting to help! VGTranslate is a local-first RetroArch AI Service
translator: Japanese game text becomes an English overlay using only free
software running on your own machine.

This guide covers how the project works and how to contribute cleanly. Everyone
is expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md). For
vulnerability reports, see [SECURITY.md](SECURITY.md).

## Ways to contribute

You do not need to be a maintainer to help:

- **Report bugs** — open an issue with a clear repro (game, frame, config).
- **Request or propose features** — open an issue or, better, an OpenSpec change
  (see [Planning changes](#planning-changes)).
- **Improve the code or docs** — see [Submitting changes](#submitting-changes).
- **Add benchmark data** — real failing screenshots with ground truth are
  extremely valuable; the `benchmark-data/` directory is where they live.

## Project layout

```
vgtranslate/            the Python package (the server + engines)
  server.py             FastAPI server, RetroArch /service endpoint
  pipeline.py           quality (VLM) and fast (OCR+MT) translation paths
  blocks.py             Block/Box model and ordering
  config.py             typed config, profiles, LLM auto-detection
  imaging.py            frame encode/decode, overlay rendering
  glossary.py           per-profile translation glossary
  ocr/                  OCR providers (rapid, manga, tesseract)
  mt/                   translation providers (openai_compat, sugoi, argos)
  benchmark/            dataset + metrics + scoreboard CLI
openspec/               change proposals (see "Planning changes")
benchmark-data/         real screenshots + ground truth for benchmarks
docs/                   user documentation
```

## Setting up a development environment

Requirements: Python 3.10+. Note that the neural fast-path extras (sugoi,
manga-ocr) require Python <=3.12.

**Windows**

```bat
install.bat          REM creates .venv and installs the standard extras
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\vgtranslate --help
```

**Linux / macOS**

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"     # pytest + ruff
.venv/bin/vgtranslate --help
```

`vgtranslate status` shows which OCR/MT/LLM engines are available on your
machine; the fast path runs on CPU alone, the quality path needs a local
OpenAI-compatible LLM server (LM Studio / Ollama) — see
[docs/install-and-run.md](docs/install-and-run.md).

## Checks we run

Run these before opening a pull request:

```bash
ruff check .           # lint (line-length 100, py310 target)
python -m py_compile vgtranslate/*.py   # syntax check
```

There is no committed test suite yet; engine and protocol behavior is validated
through the benchmark harness and the smoke checks described below. Adding real
tests under `tests/` is a welcome contribution.

### Manual smoke checks

```bash
vgtranslate serve               # then POST a frame to /service
vgtranslate status              # engine availability
```

### Benchmark harness

Engine or prompt changes should be validated against `benchmark-data/`:

```bash
vgtranslate bench run benchmark-data        # compares the configured profile
vgtranslate bench scoreboard bench-out/report_default.json
```

Read `benchmark-data/README.md` for the current scoreboard and how the fast vs
quality paths compare. Add new samples as cropped PNG text regions plus entries
in `ground_truth.json`.

## Planning changes

This repository plans work with **OpenSpec**: proposals live under
`openspec/changes/<change-id>/` as `proposal.md`, `design.md`, `specs/`, and
`tasks.md`. This keeps the spec, the tasks, and the implementation in sync.

For anything larger than a one-line fix:

1. **Propose** — open an issue or create `openspec/changes/<change-id>/` with a
   proposal describing the problem and the intended change.
2. **Design** — agree the design and delta specs (`specs/*/spec.md`) before
   writing code; validate with `openspec validate <change-id>`.
3. **Implement** — check off tasks in `tasks.md` as you go, keeping code, specs,
   and docs consistent.
4. **Archive** — once implemented and validated, sync specs to the main spec set
   and archive the change.

## Submitting changes

1. Work on a feature branch off `master`:
   ```bash
   git checkout master && git pull
   git checkout -b fix/describe-the-change
   ```
2. Make focused commits. Keep each commit self-contained with a concise
   imperative message explaining *what* and *why*, for example:
   `Raise the request.form() part-size limit so large base64 frames are not truncated`
3. Run the checks above.
4. Open a pull request against `master`. In the description, summarize the
   change, how you tested it, and (for behavior changes) link the OpenSpec
   change or issue it addresses.

## Code conventions

- Python 3.10+ with `from __future__ import annotations` in new modules.
- Line length 100; run `ruff` before submitting.
- Keep provider interfaces stable: OCR providers implement
  `detect(image) -> list[Box]` / `ocr(image) -> list[Block]`, translation
  providers implement `translate(...) / translate_batch(...) /
  translate_frame(...)`.
- Optional engines (manga-ocr, sugoi, argos, tesseract) are optional extras:
  import them lazily, degrade gracefully, and surface availability via
  `vgtranslate status`.
- Add or update user docs (`docs/`) alongside behavior changes.

## Getting help

- Open an issue for questions or bugs.
- Read the [README](README.md) and [docs](docs/) first — most engine/setup
  questions are answered there.
- Be patient and kind: this is a small, volunteer project.
