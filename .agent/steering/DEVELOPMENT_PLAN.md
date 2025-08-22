# Phase 1 Implementation Plan: Basic NPC Data Extraction

## Overview
Transform the current LLM-dependent extraction to a simple, reliable markdown and image extraction system with SQLModel persistence and caching.

## Implementation Tasks (Sequential Order)

### Task 1: Database Foundation ✅ COMPLETED
- [x] Create `NPCRawExtraction` SQLModel with fields for npc_id, name, wiki_url, markdown, image URLs
- [x] Implement `DatabaseManager` class with async SQLite operations
- [x] Add caching methods to check/save extractions
- [x] Write comprehensive database tests

### Task 2: Markdown-Only Extractor
- [ ] Create `MarkdownNPCExtractor` class (no LLM calls)
- [ ] Use Crawl4AI in markdown mode for raw content extraction
- [ ] Extract image URLs using CSS selectors
- [ ] Return `NPCRawExtraction` objects instead of analyzed data

### Task 3: Integration Layer
- [ ] Build `NPCExtractionService` coordinating extractor + database
- [ ] Implement cache-first extraction logic
- [ ] Update CLI to use new service with `--force-refresh` flag
- [ ] Add progress reporting for extraction status

### Task 4: Test Data and Fixtures
- [ ] Request 5 MHTML files from operator (merchant, guard, quest NPC, craftsperson, wizard)
- [ ] Create fixture loading utilities
- [ ] Write integration tests using real page data
- [ ] Validate extraction across different NPC types

### Task 5: CLI and User Experience
- [ ] Update `extract_npc` command for markdown extraction
- [ ] Add `--raw` flag for markdown output display
- [ ] Implement Rich formatting for extraction results
- [ ] Show cache status in output

### Task 6: Error Handling
- [ ] Add network failure recovery
- [ ] Implement graceful degradation for missing images
- [ ] Add retry logic for transient failures
- [ ] Create comprehensive error scenario tests

### Task 7: Performance Optimization
- [ ] Ensure < 30 second extraction time per NPC
- [ ] Optimize database queries and indexes
- [ ] Add performance metrics and benchmarking

### Task 8: Documentation and Validation
- [ ] Update all docstrings and type hints
- [ ] Run full test suite on 5 test NPCs
- [ ] Validate database schema for Phase 2 compatibility
- [ ] Ensure >90% test coverage

## Key Architecture Decisions
- **No LLM dependency** - Pure markdown/HTML extraction
- **SQLModel for persistence** - Separate from future DSPy models
- **Cache-first approach** - Check database before crawling
- **Async throughout** - Using aiosqlite for database operations

## Success Metrics
✅ Clean markdown extraction without LLM  
✅ Reliable image URL extraction  
✅ Data persisted to SQLite with caching  
✅ < 30 second extraction time  
✅ Tests passing with >90% coverage

## Technical Architecture Details

### Data Architecture

**New SQLModel Schema:**
```python
# src/voiceover_mage/npc/persistence.py
class NPCRawExtraction(SQLModel, table=True):
    __tablename__ = "npc_raw_extractions"
    
    id: int | None = Field(default=None, primary_key=True)
    npc_id: int = Field(index=True)
    npc_name: str
    wiki_url: str
    raw_markdown: str  # Full page markdown content
    chathead_image_url: str | None = None
    image_url: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    extraction_success: bool = True
    error_message: str | None = None
```

### Extractor Architecture

**New Markdown-Only Extractor:**
```python
# src/voiceover_mage/npc/extractors/wiki/markdown.py
class MarkdownNPCExtractor(BaseWikiNPCExtractor):
    """LLM-free extractor that returns raw markdown and image URLs"""
    
    async def extract_npc_data(self, npc_id: int) -> NPCRawExtraction
    async def _extract_markdown_content(self, url: str) -> str
    async def _extract_image_urls(self, markdown: str) -> tuple[str | None, str | None]
```

### Database Layer

**Database Management:**
```python
# src/voiceover_mage/lib/database.py
class DatabaseManager:
    def __init__(self, database_url: str = "sqlite:///./npc_data.db")
    async def get_cached_extraction(self, npc_id: int) -> NPCRawExtraction | None
    async def save_extraction(self, extraction: NPCRawExtraction) -> NPCRawExtraction
    async def create_tables(self) -> None
```

### Testing Strategy

**Test Categories:**
1. **Unit Tests:** Individual component testing
2. **Integration Tests:** Component interaction testing  
3. **End-to-End Tests:** Full CLI workflow testing
4. **Performance Tests:** Speed and memory validation
5. **Fixture Tests:** Real NPC page testing

**Test Data:**
- 5 MHTML files representing diverse NPC types
- Synthetic test data for edge cases
- Database fixtures for caching tests

## Dependencies and Setup Requirements

**New Dependencies (add to pyproject.toml):**
```toml
dependencies = [
    # ... existing deps ...
    "sqlmodel>=0.0.22",  # Already present
    "aiosqlite>=0.20.0",  # For async SQLite operations
]
```

**Configuration Updates:**
- Database URL configuration in `Config`
- Cache behavior settings
- Default paths for database files

## Current Status

🚧 **Phase 1 In Progress**
- ✅ **Task 1 Completed**: Database foundation with async SQLModel operations
- 🎯 **Next**: Task 2 - Markdown-Only Extractor implementation

### Task 1 Completion Summary
- ✅ Implemented `NPCRawExtraction` SQLModel with all required fields
- ✅ Created async `DatabaseManager` using SQLAlchemy async components
- ✅ Added `aiosqlite>=0.20.0` dependency for async SQLite support
- ✅ Implemented caching functionality (cache-first approach)
- ✅ Added database configuration to `Config` class
- ✅ Created comprehensive test suite (23 tests passing)
- ✅ Verified async operations work correctly with proper session management
- ✅ Fixed code formatting and linting issues