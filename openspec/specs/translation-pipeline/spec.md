# Translation Pipeline

## Purpose

Define the end-to-end stage pipeline that converts an input game frame into a translated overlay using pluggable OCR, translation, and rendering stages. _(TBD: full purpose)_

## Requirements

### Requirement: End-to-end frame translation
The pipeline SHALL transform an input frame into a translated overlay: decode the frame, optionally preprocess/upscale it for reading, detect text regions, recognize/translate the text, draw the translated text into the detected regions at native resolution, and return the composited frame.

#### Scenario: Full pipeline run
- **WHEN** the server receives a request with a Japanese game frame
- **THEN** the response contains an overlay frame with English text drawn in the original text regions

#### Scenario: Empty frame
- **WHEN** the input frame contains no text
- **THEN** the pipeline returns an error ("no text found") without crashing

### Requirement: Pluggable pipeline stages
The pipeline SHALL be composed of independent, replaceable stages behind common interfaces: text-region detection, recognition, translation, and overlay rendering. Each stage SHALL be selectable via configuration without changing other stages.

#### Scenario: Swap OCR engine
- **WHEN** the configured OCR provider is changed from RapidOCR to manga-ocr
- **THEN** the rest of the pipeline (translate, overlay) runs unchanged

#### Scenario: Swap translation engine
- **WHEN** the configured translation provider is changed from Sugoi to the LLM engine
- **THEN** detection and overlay stages run unchanged

### Requirement: Upscaling for small text
The pipeline SHALL be able to integer-upscale the frame (nearest-neighbor) before detection/recognition when the configured profile enables it, so small pixel fonts become readable. The overlay SHALL always be rendered at native resolution.

#### Scenario: Upscale enabled
- **WHEN** a profile has upscale factor 4 and receives a 256x224 frame
- **THEN** the OCR/VLM stage receives a 1024x896 image while the returned overlay is 256x224

### Requirement: Overlay rendering with fitted text
The overlay stage SHALL draw each translation into its detected text-region box at native resolution, fitting the text (font size and wrapping) to the box dimensions. It SHALL support CJK fonts and fall back to a configured font when glyphs are missing.

#### Scenario: Text fits into dialogue box
- **WHEN** a translated line is longer than the source region's width
- **THEN** the overlay wraps and scales the text to fit within the region bounds

#### Scenario: CJK target font
- **WHEN** the target language requires CJK glyphs
- **THEN** the overlay uses a font that renders those glyphs

### Requirement: Ordered text regions
The pipeline SHALL maintain a consistent reading order between detected text regions and their translations, so each translation is drawn into the correct region.

#### Scenario: Reading order preserved
- **WHEN** a frame contains multiple text regions
- **THEN** each region receives the translation corresponding to its detected text
