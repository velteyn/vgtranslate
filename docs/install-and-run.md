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

RetroArch has a built-in **AI Service** feature. It pauses the game, POSTs the
current frame to the URL you configure, and renders the overlay vgtranslate
returns. **You need RetroArch v1.18.0+** — official builds only ship the AI
Service from then on (the stock 1.9.x–1.17.x APKs don't include it at all;
only custom/modded builds do).

> Tested on: RetroArch 1.22.2 (Android, Retroid Pocket) + Beetle WonderSwan core.

### 4a. Find the AI Service menu

Where the menu lives depends on the build and platform:

- **Android (Retroid/handheld) — v1.18.0+:** the AI Service menu is hidden under
  **Settings → Accessibility**. First toggle **Accessibility → Enable
  Accessibility** ON (this also powers the spoken/Speech mode), then the
  **AI Service** entry appears inside Accessibility.
- **Windows/desktop — v1.18.0+:** **Settings → AI Service** (also under the
  quick menu while a game runs).
- **Old modded 1.9.x-era builds:** the AI overlay is drawn by the on-screen
  widgets, so both **Settings → On-Screen Display → On-Screen Notifications →
  On-Screen Notifications** and **Graphics Widgets** must be ON, or the overlay
  is never drawn even though translation succeeds.

### 4b. Settings to apply

1. **AI Service → AI Service Enable** — **ON** (if it's off, the hotkey does
   nothing, not even pause).
2. **AI Service URL** — the server URL **with the trailing slash**:
   - On the device running vgtranslate: `http://localhost:4404/`
   - From a handheld on the same network: `http://<PC-LAN-IP>:4404/` — e.g.
     `http://192.168.1.242:4404/`. Use the IP the server printed at startup
     ("AI Service URL: http://192.168.1.242:4404/"). The server binds
     `0.0.0.0` by default so the handheld can reach it; allow TCP port `4404`
     through the Windows firewall.
3. **AI Service Mode** — set to **Image** so RetroArch renders the translated
   overlay (it sends `output=image,png,png-a`). Speech/TTS mode reads text
   aloud via Accessibility instead.
4. **AI Service Pause** — **ON** (default). First press of the hotkey pauses
   the game and triggers translation; a second press unpauses. Turn it off if
   you'd rather the game keeps running (Speech mode).
5. **AI Service Source/Target Language** — optional; if left as "Don't care"
   the profile defaults in vgtranslate apply (`ja` → `en`).
6. **Hotkey**: **Settings → Hotkeys → AI Service** — bind a key or pad button
   (e.g. `Select`). On a handheld, binding it to a controller button is
   easiest. This hotkey, not the pause key, triggers translation.

### 4c. Expected behavior

- Pressing the AI Service hotkey pauses the game and a request reaches the
  server (watch the server terminal). The translated overlay is drawn over the
  paused frame.
- The overlay is returned as a 24-bit BGR BMP at a higher resolution
  (`overlay_scale`, default 3×) so RetroArch renders crisp text when it
  stretches the image to the full screen.
- Each request takes a few seconds on the quality path — fine for
  turn-based / pause-driven games.
- If nothing appears in the server log when you press the hotkey, re-enter the
  AI Service URL (a stale/empty URL silently aborts the request) and confirm
  the enable toggle and hotkey are set.

### 4d. Text looks soft / low-res

That's RetroArch upscaling native-resolution text to the full screen. Raise
`overlay_scale` for the active profile in the config (e.g. `4`); the server
then renders the overlay at a higher multiple and RetroArch samples it 1:1 or
downscales — always crisp. See [config-and-profiles.md](config-and-profiles.md).

## 5. Benchmark (engine selection)

```bash
vgtranslate bench init my-srw-set --images-dir screenshots --game srw
# fill in ground_truth.json (source_text + translation per sample)
vgtranslate bench run my-srw-set
vgtranslate bench scoreboard bench-out/report_default.json ...
```

See `vgtranslate bench --help` for details.
