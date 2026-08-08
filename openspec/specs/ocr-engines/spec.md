# OCR Engines

## Purpose

Define the set of interchangeable OCR providers and their common interface so detection/recognition engines can be swapped via configuration. _(TBD: full purpose)_

## Requirements

### Requirement: Common OCR provider interface
OCR providers SHALL implement a common interface exposing detection and recognition: `detect(image) -> list of text-region boxes` and `recognize(image, boxes) -> per-region text`, or an equivalent combined `ocr(image) -> blocks` operation. Providers SHALL return per-region confidence where the engine provides it.

#### Scenario: Provider returns blocks
- **WHEN** an OCR provider processes an image containing two text regions
- **THEN** it returns two blocks, each with a bounding box and text

#### Scenario: Provider swap
- **WHEN** the active OCR provider is replaced by any other provider
- **THEN** the pipeline accepts the same data shape without code changes

### Requirement: RapidOCR as default provider
The server SHALL ship with a RapidOCR (ONNX, PaddleOCR models) provider as the default local OCR engine, usable on CPU without external services.

#### Scenario: RapidOCR reads a clean JP dialogue box
- **WHEN** a high-contrast Japanese dialogue frame is processed with the RapidOCR provider
- **THEN** the recognized Japanese text is returned with region boxes

### Requirement: manga-ocr provider
The server SHALL provide a manga-ocr provider for stylized/pixelated Japanese text (as in retro pixel-font games). When enabled, recognition SHALL use the manga-ocr model, optionally combined with an external detector.

#### Scenario: Pixel-font recognition
- **WHEN** a pixel-font Japanese frame is processed with the manga-ocr provider and upscaling enabled
- **THEN** the recognized text is returned and is more accurate than the default provider for the same frame (per benchmark results)

### Requirement: Tesseract fallback provider
The server SHALL provide a Tesseract-based provider as a lightweight fallback when the other engines are not installed.

#### Scenario: Fallback available
- **WHEN** only Tesseract is installed and the profile selects it
- **THEN** the pipeline runs with Tesseract-provided text

### Requirement: Engine availability handling
Missing optional OCR engines (e.g., manga-ocr not installed) SHALL NOT crash the server. The server SHALL report the engine as unavailable in configuration/status and return a clear error if an unavailable engine is selected.

#### Scenario: Optional engine missing
- **WHEN** manga-ocr is not installed and a profile selects it
- **THEN** the request fails with a clear error identifying the missing engine, and the server keeps running

#### Scenario: Availability reported
- **WHEN** the user views engine status
- **THEN** installed vs. missing engines are listed
