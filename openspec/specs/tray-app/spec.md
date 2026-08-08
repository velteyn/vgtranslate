# Tray App

## Purpose

Provide a minimal cross-platform desktop app that runs in the system tray and controls the translation server (start/stop, logs, settings). _(TBD: full purpose)_

## Requirements

### Requirement: Tray icon with server control
The desktop app SHALL provide a system tray icon (Windows and Linux) that allows the user to start and stop the translation server, and shows whether it is running.

#### Scenario: Start server from tray
- **WHEN** the user selects "Start" from the tray menu
- **THEN** the server starts and the tray status reflects "running"

#### Scenario: Stop server from tray
- **WHEN** the user selects "Stop" from the tray menu
- **THEN** the server stops and the tray status reflects "stopped"

### Requirement: Live logs view
The app SHALL show live server logs in a window accessible from the tray, so the user can see translation requests and errors.

#### Scenario: Logs displayed
- **WHEN** the server processes a request
- **THEN** the log line appears in the logs view

### Requirement: Settings UI
The app SHALL provide a settings view (from the tray) for: LLM/VLM base URL and model, active profile, and glossary editing. Changes SHALL persist to configuration.

#### Scenario: Change LLM settings
- **WHEN** the user edits the LLM base URL or model and saves
- **THEN** the new values persist and the running server uses them on subsequent requests

#### Scenario: Edit glossary
- **WHEN** the user adds or edits a glossary entry in settings
- **THEN** the change persists and applies to subsequent translations

### Requirement: Minimal, hideable interface
The app SHALL be minimal: no always-on main window required; it SHALL run in the tray and open windows (logs/settings) on demand. Closing a window SHALL hide to tray rather than quit.

#### Scenario: Window closed hides to tray
- **WHEN** the user closes the logs or settings window
- **THEN** the app stays running in the tray

#### Scenario: Quit from tray
- **WHEN** the user selects "Quit" from the tray menu
- **THEN** the app and server shut down cleanly

### Requirement: Cross-platform (Windows + Linux)
The app SHALL run on both Windows and Linux using the same codebase.

#### Scenario: Runs on both platforms
- **WHEN** the app is launched on Windows and on Linux
- **THEN** the tray icon, start/stop, and logs work on both
