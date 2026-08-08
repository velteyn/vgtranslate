## ADDED Requirements

### Requirement: RetroArch-compatible service endpoint
The server SHALL expose an HTTP endpoint compatible with RetroArch's AI Service. It SHALL accept POST requests (to `/service` or any path) with query parameters `source_lang`, `target_lang`, and `output` (comma-separated formats), and a JSON body containing `image` (base64-encoded frame), `format` (`png` or `bmp`), `coords`, `viewport`, and `state`. It SHALL respond with HTTP 200 and a JSON payload containing at least one of `image`, `sound`, `text`, or `error`.

#### Scenario: Basic translation request
- **WHEN** RetroArch POSTs a frame with `image`, `format: png`, `target_lang: En`, and `output: image`
- **THEN** the server responds 200 with JSON containing an `image` field

#### Scenario: Request with unknown path
- **WHEN** RetroArch POSTs to a path other than `/service` (e.g. `/`)
- **THEN** the server still processes the request and returns a valid response

#### Scenario: Output format parsing
- **WHEN** the `output` query parameter is `image,png-a`
- **THEN** the server returns the image in the requested sub-format if supported, otherwise in the default `bmp`

### Requirement: Image output in 24-bit BGR
When `image` is in the requested `output` formats, the server SHALL return a base64-encoded image that RetroArch can overlay on the viewport. The returned image SHALL be 24-bit BGR order and use a supported format (`bmp`, `png`, or `png-a`), and SHALL match the dimensions of the input frame so it aligns with `coords`/`viewport`.

#### Scenario: Image returned in BGR BMP
- **WHEN** RetroArch requests `output: image` for a 256x224 frame
- **THEN** the response contains a base64 `image` field decoding to a 256x224 24-bit BMP with correct color channels

#### Scenario: Native resolution preserved
- **WHEN** a request is processed with an internally upscaled frame for reading
- **THEN** the returned image is still at the input frame's native resolution

### Requirement: Text output
When `text` is in the requested `output` formats, the server SHALL return a `text` field containing the translated text as a string, and MAY return `text_position` (1 for bottom, 2 for top) as a hint.

#### Scenario: Text mode request
- **WHEN** RetroArch requests `output: text` and the translation succeeds
- **THEN** the response contains a `text` string and optionally `text_position`

### Requirement: Error responses
When processing fails (e.g., no text found, engine unavailable, decode failure), the server SHALL return a JSON payload with an `error` field describing the problem. When `error` is present, RetroArch ignores all other fields.

#### Scenario: No text found
- **WHEN** the pipeline detects no readable text in the frame
- **THEN** the response contains an `error` field explaining that no text was found

#### Scenario: Engine unavailable
- **WHEN** the configured translation engine is not available (e.g., LM Studio not running)
- **THEN** the response contains an `error` field identifying the unavailable engine

### Requirement: Frontend state and control
The server SHALL read the `state.paused` flag from the request body. It MAY return a `press` list containing `pause` or `unpause` to control RetroArch's pause flow.

#### Scenario: Paused frame translated
- **WHEN** RetroArch sends a request with `state.paused: 1`
- **THEN** the server processes the frame normally and may include `press: ["unpause"]` in the response

### Requirement: Language parameters
The server SHALL honor `source_lang` and `target_lang` query parameters, defaulting `target_lang` to the configured default (e.g. `En`) when omitted.

#### Scenario: Target language honored
- **WHEN** RetroArch requests `target_lang: En`
- **THEN** the translated text is produced in English

#### Scenario: Default target language
- **WHEN** RetroArch omits `target_lang`
- **THEN** the server uses the configured default target language
