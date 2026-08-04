## ADDED Requirements

### Requirement: Common translation provider interface
Translation providers SHALL implement a common `translate(text or frame, source_lang, target_lang) -> translated text` interface. Providers SHALL expose whether they support one-shot frame translation (read + translate in a single call) or text-only translation.

#### Scenario: Text-only provider used
- **WHEN** a text-only provider (e.g., Sugoi) is active with detected OCR text
- **THEN** the OCR text is passed to the provider and the translation returned

#### Scenario: Frame-capable provider used
- **WHEN** a frame-capable provider (e.g., a vision LLM) is active
- **THEN** the provider may be given the frame directly and returns translations for its detected regions

### Requirement: OpenAI-compatible LLM/VLM client
The server SHALL provide a translation provider that talks to any OpenAI-compatible server (LM Studio, Ollama, or a cloud endpoint) over HTTP using a configurable base URL and model name. The provider SHALL support chat completion requests, including image content for vision models.

#### Scenario: LM Studio backend
- **WHEN** the base URL is set to `http://localhost:1234/v1` and LM Studio is running
- **THEN** translation requests are served by LM Studio with the configured model

#### Scenario: Ollama backend
- **WHEN** the base URL is set to `http://localhost:11434/v1` and Ollama is running
- **THEN** translation requests are served by Ollama with the configured model

#### Scenario: Vision model reads frame
- **WHEN** the configured model supports vision and the provider receives a frame
- **THEN** the model reads the frame's text and returns translations

### Requirement: Sugoi provider
The server SHALL provide a Sugoi (JP→EN) provider for game/visual-novel-style Japanese text. It SHALL be selectable in profiles and run locally.

#### Scenario: Sugoi translates JP text
- **WHEN** the Sugoi provider is active with source language Japanese and target English
- **THEN** Japanese OCR text is translated to English using the local Sugoi model

### Requirement: Argos provider
The server SHALL provide an Argos Translate provider for languages other than Japanese, enabling general-language pairs locally.

#### Scenario: Non-JP language pair
- **WHEN** the Argos provider is active for a non-Japanese source/target pair
- **THEN** the text is translated using the local Argos model for that pair

### Requirement: Connection testing
The server SHALL expose a way to test the configured LLM/VLM connection (e.g., `GET /v1/models` probe or a small request) and report whether it succeeded, with the discovered model list when available.

#### Scenario: Connection test succeeds
- **WHEN** LM Studio is running and the user tests the connection
- **THEN** the server reports success and lists available models

#### Scenario: Connection test fails
- **WHEN** the configured LLM host is not running
- **THEN** the server reports a clear connection failure
