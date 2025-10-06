<p align="center">
    <img src="./docs/logo.png" width="500px" />
</p>

# The Voiceover Mage

🧙‍♂️ An automated backend service that transforms silent Old School RuneScape NPCs into speaking characters using AI-powered voice synthesis.

## Overview

**Voiceover Mage** brings the world of Gielinor to life by providing unique, character-appropriate voices for its many NPCs. The system works by:

1.  **Scraping** NPC data from the Old School RuneScape Wiki.
2.  **Analyzing** the NPC's dialogue, lore, and attributes to generate a detailed character profile.
3.  **Synthesizing** a unique voice using the ElevenLabs API based on the generated profile.
4.  **Persisting** the generated voice and character data in a local database for efficient retrieval.

This project is designed to be used with the [Gielinor Speaks RuneLite plugin](https://github.com/gielinorspeaks) to provide an immersive audio experience for players.

## Features

-   **REST API**: FastAPI server with intelligent dialogue caching and automatic voice generation
-   **Automated NPC Data Extraction**: Scrapes OSRS Wiki pages for NPC information
-   **AI-Powered Character Analysis**: Uses language models to analyze text and create rich character profiles
-   **High-Quality Voice Synthesis**: Integrates with the ElevenLabs API to generate expressive and unique voices
-   **Smart Caching**: Hash-based dialogue matching for instant repeated dialogue responses
-   **Database Persistence**: Caches generated data in a local SQLite database to prevent redundant processing
-   **Async Pipeline**: Built with `anyio` and `asyncclick` for efficient, non-blocking I/O
-   **Rich CLI & API**: Detailed logging and OpenAPI documentation

## Technology Stack

-   **Python 3.13+**
-   **FastAPI**: REST API with OpenAPI documentation
-   **DSPy**: Programming with language models
-   **ElevenLabs**: Text-to-speech voice generation
-   **Crawl4AI**: Web scraping
-   **Pydantic & SQLModel**: Data validation and database ORM
-   **AsyncClick**: Asynchronous CLI
-   **UV**: Project and dependency management

## Installation

```bash
# Clone the repository
git clone https://github.com/gielinorspeaks/voiceover-mage.git
cd voiceover-mage

# Install dependencies using uv
uv sync --dev
```

## Usage

### CLI

```bash
# Generate voice for an NPC
uv run app generate-npc <npc_id>

# Run the full pipeline
uv run app pipeline run

# See all commands
uv run app --help
```

### API

```bash
# Start the API server
uv run uvicorn voiceover_mage.api.main:app --reload

# Visit interactive docs
open http://localhost:8000/docs

# Generate speech
curl -X POST "http://localhost:8000/api/v1/npc/3105/speak" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, adventurer!"}'
```

**Error Codes:**

| Code | Status | Action |
|------|--------|--------|
| `NPC_NOT_FOUND` | 404 | Verify NPC ID |
| `VOICE_NOT_CONFIGURED` | 503 | Run CLI pipeline first |
| `TTS_SERVICE_UNAVAILABLE` | 503 | Retry with backoff |
| `TTS_GENERATION_FAILED` | 500 | Retry request |

All errors include a `retryable` flag when applicable.

## Development

```bash
# Run tests
uv run pytest

# Lint the code
uv run ruff check .

# Format the code
uv run ruff format

# Typing checks
uv run pyright

# Run the application
uv run app
```

## Requirements

-   Python 3.13+
-   `uv` package manager
-   An `.env` file with an `ELEVENLABS_API_KEY` (see `.env.example`)