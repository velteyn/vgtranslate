## Why

Repeated game text (menus, battle commands, item names, recurring dialogue) is
translated from scratch on every frame. On house hardware the quality path's
VLM call costs seconds per frame, so turn-based games whose menus repeat
constantly pay that cost over and over for the same text. A durable, text-keyed
translation memory lets previously translated lines be reused instantly and
deterministically, skipping the slow translation step entirely.

## What Changes

- Add a SQLite-backed translation memory: a mapping from `(source_lang,
  target_lang, normalized source text)` to a stored translation.
- The pipeline consults the memory after text recognition and before
  translation: on a hit the stored translation is used and no MT/VLM call is
  made; on a miss the line is translated and the result is stored.
- Normalization (NFKC, kana width, Latin case, trimming) so OCR variants of the
  same line collide on purpose.
- Strict exact-match lookup only: two different lines must never collide.
  Fuzzy matching is intentionally out of scope for this change.
- A `curated` flag so a manually fixed entry cannot be silently overwritten by
  future MT/VLM output.
- Per-profile configuration: enable/disable the memory and choose its database
  path (defaults to the config directory). Off by default.
- A `vgtranslate memory` CLI with `stats` and `clear` subcommands.

## Capabilities

### New Capabilities
- `translation-memory`: durable, SQLite-backed, text-keyed storage of source
  text to translation pairs, with exact-match lookup and per-profile
  configuration.

### Modified Capabilities
- `translation-pipeline`: the frame translation flow gains a memory lookup
  stage between text recognition and translation.
- `config`: profiles gain a translation-memory section (enable flag, database
  path).

## Impact

- New module `vgtranslate/memory.py` (SQLite via stdlib `sqlite3`; no new
  dependencies).
- `vgtranslate/pipeline.py`: lookup/store calls in `translate_frame`.
- `vgtranslate/config.py`: new profile fields and validation.
- `vgtranslate/cli.py` (or existing command surface): `vgtranslate memory`
  subcommands.
- `docs/`: config reference and user guide updates.
- Overlay rendering, OCR/MT providers, and the RetroArch `/service` protocol are
  unchanged.
