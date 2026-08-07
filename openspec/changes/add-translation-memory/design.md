## Context

`pipeline.translate_frame` always runs OCR (or the VLM reads the frame directly)
and then calls a translation engine (MT provider or VLM) for every recognized
line, every frame. On the quality path the VLM call dominates latency
(seconds/frame on house hardware). Turn-based games reshow the same menu text
constantly, so the same lines are re-translated repeatedly. See proposal.md for
motivation; requirements live in specs/translation-memory/spec.md.

Relevant existing pieces: `Block.source_text` is available in both paths
(RapidOCR reads it on the fast path; OCR alignment already runs on the quality
path). Config is profile-based (`config.py`). Storage must be shared between the
server process and the tray app.

## Goals / Non-Goals

**Goals:**
- Durable, exact-match, text-keyed cache consulted between recognition and
  translation.
- Zero new runtime dependencies (stdlib `sqlite3`).
- Per-profile opt-in, safe concurrent access, curated entries never clobbered.

**Non-Goals:**
- Fuzzy/approximate matching of any kind.
- Image-hash / whole-frame caching (only helps when identical frames repeat,
  which RetroArch's manual mode never sends; revisit with automatic-mode
  support).
- Pack format / sharing / community distribution (future feature).
- Changing OCR or translation providers or the `/service` wire protocol.

## Decisions

### Store normalized text as the key, not a hash of it
Store the normalized source text in a UNIQUE composite column
`(source_lang, target_lang, source_text)`. Rationale: human-inspectable,
exportable, and directly fixable (seeds the future curated feature). A hash
would be opaque with no size or security benefit here. SQLite indexes the
composite key for O(log n) lookups.

### Keying on OCR text in both paths
Key off the recognized `Block.source_text`, which exists on the fast path
(RapidOCR) and on the quality path (via the OCR alignment pass). The memory
acts as a deterministic override: hits replace the translation, misses keep the
pipeline's normal behavior and (fast path) store the engine output. On the
quality path we store VLM output too — it is still better than re-running the
VLM on every repeat.

### Normalization = NFKC + case-fold + strip
Normalize via `unicodedata.normalize("NFKC", text)` (which folds half-width
kana to full-width), then `.strip()`, then Latin `.casefold()` (fold only if
the string is latin-only to avoid corrupting kana). Rationale: collapses common
OCR variants; NFKC already unifies kana width so we need no extra kana pass.

### Curated flag wins over engine output
Add a `curated` boolean column (plus a `updated_at`). Writes only happen when
the row is absent or not curated, so a manual fix is never overwritten by MT/VLM
output. The CLI's `curate` capability can be added later; for this change a row
is curated via direct DB edit or a future command — the mechanism to *respect*
it ships now.

### One shared SQLite database per user
DB path defaults to the config directory (same place as config/glossary),
overridable per profile. `sqlite3` with `WAL` mode and a busy timeout gives safe
concurrent access from server and tray. Table is created lazily on first use.

### Exact-match only, no Levenshtein
A miss on OCR jitter just means the line gets translated once more and stored.
Risky fuzzy collisions (e.g. two different item names differing by one kana)
would misrender — the spec requires exact matches only.

## Risks / Trade-offs

- **Quality-path caching stores VLM wording** → Users may prefer re-translation
  when the model improves. Mitigation: a `version` column can invalidate entries
  later; clearing the DB via the CLI is the escape hatch today.
- **OCR text as key is brittle to systematic OCR errors** → A line OCR'd wrong
  the same way every time caches the wrong translation. Mitigation: exact-match
  only; curated flag lets a human fix the entry.
- **DB grows unbounded** → A single text→text row is tiny; `stats` reports row
  counts. A cap/prune policy is a future concern.
- **Storage path on fresh config dirs** → The config directory must exist before
  opening the DB; create it on demand.

## Migration Plan

No migration: the memory is opt-in and off by default. The DB file is created
new. Rollback is simply disabling the profile toggle; nothing writes unless
enabled.

## Open Questions

None — decisions deferred (fuzzy matching, frame caching, pack format/sharing,
auto-invalidation on model version) are all explicitly out of scope and can be
revisited independently.
