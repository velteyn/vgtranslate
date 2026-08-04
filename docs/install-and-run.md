# Installation & running

Everything is local and free: no Google/ztranslate accounts, no cloud calls.
You only need Python 3.10+ and, for the *quality* path, a local LLM server with a
GPU. The *fast* path runs entirely on CPU.

## 0. Windows quick start (install.bat / run.bat)

The repository ships two Windows scripts that wrap everything below — this is the
recommended way to install and run on Windows.

1. Install **Python 3.12** from [python.org](https://www.python.org/downloads/)
   (check "Add to PATH" and "py launcher" during install). Python 3.13/3.14 also
   work but cannot install the neural fast-path extras (sugoi, manga-ocr) — those
   require Python <=3.12.
2. Open a terminal in the cloned project folder and run:
   ```bat
   install.bat
   ```
   It creates `.venv`, picks the best Python it can find (3.12/3.11/3.10 first,
   then any newer), and installs `vgtranslate[ocr,ocr-manga,mt-sugoi,tray]` when
   the Python supports it, or `vgtranslate[ocr,tray]` otherwise. Override with
   `install.bat all` or `install.bat ocr,tray`.
3. Start the server:
   ```bat
   run.bat
   ```
   `run.bat` forwards any vgtranslate subcommand and its arguments, e.g.
   `run.bat tray` (tray icon), `run.bat serve --detect-llm` (probe a local
   LM Studio), `run.bat status`, or `run.bat bench ...`. Then continue at
   [Configure RetroArch](#4-configure-retroarch).

## 1. Install

```bash
pip install "vgtranslate[ocr,ocr-manga,mt-sugoi,tray]"
```

On Windows, `install.bat` (section 0) wraps these exact pip commands into a
virtual environment, so you don't need to run them by hand.

or install everything:

```bash
pip install "vgtranslate[all]"
```

The base package only brings `fastapi`, `uvicorn`, `httpx`, `Pillow` and
`pydantic` — enough to run the server, but OCR/MT engines are optional extras so
you only install what you need.

### Extra detail

- `ocr` — RapidOCR (ONNX runtime, CPU). The default OCR engine.
- `ocr-manga` — manga-ocr, better on stylized/pixel Japanese fonts. Uses
  RapidOCR or Tesseract for box detection.
- `tesseract` — pytesseract; needs a Tesseract binary plus the `jpn` language
  pack on your system.
- `mt-sugoi` — Sugoi neural JP→EN translation; downloads its model on first use.
- `mt-argos` — Argos Translate; install language packages with
  `argos-translate-manage --install-from-index`.
- `tray` — pystray for the tray GUI.

Check what's available after installing:

```bash
vgtranslate status
```

## 2. Set up a local LLM (quality path)

The quality path talks to any server exposing the OpenAI `chat/completions`
API. Two supported options:

**LM Studio** (recommended for Windows):
1. Download a vision-capable model, e.g. `Qwen2.5-VL-7B-Instruct` (Q4_K_M fits in
   ~6 GB VRAM) or `Qwen3-VL-8B-Instruct` Q4.
2. In LM Studio, load the model and start the **local server** (defaults to
   `http://localhost:1234/v1`).
3. Pick the loaded model in vgtranslate's settings (or config).

**Ollama** (Linux/macOS):
```bash
ollama pull qwen2.5vl:7b
ollama serve   # defaults to http://localhost:11434/v1
```

vgtranslate probes both endpoints automatically:

```bash
vgtranslate serve --detect-llm
```

This sets `llm.base_url` and the first available model in your config; you can
override them in the tray app (Settings) or by editing the config file.

## 3. Run the server

```bash
vgtranslate serve
```

On Windows, use `run.bat` instead (section 0) — it runs the same command from
the project's `.venv`. On Linux/macOS the equivalent of the Windows scripts is:

```bash
.venv/bin/vgtranslate serve
```

On startup it prints the URL to put in RetroArch:

```
RetroArch AI Service URL: http://localhost:4404/
```

Optional flags:

- `--detect-llm` — probe local LLM endpoints and persist the result before serving.
- `--config PATH` — use a config file at `PATH` instead of the user config dir.
- `-v` — verbose/debug logging.

For a tray icon instead of a terminal (Windows/Linux): `vgtranslate tray`.

## 4. Configure RetroArch

RetroArch has a built-in **AI Service** feature:

1. **Settings → AI Service**, or the `AI Service` entry under the quick menu.
2. Set **AI Service URL** to `http://localhost:4404/`.
3. Enable the AI Service (start it from the menu).
4. Pause the game with the configured pause key (AI Service binds to a key;
   often `F1`). vgtranslate receives the frame, translates it, and RetroArch
   shows the overlay on top.

Notes:

- The overlay is returned at native resolution as 24-bit BGR BMP, so it aligns
  exactly with the game frame.
- Output mode defaults to `output=image` (a full overlay). If you prefer to feed
  RetroArch's built-in text rendering, configure the output mode in RetroArch;
  the server also honors `output=text`.
- Each request can take several seconds on the quality path — fine for
  turn-based / pause-driven games. RetroArch stays paused while waiting.

## 5. Benchmark (engine selection)

```bash
vgtranslate bench init my-srw-set --images-dir screenshots --game srw
# fill in ground_truth.json (source_text + translation per sample)
vgtranslate bench run my-srw-set
vgtranslate bench scoreboard bench-out/report_default.json ...
```

See `vgtranslate bench --help` for details.
