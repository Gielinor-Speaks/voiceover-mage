# Technology Stack

## Language & Runtime
- **Python 3.13+** (minimum required version)
- Modern Python features and syntax expected

## Build System
- **pyproject.toml** for project configuration and dependency management
- Standard Python packaging with PEP 621 compliance

## Project Management
- Uses modern Python project structure with pyproject.toml
- No external dependencies currently defined (early stage project)

## Common Commands
```bash
# Run the application
uv run app

# Install in development mode (when dependencies are added)
uv sync --dev

# Python version management
# Project uses .python-version file for version specification
```

## Development Guidelines
- Follow Python 3.13+ syntax and features
- Maintain compatibility with the specified minimum Python version
- Use type hints where appropriate for AI voice generation components