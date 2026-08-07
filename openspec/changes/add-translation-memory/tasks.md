## 1. Memory module

- [ ] 1.1 Add `vgtranslate/memory.py` with a `TranslationMemory` class backed by stdlib `sqlite3`: lazy schema creation (table `entries(source_lang, target_lang, source_text, translation, curated, updated_at)` with a UNIQUE composite index), WAL mode and busy timeout
- [ ] 1.2 Implement `normalize(text) -> str` using NFKC, latin-only casefold, and strip (kana-safe)
- [ ] 1.3 Implement `lookup(source_lang, target_lang, source_text) -> Optional[str]` (exact match on normalized key)
- [ ] 1.4 Implement `store(source_lang, target_lang, source_text, translation)` that writes only when the row is absent or not curated (curated entries are never overwritten)
- [ ] 1.5 Implement `stats() -> dict` (row count, curated count) and `clear() -> int` (rows removed)
- [ ] 1.6 Ensure the DB parent directory is created on demand and open errors surface a clear message

## 2. Configuration

- [ ] 2.1 Add profile fields `translation_memory: bool` (default False) and `memory_path: Optional[str]` to the config model in `vgtranslate/config.py`
- [ ] 2.2 Validate the configured memory path: reject profiles whose path cannot be created or opened with a clear error
- [ ] 2.3 Wire a default memory path (config directory) used when the profile enables the memory without a path

## 3. Pipeline integration

- [ ] 3.1 In `pipeline.translate_frame`, instantiate the memory only when the active profile enables it (off by default, per spec)
- [ ] 3.2 After recognition and before translation, look up each block's normalized source text; on a hit, set the block's translation from the memory and skip the engine for that line
- [ ] 3.3 On a miss, translate normally and store the result (respecting the curated flag)
- [ ] 3.4 Ensure both paths (fast OCR+MT and quality VLM) consult the memory consistently, keying on recognized `Block.source_text`
- [ ] 3.5 Verify no storage or lookup happens when the memory is disabled, and that a disabled memory never changes existing behavior

## 4. CLI

- [ ] 4.1 Add `vgtranslate memory` subcommand with `stats` and `clear` subcommands in `vgtranslate/__main__.py`
- [ ] 4.2 `memory stats` prints row count, curated count, and DB path; `memory clear` removes all rows and prints the number removed

## 5. Documentation

- [ ] 5.1 Document the `translation_memory` and `memory_path` profile options in the config reference docs
- [ ] 5.2 Add a user-guide section explaining when the memory helps (repeated menu/dialogue text), that it is off by default, and how to clear it

## 6. Verification

- [ ] 6.1 Run `ruff check .` and `python -m py_compile vgtranslate/*.py`
- [ ] 6.2 Add a smoke check covering: lookup hit skips translation, miss stores, curated entry not overwritten, normalization collision (half-width vs full-width kana), and disabled profile performs no I/O
- [ ] 6.3 Run the existing smoke suite and `openspec validate add-translation-memory`
