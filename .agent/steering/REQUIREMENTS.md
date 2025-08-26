# Voice Generation Pipeline Requirements

## Overview
Build a DSPy-powered voice generation pipeline that transforms OSRS NPC IDs into high-quality character voices through multiple providers with automatic quality grading.

## Core Principle
**Incremental Development**: Each phase must be working and tested before proceeding to the next.

## Critical Architecture Decision: DSPy vs SQLModel Separation

**Finding**: DSPy (Pydantic-based) and SQLModel (also Pydantic-based) should remain separate.

### Why Separation is Necessary
1. **Different Concerns**: DSPy models define LLM I/O schemas; SQLModel defines database schemas
2. **Schema Evolution**: DSPy prompts can evolve without database migrations
3. **Version Tracking**: Database stores all extraction attempts, not just latest
4. **Clean Architecture**: Extraction logic separate from persistence logic

### Implementation Pattern
```python
# DSPy Model (for LLM extraction)
class NPCTextExtraction(BaseModel):
    dialogue_examples: list[str]
    occupation: str
    
# SQLModel (for database persistence)  
class NPCTextAnalysis(SQLModel, table=True):
    id: int = Field(primary_key=True)
    extraction_json: str  # Serialized DSPy result
    dspy_version: str
    timestamp: datetime
    
# Conversion function
def save_extraction(extraction: NPCTextExtraction, npc_id: int):
    record = NPCTextAnalysis(
        extraction_json=extraction.model_dump_json(),
        dspy_version="v1",
        npc_id=npc_id
    )
```

## Data Persistence Strategy

### SQLModel Schema (Progressive Enhancement)
Each phase adds its own table, maintaining full extraction history:

1. **Phase 1**: `NPCData` - Markdown and image URLs
2. **Phase 2**: `NPCTextAnalysis` - DSPy text extraction results
3. **Phase 3**: `NPCVisualAnalysis` - DSPy image analysis results
4. **Phase 4**: `NPCCharacterProfile` - Synthesized profiles
5. **Phase 5+**: `VoiceGeneration` - Voice samples and scores

### Benefits
- **Data Flywheel**: Every extraction becomes training data
- **A/B Testing**: Compare different DSPy prompt versions
- **Debugging**: Full audit trail of all extractions
- **Caching**: Natural cache with query capabilities

## Phase 1: Basic NPC Data Extraction ✅ CURRENT
**Goal**: Extract clean markdown and images from wiki pages

### Requirements
- [ ] Refactor `crawl4ai.py` to use markdown extraction (no LLM)
- [ ] Create `NPCData` SQLModel for persistence
- [ ] Return simple data structure with:
  - NPC name and wiki URL
  - Raw markdown content
  - Image URLs (chathead and full body)
- [ ] Implement SQLModel caching (check DB before crawling)
- [ ] Test with 5 diverse NPCs (merchant, guard, quest NPC, etc.) (AGENTTODO: ASK OPERATOR FOR .mhtml files that can be fixtures.)

### Success Criteria
- Clean markdown extraction from wiki pages
- Reliable image URL extraction
- No dependency on LLM for this phase
- Data persisted to SQLite database

## Phase 2: Text Analysis with DSPy
**Goal**: Extract structured text data from markdown using DSPy

### Requirements
- [ ] Create DSPy extraction model (`NPCTextExtraction` - Pydantic only):
  - Dialogue examples
  - Occupation/role
  - Location
  - Quest appearances
- [ ] Create SQLModel persistence (`NPCTextAnalysis` - database table):
  - Links to `NPCData`
  - Stores serialized DSPy result
  - Tracks DSPy model version
- [ ] Build DSPy signature for text extraction
- [ ] Implement confidence scoring for extracted fields
- [ ] Test extraction accuracy on Phase 1's test NPCs

### Success Criteria
- Consistent extraction of dialogue and lore
- Confidence scores reflect extraction quality
- Handle NPCs with minimal wiki data gracefully
- All extractions persisted for future optimization

## Phase 3: Visual Analysis with DSPy
**Goal**: Analyze NPC appearance from images

### Requirements
- [ ] Create DSPy extraction model (`NPCVisualExtraction` - Pydantic only):
  - Apparent age
  - Physical build
  - Clothing/attire
  - Facial features
- [ ] Create SQLModel persistence (`NPCVisualAnalysis` - database table):
  - Links to `NPCData`
  - Stores serialized DSPy result
  - Tracks which image URL was analyzed
- [ ] Build DSPy signature for image analysis
- [ ] Handle missing images gracefully
- [ ] Test on NPCs with/without images

### Success Criteria
- Meaningful visual descriptions from images
- Fallback to text-based appearance when no images
- Consistent trait extraction
- All analyses persisted for comparison

## Phase 4: Character Profile Synthesis
**Goal**: Combine text and visual data into unified character profile

### Requirements
- [ ] Create `NPCCharacterProfile` model
- [ ] DSPy ChainOfThought for synthesis with reasoning
- [ ] Define voice-relevant attributes:
  - Speaking style
  - Education level
  - Emotional baseline
  - Regional accent hints
- [ ] Test profile quality and consistency

### Success Criteria
- Coherent character profiles
- Clear reasoning for inferred traits
- Voice-relevant attributes properly extracted

## Phase 5: Voice Provider Integration
**Goal**: Generate voice configurations for providers

### Requirements
- [ ] ElevenLabs prompt generator (DSPy module)
- [ ] Provider-agnostic base class
- [ ] Voice configuration models
- [ ] API integration with error handling
- [ ] Start with ONE provider (ElevenLabs)

### Success Criteria
- Generate provider-specific prompts from profiles
- Successfully create voice samples
- Handle API errors gracefully

## Phase 6: Voice Grading System
**Goal**: Automatically evaluate generated voices

### Requirements
- [ ] Define grading criteria:
  - Character match
  - OSRS authenticity
  - Technical quality
- [ ] DSPy grading module
- [ ] Score aggregation logic
- [ ] Test with multiple voice samples

### Success Criteria
- Consistent scoring across samples
- Meaningful differentiation between qualities
- Explainable scoring (with reasoning)

## Phase 7: Multi-Provider Support
**Goal**: Add additional voice providers

### Requirements
- [ ] Hume AI integration
- [ ] Provider comparison framework
- [ ] Parallel generation support
- [ ] Cost tracking per provider

### Success Criteria
- Multiple providers generating voices
- Fair comparison between providers
- Cost-optimized selection when quality is similar

## Phase 8: DSPy Optimization
**Goal**: Optimize pipeline performance with DSPy

### Requirements
- [ ] Create training datasets (20-30 NPCs)
- [ ] Define evaluation metrics for each module
- [ ] Implement MIPROv2 optimization for synthesis
- [ ] BootstrapFewShot for extractors
- [ ] A/B testing framework

### Success Criteria
- Measurable improvement in extraction accuracy
- Better character profiles post-optimization
- Higher voice quality scores

## Phase 9: Production Pipeline
**Goal**: Production-ready system

### Requirements
- [ ] Full error handling and recovery
- [ ] Comprehensive caching strategy
- [ ] Monitoring and logging
- [ ] Batch processing support
- [ ] API endpoint for voice generation

### Success Criteria
- 95%+ success rate for voice generation
- Sub-30 second generation time
- Automated quality assurance

## Technical Constraints

1. **DSPy Usage**: All LLM interactions MUST use DSPy (no direct prompting)
2. **Model Separation**: DSPy models (Pydantic) and SQLModel tables MUST be separate
   - DSPy models for LLM I/O (runtime extraction)
   - SQLModel for database persistence
   - Serialize DSPy results as JSON in SQLModel tables
3. **Modularity**: Each component must be independently testable
4. **Provider Agnostic**: Core pipeline shouldn't depend on specific providers
5. **Optimization Ready**: Structure code to support DSPy optimization from day 1
6. **Type Safety**: Use Pydantic models throughout (both DSPy and SQLModel inherit from Pydantic)
7. **Data Flywheel**: Every extraction attempt must be persisted for future training

## Non-Functional Requirements

- **Performance**: < 30s end-to-end for single NPC
- **Reliability**: Graceful degradation on partial failures
- **Cost**: Track and optimize token usage
- **Maintainability**: Clear separation of concerns
- **Testability**: Unit tests for each module

## Definition of Done

Each phase is complete when:
1. Code is implemented and working
2. Tests are passing
3. Documentation is updated
4. Results are validated on test NPCs
5. Next phase can build on it safely

## Current Status

🚧 **Phase 1 In Progress**
- Starting with markdown extraction refactor
- Removing LLM dependency from crawl4ai extractor