# Glossary

## Purpose

Provide user-editable per-profile name dictionaries so game-specific terms (e.g., proper nouns) are translated consistently. _(TBD: full purpose)_

## Requirements

### Requirement: Editable glossary
The server SHALL support a user-editable glossary mapping source terms (e.g., ビームライフル) to preferred translations (e.g., "Beam Rifle"). Glossaries SHALL be stored in configuration and editable through the GUI.

#### Scenario: Add a glossary entry
- **WHEN** the user adds the term ビームライフル with translation "Beam Rifle"
- **THEN** the glossary persists the entry in configuration

#### Scenario: Glossary loaded at startup
- **WHEN** the server starts with a saved glossary
- **THEN** the glossary entries are loaded and applied during translation

### Requirement: Glossary applied consistently
The glossary SHALL be applied to every translation of a session, so the same term is always rendered the same way. Application SHALL work for both translation paths: injected as guidance for the LLM/VLM prompt, and applied as post-processing for text-only MT engines.

#### Scenario: Term applied in LLM path
- **WHEN** a VLM translates a frame containing a glossary term
- **THEN** the glossary term's preferred translation is used in the output

#### Scenario: Term applied in MT path
- **WHEN** a text-only MT engine translates text containing a glossary term
- **THEN** the term is post-processed to the preferred translation

### Requirement: Per-profile glossaries
Each game profile SHALL be able to reference its own glossary (or the default one), so different games can have different name dictionaries.

#### Scenario: Profile-specific glossary
- **WHEN** a profile selects a custom glossary
- **THEN** only that glossary's terms apply within the profile
