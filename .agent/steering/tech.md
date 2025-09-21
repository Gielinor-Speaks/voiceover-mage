# Technology Stack

## Language & Runtime
- **Python 3.13+** (minimum required version)
- Modern Python features and syntax expected

## Build System & Dependency Management
- **uv** for dependency management and running tasks.
- **pyproject.toml** for project configuration and dependency definition (PEP 621).

## Core Dependencies
- **dspy**: For programming with language models.
- **ElevenLabs**: For text-to-speech voice generation.
- **crawl4ai**: For web scraping and data extraction.
- **Pydantic**: For data validation and settings management.
- **SQLModel**: For database interaction (ORM).
- **Loguru**: For logging.
- **Rich**: For rich text and beautiful formatting in the terminal.
- **AsyncClick**: For creating asynchronous command-line interfaces.

## Development & Tooling
- **pytest**: For running automated tests.
- **ruff**: For linting and code formatting.
- **pyright**: For static type checking.

## Common Commands
```bash
# Install dependencies
uv sync --dev

# Run the application
uv run app

# Run tests
uv run pytest

# Lint the code
uv run ruff check .
```

## Development Guidelines
- Follow Python 3.13+ syntax and features.
- Use type hints for all function signatures.
- Adhere to the `ruff` linter rules for code style and quality.
- Run `pyright` to identify any typing issues.
- Write `pytest` tests for all new functionality.
