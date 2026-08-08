# Config

## Purpose

Define how the translation server is configured, validated, and persisted so users can start it without manual setup and switch between per-game settings. _(TBD: full purpose)_

## Requirements

### Requirement: Typed configuration model
The server SHALL load and save a typed, validated configuration (server host/port, default target language, engine selections, profiles, glossary, LLM settings). Invalid configuration SHALL produce a clear error identifying the invalid field.

#### Scenario: Valid config loads
- **WHEN** the server starts with a well-formed configuration
- **THEN** all settings are applied

#### Scenario: Invalid config rejected
- **WHEN** the configuration contains an invalid value (e.g., bad port)
- **THEN** startup fails with an error naming the invalid field

### Requirement: Per-game profiles
Configuration SHALL support named profiles, each holding: OCR provider, translation provider, upscale factor, source/target languages, glossary reference, and overlay options. One profile SHALL be active at a time.

#### Scenario: Create and activate a profile
- **WHEN** the user creates an "SRW" profile (RapidOCR + LLM, 4x upscale, ja→en) and activates it
- **THEN** translation requests use that profile's settings

#### Scenario: Profile switch
- **WHEN** the user switches the active profile
- **THEN** subsequent requests use the new profile's settings

### Requirement: Default configuration on first run
The server SHALL generate a default configuration on first run (sensible defaults: localhost:4404, RapidOCR, LLM host auto-detection, en target) so the user can start without editing files by hand.

#### Scenario: First run
- **WHEN** the server runs with no existing configuration
- **THEN** it writes a default configuration and starts with it

### Requirement: LLM host auto-detection
The server SHALL probe common local LLM endpoints (LM Studio `localhost:1234`, Ollama `localhost:11434`) and use the first reachable one as the default LLM base URL, while still allowing manual override.

#### Scenario: LM Studio detected
- **WHEN** LM Studio is listening on `localhost:1234` and no LLM URL is configured
- **THEN** the default LLM base URL is set to `http://localhost:1234/v1`

#### Scenario: Manual override
- **WHEN** the user configures a custom LLM base URL
- **THEN** auto-detection is skipped and the custom URL is used
