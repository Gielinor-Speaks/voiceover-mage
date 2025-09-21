# Project Structure & Architecture

## Current Structure
```
voiceover-mage/
├── src/voiceover_mage/
│   ├── __init__.py
│   ├── main.py          # Application entry point (CLI)
│   ├── config.py        # Application configuration
│   ├── core/            # Core business logic and pipelines
│   ├── extraction/      # Data extraction from various sources
│   ├── lib/             # Shared library code
│   ├── persistence/     # Database models and persistence logic
│   ├── services/        # External service integrations (e.g., ElevenLabs)
│   └── utils/           # Utility functions and helpers
├── tests/               # Test suite
├── docs/                # Documentation and assets
├── pyproject.toml       # Project configuration
└── .python-version      # Python 3.13+ requirement
```

## Code Organization Rules

### Module Structure
- **`src/voiceover_mage/main.py`**: Entry point and CLI interface using `asyncclick`.
- **`src/voiceover_mage/config.py`**: Manages application settings and environment variables using Pydantic's `BaseSettings`.
- **`src/voiceover_mage/core/`**: Contains the main business logic.
    - `unified_pipeline.py`: The main pipeline for generating voiceovers.
    - `dashboard_pipeline.py`: Pipeline for generating a dashboard of voiceovers.
- **`src/voiceover_mage/extraction/`**: Handles data extraction from different sources.
    - `wiki/`: Scrapes data from OSRS wiki.
    - `analysis/`: Analyzes extracted data to generate character profiles.
- **`src/voiceover_mage/persistence/`**: Manages data storage.
    - `manager.py`: Handles database sessions and operations.
    - `models.py`: Defines `SQLModel` database tables.
- **`src/voiceover_mage/services/`**: Interfaces with external APIs.
    - `voice/elevenlabs.py`: Interacts with the ElevenLabs API.
- **`src/voiceover_mage/utils/`**: Contains shared utilities.
    - `logging/`: Configures logging with `Loguru` and `Rich`.
    - `retry.py`: Provides retry mechanisms for network requests.

### Architecture Patterns
- **Pipeline-based architecture**: Core logic is organized into pipelines (`unified_pipeline.py`).
- **Separation of Concerns**: Clear separation between data extraction, business logic, persistence, and external services.
- **Pydantic & SQLModel**: Extensive use of Pydantic for data validation and SQLModel for ORM.
- **Dependency Injection**: Used implicitly through service classes and configuration objects.

### File Naming Conventions
- Snake_case for Python files and modules.
- Test files: `test_<module_name>.py`.

### Import Organization
- Standard library imports first.
- Third-party imports second.
- Local imports last, using absolute paths from the package root (e.g., `from voiceover_mage.core import ...`).
