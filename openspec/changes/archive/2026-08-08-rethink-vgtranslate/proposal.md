## Why

vgtranslate is a Python 2 codebase (httplib, print statements, pycrypto) that depends on paid cloud APIs — Google Vision/Translate/TTS and the ztranslate.net passthrough — and produces poor results on retro game text (tiny pixel fonts, menus, vertical text). It has a bare "hello world" Kivy app where the GUI was planned but never built. Retro gaming with Japanese text (Super Robot Wars, JRPG menus) needs a local, free, and actually *readable* translation path.

## What Changes

- **Rewrite the server as a Python 3, local-first service** that speaks RetroArch's AI Service wire protocol on `http://localhost:4404` (the `/service` endpoint): receives a paused-game screenshot, returns a translated overlay image.
- **Vision-LLM engine via LM Studio** as the quality path: one OpenAI-compatible call reads and translates the frame in one shot. Configurable base URL + model; auto-detects LM Studio (`:1234`) / Ollama (`:11434`).
- **Pluggable translation pipeline**: preprocess/upscale → detect → recognize → translate → overlay. Engines are interchangeable per stage.
- **Local OCR engines**: RapidOCR (default, CJK, CPU-fast) and manga-ocr (pixel/stylized JP text), with Tesseract as fallback.
- **Local translation engines**: Sugoi (JP→EN, tuned for game text) and Argos (other languages); LLM/VLM used for the quality path.
- **User-editable glossary**: name/term dictionary (mechs, attacks, characters) applied to translations for consistency.
- **Minimal tray GUI** (Windows + Linux): start/stop server, live logs, settings (LM Studio detection, engine/profile selection, glossary editing).
- **Benchmark harness**: a set of real failing screenshots with ground truth, scored per engine, to drive engine selection with data instead of vibes.
- **Config rework**: typed settings with per-game profiles.
- **BREAKING**: Python 2 support dropped. Google/ztranslate cloud APIs removed as required path (may return later as optional providers behind the same interface). `config.json` schema and CLI change. Existing dead modules (`opencv_engine.py`, `ocr_texter.py`, `notes.py`, `pyocr_util.py`) removed.

## Capabilities

### New Capabilities
- `retroarch-service`: RetroArch AI-service-compatible HTTP endpoint — request/response wire contract, image/text/sound outputs, BGR image format, pause/state handling.
- `translation-pipeline`: end-to-end frame → overlay pipeline with pluggable stages and fitted-text overlay rendering into detected text regions.
- `ocr-engines`: local OCR providers (RapidOCR, manga-ocr, Tesseract) behind a common detect/recognize interface, including upscaling for small pixel fonts.
- `translation-engines`: local MT providers (Sugoi, Argos) plus OpenAI-compatible LLM/VLM client (LM Studio/Ollama) behind a common translate interface.
- `glossary`: user-editable term/name dictionary applied to translations.
- `tray-app`: minimal desktop tray app — server start/stop, live logs, settings, LM Studio detection.
- `benchmark-harness`: screenshot dataset with ground truth and per-engine scoring (detection, CER, end-to-end usability).
- `config`: typed configuration model, per-game profiles, and engine/provider settings.

### Modified Capabilities
<!-- None: no existing specs in openspec/specs/ -->

## Impact

- **Code**: full rewrite of `vgtranslate/` (serve.py, config.py, util.py, imaging.py, ocr_tools.py, pyocr_util.py, ocr_texter.py, opencv_engine.py, screen_translate.py, server_client.py, text_to_speech.py, app.py, notes.py) into a Python 3 package.
- **Packaging**: `setup.py` (Python 2) → modern `pyproject.toml`.
- **Dependencies (new)**: rapidocr-onnxruntime, manga-ocr (optional), sugoi/argos (optional), httpx, pystray, Pillow, numpy. LM Studio/Ollama as external LLM host (not bundled).
- **Dependencies (removed)**: pycrypto, pyttsx, Kivy stub, pyocr ctypes hack.
- **External systems**: LM Studio (or Ollama) running locally; RetroArch configured with `AI Service URL = http://localhost:4404`.
- **Config**: `config.json` schema replaced by a typed settings file (profiles, engines, glossary, server).
