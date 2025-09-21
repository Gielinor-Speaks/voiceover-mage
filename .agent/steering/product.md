# Voiceover Mage - AI Voice Generation for OSRS NPCs

## Product Context
Voiceover Mage is an automated system that generates unique, high-quality voiceovers for Old School RuneScape (OSRS) NPCs. It scrapes data from the OSRS Wiki, analyzes NPC lore and dialogue to create detailed character profiles, and then uses the ElevenLabs API to synthesize voices. The generated voice profiles and audio are stored in a local database for persistence and retrieval.

**Data Flow**:
Wiki Scrape (Crawl4AI) → NPC Data Extraction → Character Analysis (DSPy) → Voice Profile Generation → ElevenLabs Voice Synthesis → Database Persistence (SQLModel) → Audio File Storage

## Implementation Guidelines

### Data Extraction (Extraction Module)
- Use `crawl4ai` to efficiently scrape NPC pages from the OSRS Wiki.
- Extract key information: dialogue, quest involvement, location, race, gender, and combat level.
- Structure the extracted data into Pydantic models for validation.

### Character Analysis (Analysis Module)
- Use `dspy` to create signatures and modules for analyzing NPC data.
- Infer personality traits, vocal characteristics (age, accent, tone), and a descriptive summary from the extracted text.
- Generate a detailed `CharacterProfile` Pydantic model.

### Voice Generation (Services Module)
- Use the `elevenlabs` Python SDK for all interactions with the ElevenLabs API.
- Generate voice designs based on the `CharacterProfile`.
- Synthesize audio samples for each NPC.
- Implement robust error handling and retry mechanisms (`tenacity`) for API calls.

### Persistence (Persistence Module)
- Use `SQLModel` to define database tables for NPCs, Character Profiles, and Voice Samples.
- Store all generated data in a local SQLite database.
- Implement a `DBManager` to handle all database sessions and transactions.
- Cache generated profiles and audio to prevent redundant API calls.

### Core Logic (Core Module)
- Encapsulate the end-to-end process in a `UnifiedPipeline`.
- Provide clear logging and progress tracking using `Loguru` and `Rich`.
- Structure the application CLI using `asyncclick` to handle asynchronous operations gracefully.

### Quality Assurance
- Validate generated voices against character descriptions.
- Store voice previews and metadata for manual review.
- Ensure the generated voices align with the medieval fantasy setting of RuneScape.
