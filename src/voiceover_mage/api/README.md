# Voiceover Mage API

FastAPI-based REST API for NPC voice generation. Mirrors CLI functionality with intelligent dialogue caching.

## Quick Start

### Run the API server

```bash
# Using uvicorn directly
uv run uvicorn voiceover_mage.api.main:app --reload --port 8000

# Or with hot reload
uv run uvicorn voiceover_mage.api.main:app --reload
```

### API Documentation

Once running, visit:
- **Interactive API docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative docs**: http://localhost:8000/redoc (ReDoc)

## Endpoints

### Health Check

```bash
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected"
}
```

### Generate NPC Speech

```bash
POST /api/v1/npc/{npc_id}/speak
Content-Type: application/json

{
  "text": "Hello, adventurer! What brings you to my shop today?"
}
```

**Response:**
```json
{
  "npc_id": 1,
  "npc_name": "Wise Old Man",
  "text": "Hello, adventurer!",
  "audio_base64": "base64_encoded_mp3_data...",
  "cached": false,
  "provider": "elevenlabs",
  "generation_metadata": {
    "preview_id": 42,
    "voice_prompt": "Elderly male, wise and patient..."
  }
}
```

### Get Audio Response (Alternative)

```bash
GET /api/v1/npc/{npc_id}/speak/audio?text=Hello,%20adventurer!
```

**Response:** Raw MP3 audio bytes

## Voice Generation Flow

The API follows this intelligent priority system:

1. **Cache Hit** - Return cached dialogue if text matches (hash-based lookup, O(1))
2. **Cloned Voice** - Use NPC's cloned voice if available
3. **Selected Preview** - Use the selected voice preview
4. **Random Preview** - Pick random preview from existing ones, set as selected
5. **Full Pipeline** - Run complete NPC extraction pipeline, generate previews, pick one

This ensures:
- **Instant responses** for repeated dialogue (cache hits)
- **Automatic fallback** to pipeline if NPC has no voice configured
- **Consistent voice** once selected for an NPC

## Dialogue Caching

### How It Works

Dialogue is cached using **content-addressable hashing**:

- Text is normalized (lowercase, strip whitespace)
- SHA256 hash computed
- Hash + NPC ID used as cache key (indexed for O(1) lookup)

### Cache Behavior

**Same dialogue, different formatting = Cache Hit:**
```json
// These all match the same cached audio:
{"text": "Hello"}
{"text": "  HELLO  "}
{"text": "hello"}
```

**Different dialogue = Cache Miss:**
```json
// These are treated as different:
{"text": "Hello world"}
{"text": "Helloworld"}  // Internal whitespace matters
```

## Database

The API shares the same SQLite database as the CLI:

```
./data/voiceover_mage.db
```

Tables used:
- `npc` - NPC identity and selected voice
- `generated_dialogue` - Cached dialogue with hashes
- `voice_preview` - Generated voice previews
- `character_profile` - Extracted character data

## Environment Variables

Configure via `.env` file or environment:

```bash
# Database
VOICEOVER_MAGE_DATABASE_URL=sqlite+aiosqlite:///./data/voiceover_mage.db

# API Keys
VOICEOVER_MAGE_GEMINI_API_KEY=your_key_here
VOICEOVER_MAGE_ELEVENLABS_API_KEY=your_key_here

# TTS Service
VOICEOVER_MAGE_LOCAL_TTS_API_URL=http://localhost:8000
```

## Performance

### Dialogue Matching

- **Hash lookup**: O(1) with database index
- **Storage overhead**: 64 bytes per dialogue (SHA256 hash)
- **Collision probability**: Effectively zero (2^-256)

### API Response Times

- **Cache hit**: <10ms (indexed database lookup)
- **Cache miss with selected voice**: ~2-5s (TTS generation)
- **Full pipeline**: ~30-60s (wiki scrape + analysis + voice gen)

## Error Handling

All errors include a `retryable` flag where applicable. See [error codes reference](../../../docs/api/error-codes.md) for complete list.

### Common Error Codes

| Code | Status | Action |
|------|--------|--------|
| `NPC_NOT_FOUND` | 404 | Verify NPC ID |
| `VOICE_NOT_CONFIGURED` | 503 | Run CLI pipeline |
| `TTS_SERVICE_UNAVAILABLE` | 503 | Retry with backoff |
| `TTS_GENERATION_FAILED` | 500 | Retry request |

### Example Error Response

```json
{
  "detail": {
    "error": "TTS_SERVICE_UNAVAILABLE",
    "message": "Text-to-speech service is unavailable",
    "service_url": "http://localhost:8001",
    "reason": "Connection refused",
    "retryable": true
  }
}
```

**📚 More details:**
- [Error Codes](../../../docs/api/error-codes.md)
- [OpenAPI Spec](http://localhost:8000/docs)

## Testing

Run API tests:

```bash
# Unit tests for hash matching
uv run pytest tests/utils/test_text_hash.py -v

# Integration tests for dialogue caching
uv run pytest tests/api/test_dialogue_caching.py -v
```

## Architecture

```
voiceover_mage/api/
├── main.py              # FastAPI app, CORS, lifespan
├── dependencies.py      # Dependency injection (DB, sessions)
├── models.py            # Pydantic request/response models
├── services.py          # VoiceGenerationService (business logic)
└── routes/
    ├── generation.py    # /npc/{id}/speak endpoints
    └── health.py        # /health endpoint
```

## Future Enhancements

- [ ] LLM-based voice selection (replace random pick)
- [ ] Batch generation endpoint
- [ ] WebSocket streaming for long operations
- [ ] Voice preview management endpoints
- [ ] Dialogue history/analytics
- [ ] Rate limiting
- [ ] Authentication
