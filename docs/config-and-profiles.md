# Configuration, profiles & glossary

Configuration lives in a single JSON file:

- Linux: `~/.config/vgtranslate/config.json` (or `$XDG_CONFIG_HOME/vgtranslate/config.json`)
- Windows: `%APPDATA%\vgtranslate\config.json`

A default config is written automatically on first run. You can point any command
at a different file with `--config PATH`. The tray app (Settings window) edits the
same file.

## Schema

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 4404,
    "default_target": "en",
    "auto_unpause": false
  },
  "llm": {
    "base_url": "http://localhost:1234/v1",
    "model": "qwen2.5-vl-7b-instruct",
    "timeout": 90,
    "temperature": 0.1,
    "json_mode": true
  },
  "active_profile": "default",
  "profiles": {
    "default": {
      "mode": "quality",
      "ocr": "rapid",
      "translator": "openai",
      "upscale": 2,
      "color_isolation": false,
      "source_lang": "ja",
      "target_lang": "en",
      "glossary": "default"
    }
  },
  "glossaries": {
    "default": {
      "ビームライフル": "Beam Rifle",
      "アムロ・レイ": "Amuro Ray"
    }
  }
}
```

## Server settings

| Key | Meaning |
|---|---|
| `host` / `port` | Bind address for the RetroArch endpoint (default `127.0.0.1:4404`). |
| `default_target` | Language used when a request has no `target_lang` (default `en`). |
| `auto_unpause` | When `true` and the game reports itself paused, the response includes `press: ["unpause"]` so RetroArch resumes automatically after translation. |

## LLM settings

| Key | Meaning |
|---|---|
| `base_url` | OpenAI-compatible endpoint root, e.g. `http://localhost:1234/v1`. Set by `vgtranslate serve --detect-llm` or `vgtranslate detect`. |
| `model` | Model id to use for the quality path. |
| `timeout` | Seconds to wait for a completion (default 90). |
| `temperature` | Sampling temperature; keep low for translation (default 0.1). |
| `json_mode` | Request `response_format: {type: json_object}`; some servers reject it and vgtranslate retries without it automatically. |

## Profiles

A profile fixes the full translation recipe for one game. Set `active_profile` to
the profile you want served (or switch from the tray app).

| Key | Values | Default | Meaning |
|---|---|---|---|
| `mode` | `quality` / `fast` | `quality` | `quality` = vision LLM reads+translates the whole frame; `fast` = OCR then text MT. |
| `ocr` | `rapid` / `manga` / `tesseract` | `rapid` | OCR engine for the fast path. |
| `translator` | `openai` / `sugoi` / `argos` | `openai` | MT engine. `openai` is frame-capable (used by `quality`). |
| `upscale` | integer ≥ 1 | `2` | Nearest-neighbor upscale applied before OCR/VLM; boxes are mapped back to native resolution. |
| `color_isolation` | bool | `false` | High-contrast preprocessing before OCR (occasionally helps noisy frames). |
| `source_lang` | BCP-47, e.g. `ja` | `ja` | Source language. |
| `target_lang` | BCP-47, e.g. `en` | `en` | Translation target. |
| `glossary` | glossary name | `default` | Which glossary to apply for this profile. |

Example for Megaman (pixel fonts → manga-ocr):

```json
{
  "active_profile": "megaman",
  "profiles": {
    "megaman": {
      "mode": "quality",
      "ocr": "manga",
      "translator": "openai",
      "upscale": 4,
      "color_isolation": false,
      "source_lang": "ja",
      "target_lang": "en",
      "glossary": "megaman"
    }
  }
}
```

## Glossaries

Glossaries fix the translation of names and jargon. Each profile references one
by name. Entries are `"source => target"` pairs.

Two application points:

1. **Prompt injection** — on the quality path the terms are listed in the LLM
   system prompt so the model uses them.
2. **Post-processing** — for text MT engines (Sugoi/Argos) the terms are patched
   into the translation afterward (longest match first).

```json
{
  "glossaries": {
    "default": {
      "ゼロ": "Zero",
      "ロックマン": "Mega Man",
      "ビームライフル": "Beam Rifle"
    }
  }
}
```

Longest terms win, so `ビームライフル` ("Beam Rifle") replaces before the
shorter `ビーム` would.

## Request/response override

The server is fully driven by RetroArch's request too:

- `source_lang` / `target_lang` query params override the profile defaults.
- `output` ∈ `image` (default) / `text` / `both` chooses what the response
  contains.
- `state` (`{"paused": true}`) enables the optional `press: ["unpause"]` reply.

## Troubleshooting

- **`vgtranslate status` shows `rapid ... missing`** — install the extra:
  `pip install "vgtranslate[ocr]"`.
- **Quality path errors with "LLM not configured"** — set `llm.base_url`/`model`
  (tray Settings, or `vgtranslate serve --detect-llm`).
- **No overlay in RetroArch** — confirm the AI Service URL, that RetroArch
  reports the game paused, and check the server log window for the request.
