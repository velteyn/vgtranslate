## ADDED Requirements

### Requirement: Screenshot dataset with ground truth
The benchmark harness SHALL maintain a dataset of real game screenshots with per-image ground truth: the correct source text and its expected translation, plus metadata (game, horizontal/vertical text, textbox vs. HUD/menu). Images SHALL be sourced from actual failing captures (e.g., Super Robot Wars, Megaman).

#### Scenario: Add a sample
- **WHEN** the user adds an image and its ground truth text to the dataset
- **THEN** the sample is stored with metadata and can be run in comparisons

### Requirement: Per-engine scoring
The harness SHALL run each configured engine/pipeline over the dataset and compute metrics: text-region detection hit rate, character error rate (CER) of recognized text, and an end-to-end usability flag per sample (translation readable and placed correctly).

#### Scenario: Score a pipeline
- **WHEN** the user runs the harness with a pipeline configuration
- **THEN** the harness reports detection, CER, and usability metrics across all samples

### Requirement: Comparison report
The harness SHALL produce a comparison report (scoreboard) across multiple pipelines/engines so engine choices are driven by data.

#### Scenario: Compare engines
- **WHEN** the user runs the harness over two or more engine configurations
- **THEN** the report ranks them by the recorded metrics

### Requirement: CLI invocation
The harness SHALL be runnable from the command line, headlessly, so it can be scripted and repeated.

#### Scenario: Headless run
- **WHEN** the user runs the harness CLI on a dataset
- **THEN** it prints or writes the metrics report and exits
