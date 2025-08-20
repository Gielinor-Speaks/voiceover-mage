# Docker Setup for Voiceover Mage

This project includes Docker and dev container configurations for safe and isolated development.

## Quick Start

### Using Docker Compose (Recommended for development)

```bash
# Build and run the development environment
docker-compose up --build

# Or run in the background
docker-compose up -d --build

# Run production version
docker-compose --profile prod up

# Enter the container for interactive development
docker-compose exec voiceover-mage bash
```

### Using Dev Container (VS Code)

1. Install the "Dev Containers" extension in VS Code
2. Open the project in VS Code
3. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
4. Select "Dev Containers: Reopen in Container"
5. VS Code will build and open the project in the dev container

The dev container includes:
- Claude Code integration for safe AI-assisted development
- Python 3.13 with uv package manager
- All project dependencies pre-installed
- Development tools (ruff, pytest, mypy)
- VS Code extensions for Python development

## Available Services

### 🔧 voiceover-mage (dev)
- Interactive development environment 
- Full tooling: pytest, ruff, vim, less
- Port 8000, live reload enabled

### 🚀 voiceover-mage-prod  
- Lean production runtime
- Port 8001, optimized for deployment
- Run with: `docker-compose --profile prod up`

## Claude Code Integration

The dev container is configured for safe Claude Code usage:
- Isolated environment prevents accidental system modifications
- Configuration is mounted from your host machine
- Easy to reset if anything goes wrong

To use Claude Code in the container:
1. Ensure you have Claude Code configured on your host machine
2. Open the project in the dev container
3. Claude Code will be available within the sandboxed environment

## File Watching

The Docker Compose setup includes file watching for development:
- Changes to source files are automatically synced to the container
- Changes to `pyproject.toml` or `uv.lock` trigger container rebuilds
- Virtual environment is preserved across rebuilds

## Commands

Inside the container, you can use:

```bash
# Run the application
uv run app

# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run type checking
uv run mypy src/

# Install new dependencies
uv add <package-name>

# Install dev dependencies
uv add --dev <package-name>
```

## Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all
```