## Purpose

Durable storage of source-text to translation pairs so repeated game text is
translated once and then reused instantly and deterministically.

## ADDED Requirements

### Requirement: Text-keyed lookup
The translation memory SHALL store and retrieve translations keyed by the
normalized source text together with the source and target language pair.

#### Scenario: Repeated line hit
- **WHEN** the pipeline recognizes a source line whose normalized text and
  language pair already have a stored translation
- **THEN** the stored translation is returned without calling the translation
  engine

#### Scenario: Language pair isolation
- **WHEN** the same source text is requested with a different target language
- **THEN** the lookup misses and the line is translated normally

### Requirement: Normalization for lookup
The translation memory SHALL normalize source text before lookup using NFKC
normalization, half/full-width kana unification, Latin case folding, and
whitespace trimming, so OCR variants of the same line resolve to the same key.

#### Scenario: Half-width kana variant
- **WHEN** OCR produces half-width `ﾋﾞｰﾑ` for a line previously stored as
  full-width `ビーム`
- **THEN** the lookup returns the stored translation

#### Scenario: Case variant
- **WHEN** OCR produces `ITEM` for a stored line `item`
- **THEN** the lookup returns the stored translation

### Requirement: Exact-match safety
The translation memory SHALL match only on the exact normalized key; two
different source lines SHALL never resolve to the same stored translation
through fuzzy or approximate matching.

#### Scenario: Distinct lines stay distinct
- **WHEN** two lines differ by a single character
- **THEN** each line resolves to its own stored translation, or misses if not
  present

### Requirement: Curated entries protected
The translation memory SHALL distinguish curated entries from machine-produced
entries, and SHALL NOT overwrite a curated entry with newly produced
translation-engine output.

#### Scenario: Manual fix preserved
- **WHEN** an entry is marked curated and a later translation pass produces a
  different result for the same line
- **THEN** the curated translation remains stored and is used

### Requirement: Persistent storage
The translation memory SHALL persist across server restarts in a local database
file, and SHALL support inspecting and clearing its contents via the CLI.

#### Scenario: Survives restart
- **WHEN** the server restarts
- **THEN** previously stored translations remain available

#### Scenario: Clear command
- **WHEN** the user runs the memory clear command
- **THEN** the memory is emptied

### Requirement: Opt-in by profile
The translation memory SHALL be disabled unless a profile explicitly enables it.

#### Scenario: Disabled by default
- **WHEN** no profile enables the translation memory
- **THEN** the pipeline performs lookups without consulting the memory
