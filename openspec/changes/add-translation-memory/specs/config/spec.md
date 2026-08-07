## ADDED Requirements

### Requirement: Translation memory profile settings
Profiles SHALL support configuring the translation memory with an enable toggle
and a database path, where an unset path defaults to the config directory.

#### Scenario: Enabled profile
- **WHEN** a profile enables the translation memory
- **THEN** the pipeline uses it for lookups and storage

#### Scenario: Default database path
- **WHEN** a profile enables the memory without setting a path
- **THEN** the memory database is created in the config directory

#### Scenario: Invalid path rejected
- **WHEN** a profile sets a database path that cannot be created or opened
- **THEN** the configuration is rejected with a clear error
