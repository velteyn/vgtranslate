## 1. Project scaffolding

- [x] 1.1 Create `pyproject.toml` (Python 3, package metadata, optional extras for ocr/mt engines)
- [x] 1.2 Create new `vgtranslate/` package layout (server, http_api, pipeline, blocks, ocr/, mt/, overlay, glossary, config, imaging_util, tray_app, benchmark/)
- [x] 1.3 Remove Python 2 modules and dead code (serve.py, app.py, notes.py, opencv_engine.py, ocr_texter.py, pyocr_util.py, screen_translate.py, server_client.py, setup.py)
- [x] 1.4 Port reusable assets: fonts/ and fitted-text rendering concepts from imaging.py/util.py into imaging_util.py

## 2. Config module

- [x] 2.1 Define typed Config dataclasses (server, default target, profiles, glossary, llm) with validation and clear errors
- [x] 2.2 Implement config load/save + default config generation on first run
- [x] 2.3 Implement named per-game profiles with an active-profile pointer (OCR provider, MT provider, upscale, languages, glossary)
- [x] 2.4 Implement LLM host auto-detection (probe LM Studio :1234, Ollama :11434) with manual override

## 3. Core data model and image utilities

- [x] 3.1 Define `Block` model (box, source_text, translation, confidence, target_lang) and frame encode/decode helpers (base64, png/bmp, BGR output)
- [x] 3.2 Implement integer nearest-neighbor upscale + optional color-isolation preprocessing (ported, off by default)

## 4. RetroArch-compatible HTTP endpoint

- [x] 4.1 Implement `Server` class (start/stop/status) hosting the HTTP endpoint on localhost:4404
- [x] 4.2 Implement `/service` POST handler: parse query params (source_lang, target_lang, output) and body (image, format, coords, viewport, state)
- [x] 4.3 Implement response building: image output (24-bit BGR BMP, native resolution, png/png-a), error responses, honor target_lang default
- [x] 4.4 Support text output (text + text_position) when requested
- [x] 4.5 Read state.paused and support optional `press: ["unpause"]`
- [x] 4.6 Add health/status endpoint for the tray app (server state, engine availability)

## 5. Pipeline orchestration

- [x] 5.1 Implement pipeline runner composing stages from a profile (preprocess → detect → recognize → translate → overlay → encode)
- [x] 5.2 Implement quality path (frame-capable VLM read+translate) and fast path (OCR detect/recognize + text MT)
- [x] 5.3 Implement overlay rendering: fitted text into native-res boxes with CJK font fallback
- [x] 5.4 Implement ordered-region mapping so translations land in the correct boxes

## 6. LLM/VLM OpenAI-compatible client

- [x] 6.1 Implement `OpenAICompatTranslator` (httpx client, configurable base_url + model, chat completions with image content)
- [x] 6.2 Implement connection testing + model listing (GET /v1/models) for tray app + config auto-detection
- [x] 6.3 Implement VLM prompt with glossary guidance and JSON region output (text + box), parsing into Blocks

## 7. OCR providers

- [x] 7.1 Define OCR provider interface (detect/recognize, blocks with boxes + confidence)
- [x] 7.2 Implement RapidOCR provider (default, ONNX, CPU)
- [x] 7.3 Implement manga-ocr provider (optional extra, stylized/pixel JP text)
- [x] 7.4 Implement Tesseract fallback provider
- [x] 7.5 Implement engine availability detection (installed vs missing) surfaced in status

## 8. MT providers

- [x] 8.1 Define translation provider interface (text-only vs frame-capable)
- [x] 8.2 Implement Sugoi provider (JP→EN, optional extra)
- [x] 8.3 Implement Argos provider (other languages, optional extra)

## 9. Glossary

- [x] 9.1 Implement glossary storage + loading (persisted, per-profile)
- [x] 9.2 Apply glossary via LLM prompt injection and via MT post-processing

## 10. Benchmark harness

- [x] 10.1 Implement benchmark dataset structure (images + ground_truth.json with metadata)
- [x] 10.2 Implement metrics (detection hit rate, CER, end-to-end usability)
- [x] 10.3 Implement comparison report (scoreboard) + headless CLI
- [x] 10.4 Gather first benchmark set: real failing screenshots (Super Robot Wars dialogue/menus, Megaman) with ground truth

## 11. Engine selection via benchmark

- [x] 11.1 Run benchmark comparing VLM-coords vs RapidOCR-detect paths on SRW frames
- [x] 11.2 Run benchmark on pixel-font (Megaman) frames for manga-ocr vs RapidOCR vs VLM
- [x] 11.3 Decide and set default profile(s) from measured results (document choices)

## 12. Tray app

- [x] 12.1 Implement pystray tray icon/menu (start/stop server, show logs, settings, quit) for Windows + Linux
- [x] 12.2 Implement logs view (logging handler → queue → Tk window)
- [x] 12.3 Implement settings window (LLM URL/model, profile select, glossary editing) persisting to config
- [x] 12.4 Implement hide-to-tray behavior (no always-on main window)

## 13. End-to-end validation

- [x] 13.1 Validate protocol against a real RetroArch instance (pause → translate → overlay aligns at native res, BGR correct)
- [x] 13.2 Validate LM Studio integration end-to-end (quality path on an SRW screenshot)
- [x] 13.3 Validate fast path (RapidOCR + Sugoi) on CPU

## 14. Packaging and docs

- [x] 14.1 Write install/run docs (pyproject extras, LM Studio model setup, RetroArch AI Service URL config)
- [x] 14.2 Write config + profile + glossary documentation
- [x] 14.3 Update README for the new local-first workflow
