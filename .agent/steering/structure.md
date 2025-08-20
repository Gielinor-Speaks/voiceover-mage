# Project Structure & Architecture

## Current Structure
```
voiceover-mage/
├── src/voiceover_mage/  # Main package
│   ├── __init__.py      # Package initialization
│   └── main.py          # Application entry point
├── tests/               # Test suite
├── docs/                # Documentation and assets
├── pyproject.toml       # Project configuration
└── .python-version      # Python 3.13+ requirement
```

## Code Organization Rules

### Module Structure
- **src/voiceover_mage/main.py**: Entry point and CLI interface
- Place new modules in `src/voiceover_mage/` package
- Use descriptive module names: `character_analyzer.py`, `voice_generator.py`, `wiki_scraper.py`
- Keep related functionality grouped in single modules

### Architecture Patterns
- Use Pydantic models for all data structures (NPC profiles, voice characteristics)
- Implement template-based prompt generation with character trait mapping
- Structure for batch processing multiple NPCs
- Separate concerns: data extraction → analysis → voice generation → API integration

### File Naming Conventions
- Snake_case for Python files and modules
- Descriptive names reflecting functionality
- Test files: `test_<module_name>.py`
- Configuration files in root level

### Import Organization
- Standard library imports first
- Third-party imports second
- Local imports last
- Use absolute imports from package root: `from voiceover_mage.character_analyzer import ...`

### Future Module Organization
When expanding, create these modules:
- `character_analyzer.py` - NPC personality extraction
- `voice_generator.py` - ElevenLabs prompt generation
- `wiki_scraper.py` - OSRS wiki data extraction
- `models.py` - Pydantic data models
- `config.py` - Configuration management