# Core Layer

**Purpose**: Business logic, workflow orchestration, and high-level APIs.

## Architecture

```
Database Data → core/pipeline.py → core/service.py → Public API
```

## Components

### `models.py`
- `ExtractionStage` - Pipeline stage enumeration
- `NPCProfile` - Final business domain model
- Domain-specific business objects

### `pipeline.py`
- `ResumablePipeline` - Checkpoint-aware pipeline execution
- Stage orchestration and error handling
- Resume logic for failed operations

### `service.py`
- `NPCExtractionService` - High-level public API
- Coordinates extraction → persistence → core workflow
- User-friendly interface for CLI and future APIs

## Pipeline Stages

1. **Raw Extraction** - Get wiki data
2. **Text Analysis** - Extract personality traits
3. **Image Analysis** - Visual characteristic extraction
4. **Synthesis** - Combine analyses into final profile
5. **Complete** - Ready for voice generation

## Data Flow

1. **Request**: NPC ID → Service coordination
2. **Resume**: Check persistence for existing progress
3. **Execute**: Run missing pipeline stages
4. **Return**: Final business objects