# Persistence Layer

**Purpose**: Database operations, checkpointing, and data storage management.

## Architecture

```
Extraction Data → persistence/models.py → Database → Cached Retrieval
```

## Components

### `models.py`
- `NPCExtraction` - Main database table with checkpoint columns
- Proper TypeAdapter JSON columns for each pipeline stage
- Stage tracking and resume capabilities

### `manager.py`
- `DatabaseManager` - Async database operations
- Connection management and transactions
- Checkpoint save/restore operations

### `json_types.py`
- `PydanticJson` - TypeAdapter utilities for JSON columns
- Seamless Pydantic model ↔ database serialization

## Checkpointing Strategy

Each extraction can be resumed from any stage:
- `RAW` - Initial wiki data extracted
- `TEXT` - Text analysis completed  
- `IMAGE` - Image analysis completed
- `SYNTHESIS` - Final profile synthesized
- `COMPLETE` - Ready for voice generation

## Data Flow

1. **Save**: Structured data → JSON serialization → Database
2. **Resume**: Database → JSON deserialization → Structured data
3. **Cache**: Automatic retrieval of completed stages