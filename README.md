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

-   **Automated NPC Data Extraction**: Scrapes OSRS Wiki pages for NPC information.
-   **AI-Powered Character Analysis**: Uses language models to analyze text and create rich character profiles.
-   **High-Quality Voice Synthesis**: Integrates with the ElevenLabs API to generate expressive and unique voices.
-   **Database Persistence**: Caches generated data in a local SQLite database to prevent redundant processing.
-   **Asynchronous Pipeline**: Built with `anyio` and `asyncclick` for efficient, non-blocking I/O.
-   **Rich CLI**: Provides detailed progress and logging in the terminal using `rich` and `loguru`.

## Technology Stack

-   **Python 3.13+**
-   **DSPy**: For programming with language models.
-   **ElevenLabs**: For text-to-speech voice generation.
-   **Crawl4AI**: For web scraping.
-   **Pydantic & SQLModel**: For data validation and database operations.
-   **AsyncClick**: For the asynchronous command-line interface.
-   **UV**: For project and dependency management.

## Installation

```bash
# Clone the repository
git clone https://github.com/gielinorspeaks/voiceover-mage.git
cd voiceover-mage

# Install dependencies using uv
uv sync --dev
```

## Usage

The main entry point is a CLI application.

```bash
# Run the main voice generation pipeline
uv run app pipeline run

# See all available commands
uv run app --help
```

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