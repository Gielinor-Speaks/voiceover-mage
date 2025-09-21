# Utils Layer

**Purpose**: Cross-cutting utilities and shared infrastructure.

## Architecture

```
Configuration + Logging + Common Helpers → Supporting All Layers
```

## Components

### `logging/`
- `config.py` - Logging configuration and setup
- `progress.py` - Rich progress tracking and console output
- Smart log interception and formatting

### `json_types.py`
- TypeAdapter utilities for JSON serialization
- Pydantic ↔ SQLModel integration helpers

## Services Provided

### Logging
- **Interactive Mode**: Rich console output with progress bars
- **Production Mode**: Structured JSON logging  
- **Context Tracking**: NPC ID, pipeline stage context
- **Progress Reporting**: Real-time extraction status

### Configuration
- Environment-based configuration
- Database connection settings
- API key management

## Usage

All other layers import utilities from here:
```python
from voiceover_mage.utils.logging import get_logger, create_smart_progress
from voiceover_mage.utils.json_types import PydanticJson
```