## ADDED Requirements

### Requirement: Translation memory consultation
The pipeline SHALL consult the configured translation memory after text
recognition and before translation: recognized lines with a memory hit SHALL
use the stored translation and the translation engine SHALL NOT be called for
them; lines with no entry SHALL be translated normally and the result SHALL be
stored unless the matching entry is curated.

#### Scenario: Memory hit skips translation engine
- **WHEN** a recognized line matches a stored entry
- **THEN** the stored translation is used and no MT/VLM call is made for that
  line

#### Scenario: Memory miss stores result
- **WHEN** a recognized line has no stored entry
- **THEN** the translation engine translates it and the result is stored for
  future frames

#### Scenario: Memory disabled
- **WHEN** the active profile does not enable the translation memory
- **THEN** the pipeline behaves as today and never stores or consults entries
