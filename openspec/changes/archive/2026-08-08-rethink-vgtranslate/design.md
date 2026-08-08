## Context

vgtranslate is a Python 2 server (BaseHTTPServer, httplib, print statements) that proxies or drives cloud OCR/MT APIs (Google Vision/Translate, ztranslate.net passthrough) for RetroArch's AI Service. It produces poor results on retro game text, is configured through a fragile `config.json`, and its GUI was never built (`app.py` is a Kivy hello-world). The rethink targets a **local-first, free, offline** workflow: the player pauses a retro game in RetroArch, presses the AI hotkey, and RetroArch POSTs the paused frame to the server, which returns a translated overlay image.

Confirmed constraints from the exploration:
- RetroArch speaks a documented wire protocol (docs.libretro.com/guides/ai-service). The server must implement it exactly (image output in 24-bit BGR, optional text output, `state.paused`, `press` control).
- User has an NVIDIA GPU with 8GB VRAM → can run a 7-8B Q4 vision LLM (Qwen2.5-VL / Qwen3-VL) via LM Studio.
- Usage is pause-based (turn-based JRPGs, menus), so latency of seconds is acceptable; realtime is not required for v1.
- Target games: Super Robot Wars (clean proportional JP font, menus/dialogue, name-heavy), Megaman (tiny pixel fonts).

## Goals / Non-Goals

**Goals:**
- Python 3 rewrite that can be installed and run offline on Windows and Linux.
- A single HTTP endpoint compatible with RetroArch's AI Service; the old ztranslate passthrough and Google cloud paths are dropped as defaults.
- Pluggable pipeline stages so engines can be swapped per game profile.
- Quality-first translation via a local vision LLM (LM Studio / Ollama, OpenAI-compatible API), with a local fast path (RapidOCR + Sugoi/Argos) as fallback.
- User-editable glossary so mech/attack/character names translate consistently.
- Minimal tray GUI: start/stop, logs, settings, engine status.
- Benchmark harness to drive engine selection with measured data.

**Non-Goals:**
- Realtime/continuous translation (RetroArch continuous mode) — pause-based only for v1; the `auto`/`continue` response fields are stubbed but not required.
- Bundling or managing LLM models — LM Studio/Ollama own downloads and VRAM.
- Cloud providers as first-class config — the OpenAI-compatible client keeps them possible but out of scope.
- TTS/sound output in v1 (protocol-compatible `sound` field may be returned as an error if requested).
- Web dashboard or multi-user features.

## Decisions

### 1. Server-as-library, embedded by the tray app
The HTTP service is a `Server` class (start/stop/status) that the tray app embeds in-process. RetroArch never talks to the tray app — only to the server's port. This makes start/stop trivial and keeps logs in one process.

**Alternatives considered:** separate daemon process managed by the tray app (more isolation, more moving parts). In-process is simpler and adequate for single-user localhost.

### 2. HTTP layer: FastAPI + uvicorn
One route (`/service`) plus a health check. FastAPI gives clean JSON handling, query params, and a dev server; uvicorn is fine for localhost single-user load. The handler ignores the path so RetroArch works with `http://localhost:4404` (any path).

**Alternatives:** plain `http.server` (fewer deps but manual JSON/BGR handling, more code to test). FastAPI chosen for maintainability; it's a common, well-supported dependency.

### 3. Pipeline of pluggable stages over a common block model
A `Block` data object: `{box, source_text, translation, confidence, target_lang}`. Stages:

```
frame ─▶ preprocess/upscale ─▶ detect ─▶ recognize ─▶ translate ─▶ overlay ─▶ encode
```

- `preprocess`: optional integer nearest-neighbor upscale (read path only) and optional color isolation (ported from the old `util.py`, per-profile, off by default).
- `detect` / `recognize`: provider interfaces from the `ocr-engines` spec.
- `translate`: provider interface from the `translation-engines` spec; may be frame-capable (VLM) or text-only.
- `overlay`: fitted-text rendering at native resolution; `encode`: output image in the requested format (default BMP, 24-bit BGR).

Profiles bind concrete providers to each stage.

### 4. Quality path = vision LLM one-shot; fast path = OCR + MT
Two pipeline compositions, chosen by profile:

- **Quality path** (default for SRW-style games): frame → (optional upscale) → VLM prompt: "read all text, return JSON of regions with text + translation" → glossary guidance in the prompt → overlay. One model call does read + translate.
- **Fast path** (CPU, for high-volume or weak-GPU machines): frame → upscale → RapidOCR (detect+recognize) → Sugoi/Argos → glossary post-process → overlay.

Rationale: the VLM reads stylized/pixel text far better than classical OCR and handles context (names, honorifics, vertical text). The fast path exists so the tool works without a GPU and for realtime-ish use later.

### 5. Region boxes for overlay: VLM-coords first, hybrid fallback
The overlay needs boxes. Two options were explored: VLM returns coordinates in its JSON output, or RapidOCR detects boxes while the VLM/MT translates. **Decision: start with VLM-supplied boxes** (fewer moving parts); if the benchmark shows coordinate drift, add a hybrid mode where RapidOCR detects boxes and a recognizer/translator fills text. Both produce the same `Block` list, so the pipeline interface doesn't change.

### 6. OpenAI-compatible LLM client
One HTTP client (httpx) speaks `POST {base}/chat/completions` with text or image content, configurable `base_url` and `model`. Auto-detection probes `localhost:1234/v1/models` (LM Studio) then `localhost:11434/v1/models` (Ollama). Works unchanged against a cloud endpoint later.

### 7. Overlay: fitted-text into native-res boxes (port from imaging.py)
The old `imaging.py` (font fitting, wrapping, CJK font switching, `drawTextBox`) is ported and kept as the overlay engine. Fonts already shipped in `fonts/` (Roboto + Noto Sans CJK TC) are reused. The overlay always draws at native resolution so the returned image aligns with RetroArch's `coords`/`viewport`.

### 8. Image output: BMP 24-bit BGR by default
BMP natively stores 24-bit BGR, so returning BMP from Pillow matches RetroArch's requirement with no manual channel swap. `png`/`png-a` are supported for alpha overlay needs. The old `swap_red_blue` BGR special-case is removed.

### 9. Tray app: pystray + Tkinter
- `pystray` for the tray icon/menu (Windows + Linux), `tkinter` for logs/settings windows.
- Server logs are captured through a `logging.Handler` pushing to a `queue.Queue` that the logs window tails.
- Settings window edits config (LLM URL/model, profile, glossary) and persists via the config module.
- No always-on main window; closing windows hides to tray.

**Alternatives:** Kivy (repo's old plan — heavy, weak tray support), PySide6 (nicer widgets but a much bigger dependency). pystray+Tkinter is the minimal cross-platform fit.

### 10. Config: typed dataclasses + JSON file
`Config` dataclass (server, default target, profiles, glossary, llm), load/save/validate with clear error messages. First run writes a default config. Profiles are a dict keyed by name with an `active` pointer. Port/config UI are the only entry points; no hand-editing required (but the file stays readable).

### 11. Optional engine extras (packaging)
`pyproject.toml` with optional extras so heavy/optional engines don't force installs:
- base: httpx, fastapi, uvicorn, pydantic, Pillow, numpy, pystray
- `ocr`: rapidocr-onnxruntime
- `ocr-manga`: manga-ocr + torch (optional, heavy)
- `mt-sugoi`: sugoi (optional)
- `mt-argos`: argos-translate (optional)
- `tesseract`: pytesseract (fallback)

### 12. Benchmark harness as a CLI
A `benchmark/` subpackage: dataset directory (images + `ground_truth.json`) + CLI `vg-bench` that runs pipeline configs over the dataset and writes a scored report (detection hit rate, CER, usability). It reuses the same pipeline code the server uses, so it measures the real system. First dataset = screenshots gathered during this change's implementation.

## Risks / Trade-offs

- **[Risk] VLM-supplied boxes drift from true text positions** → Mitigation: hybrid detect (RapidOCR) + translate mode is a designed fallback; benchmark validates before v1 ships.
- **[Risk] 8GB VRAM is tight for vision LLMs (Q4 7-8B ~4.5GB + KV cache)** → Mitigation: recommend Qwen2.5-VL-7B / Qwen3-VL-8B Q4; document VRAM headroom; fast path (RapidOCR+Sugoi, CPU) is always available.
- **[Risk] Local MT quality below Google for generic text** → Mitigation: Sugoi is game/VN-tuned, glossary handles names, and the VLM path is the primary quality engine; benchmark measures usability, not just CER.
- **[Risk] RetroArch protocol edge cases (BGR, image sizing, `text`/`press` fields)** → Mitigation: protocol implemented from the documented contract and validated against a real RetroArch instance early (first task).
- **[Risk] Language coverage beyond JP→EN is weaker locally** → Mitigation: Argos/NLLB provider covers other pairs; documented as a known quality ceiling.
- **[Risk] First-run model downloads confuse users** → Mitigation: tray app surfaces engine availability + LM Studio detection; docs cover model setup.

## Migration Plan

- This is a rewrite. Old Python 2 modules are not migrated incrementally; the new package replaces `vgtranslate/`, and `setup.py` is replaced by `pyproject.toml`.
- Old `config.json` is not read; a fresh default config is generated. Users reconfigure via the tray app (LM Studio model selection + profile).
- Deployment is per-machine (single user), so there is no server migration; rollback = run the old branch.
- The old repo's screenshots-saving and font assets are reused where useful.

## Open Questions

- Which Super Robot Wars entry(ies) to target for the first benchmark set, and at what core resolution (GBA 240x160 vs SNES 256x224 vs GB)?
- Whether Megaman's realtime path is needed in v1 or only the quality path (decided during benchmark).
- Preferred overlay style for menus: replace text in place (native-res fitted text) vs. boxed subtitle region — to confirm with screenshots.
