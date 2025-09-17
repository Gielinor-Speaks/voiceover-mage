# ABOUTME: Tests for normalized DatabaseManager and NPC pipeline state aggregation
# ABOUTME: Validates upsert helpers, derived stages, and artifact persistence

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.pool import StaticPool

from voiceover_mage.extraction.analysis.image import NPCVisualCharacteristics
from voiceover_mage.extraction.analysis.synthesizer import NPCDetails
from voiceover_mage.extraction.analysis.text import NPCTextCharacteristics
from voiceover_mage.persistence.manager import DatabaseManager, NPCPipelineState


@pytest_asyncio.fixture
async def temp_db() -> DatabaseManager:
    """Provide an in-memory database manager for async tests."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlmodel.ext.asyncio.session import AsyncSession

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    db.engine = engine
    db.async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await db.create_tables()
    yield db
    await db.close()


async def _bootstrap_npc(db: DatabaseManager, npc_id: int = 1) -> NPCPipelineState:
    """Create a minimal NPC identity and snapshot for derived-stage tests."""
    await db.ensure_npc(
        npc_id=npc_id,
        name="Hans",
        variant=None,
        wiki_url="https://oldschool.runescape.wiki/w/Hans",
    )
    await db.upsert_wiki_snapshot(
        npc_id=npc_id,
        raw_markdown="# Hans\nThe loyal servant of Duke Horacio.",
        chathead_image_url="https://example.com/hans_chat.png",
        image_url="https://example.com/hans.png",
        raw_data=None,
        source_checksum="abc123",
        fetched_at=datetime.now(UTC),
        extraction_success=True,
        error_message=None,
    )
    state = await db.get_cached_extraction(npc_id)
    assert state is not None
    return state


@pytest.mark.asyncio
async def test_ensure_npc_creates_identity(temp_db: DatabaseManager):
    npc = await temp_db.ensure_npc(
        npc_id=7,
        name="Bob",
        variant="Lumbridge",
        wiki_url="https://oldschool.runescape.wiki/w/Bob",
    )

    assert npc.id == 7
    assert npc.name == "Bob"
    assert npc.variant == "Lumbridge"

    state = await temp_db.get_cached_extraction(7)
    assert state is not None
    assert state.npc_name == "Bob"
    assert state.stage_flags["wiki_data"] is False


@pytest.mark.asyncio
async def test_wiki_snapshot_round_trip(temp_db: DatabaseManager):
    state = await _bootstrap_npc(temp_db, npc_id=42)

    assert state.raw_markdown.startswith("# Hans")
    assert state.chathead_image_url.endswith("hans_chat.png")
    assert state.stage_flags["wiki_data"] is True
    assert state.completed_stages == ["wiki_data"]


@pytest.mark.asyncio
async def test_character_profile_upsert(temp_db: DatabaseManager):
    state = await _bootstrap_npc(temp_db)

    profile = NPCDetails(
        npc_name=state.npc_name,
        personality_traits="loyal, dutiful",
        occupation="Castle servant",
        social_role="Guide",
        dialogue_patterns="Polite responses",
        emotional_range="Friendly",
        background_lore="Lives in Lumbridge",
        age_category="Adult",
        build_type="Average",
        attire_style="Simple garb",
        distinctive_features="Bald head",
        color_palette="Blue and white",
        visual_archetype="Helpful citizen",
        chathead_image_url=state.chathead_image_url,
        image_url=state.image_url,
        overall_confidence=0.8,
        text_confidence=0.75,
        visual_confidence=0.7,
        synthesis_notes="Baseline profile",
    )

    text = NPCTextCharacteristics(
        personality_traits="Helpful",
        occupation="Servant",
        social_role="Guide",
        dialogue_patterns="Polite",
        emotional_range="Warm",
        background_lore="Castle duties",
        confidence_score=0.7,
        reasoning="Markdown summary",
    )

    visual = NPCVisualCharacteristics(
        chathead_image_url=state.chathead_image_url,
        image_url=state.image_url,
        age_category="Adult",
        build_type="Average",
        attire_style="Blue tunic",
        distinctive_features="Bald",
        color_palette="Blue",
        visual_archetype="Servant",
        confidence_score=0.6,
        reasoning="Image tags",
    )

    await temp_db.upsert_character_profile(
        npc_id=state.id,
        profile=profile,
        text_analysis=text,
        visual_analysis=visual,
        pipeline_version="test-1",
    )

    refreshed = await temp_db.get_cached_extraction(state.id)
    assert refreshed is not None
    assert refreshed.character_profile is not None
    assert refreshed.character_profile.personality_traits == "loyal, dutiful"
    assert refreshed.text_analysis is not None
    assert refreshed.visual_analysis is not None
    assert refreshed.stage_flags["character_profile"] is True


@pytest.mark.asyncio
async def test_voice_preview_selection(temp_db: DatabaseManager):
    state = await _bootstrap_npc(temp_db, npc_id=99)

    first = await temp_db.create_voice_preview(
        npc_id=state.id,
        voice_prompt="calm and friendly",
        sample_text="Hello adventurer!",
        provider="elevenlabs",
        model="eleven_ttv_v3",
        generation_metadata={"index": 1},
        audio_path="/tmp/99_preview_1.mp3",
        is_representative=False,
    )
    second = await temp_db.create_voice_preview(
        npc_id=state.id,
        voice_prompt="excited",
        sample_text="The duke is waiting!",
        provider="elevenlabs",
        model="eleven_ttv_v3",
        generation_metadata={"index": 2},
        audio_path="/tmp/99_preview_2.mp3",
        is_representative=True,
    )

    assert first.is_representative is False
    assert second.is_representative is True

    selected = await temp_db.set_selected_voice_preview(state.id, first.id)
    assert selected is not None
    assert selected.is_representative is True

    refreshed = await temp_db.get_cached_extraction(state.id)
    assert refreshed is not None
    assert refreshed.selected_preview_id == first.id
    assert refreshed.stage_flags["voice_generation"] is True
    assert refreshed.stage_flags["voice_selection"] is True


@pytest.mark.asyncio
async def test_audio_transcript_storage(temp_db: DatabaseManager):
    state = await _bootstrap_npc(temp_db, npc_id=5)
    preview = await temp_db.create_voice_preview(
        npc_id=state.id,
        voice_prompt="formal",
        sample_text="Greetings, traveler.",
        provider="elevenlabs",
        model="eleven_ttv_v3",
        generation_metadata={},
        is_representative=True,
    )

    await temp_db.set_selected_voice_preview(state.id, preview.id)

    transcript = await temp_db.save_audio_transcript(
        npc_id=state.id,
        preview_id=preview.id,
        provider="whisper",
        text="Greetings, traveler.",
        metadata={"language": "en"},
    )

    assert transcript.preview_id == preview.id

    refreshed = await temp_db.get_cached_extraction(state.id)
    assert refreshed is not None
    assert refreshed.stage_flags["transcription"] is True
    assert refreshed.completed_stages[-1] in {"transcription", "complete"}


@pytest.mark.asyncio
async def test_stage_map_completion(temp_db: DatabaseManager):
    state = await _bootstrap_npc(temp_db, npc_id=12)

    profile = NPCDetails(
        npc_name=state.npc_name,
        personality_traits="calm",
        occupation="guide",
        social_role="helper",
        dialogue_patterns="gentle",
        emotional_range="warm",
        background_lore="Lumbridge",
        age_category="adult",
        build_type="average",
        attire_style="simple",
        distinctive_features="bald",
        color_palette="blue",
        visual_archetype="citizen",
        chathead_image_url=state.chathead_image_url,
        image_url=state.image_url,
        text_confidence=0.7,
        visual_confidence=0.6,
        overall_confidence=0.65,
        synthesis_notes="baseline",
    )

    await temp_db.upsert_character_profile(
        npc_id=state.id,
        profile=profile,
        text_analysis=None,
        visual_analysis=None,
        pipeline_version="v0",
    )

    preview = await temp_db.create_voice_preview(
        npc_id=state.id,
        voice_prompt="warm",
        sample_text="Hello!",
        provider="elevenlabs",
        model="eleven_ttv_v3",
        generation_metadata={},
        is_representative=True,
    )

    await temp_db.save_audio_transcript(
        npc_id=state.id,
        preview_id=preview.id,
        provider="whisper",
        text="Hello!",
        metadata={},
    )

    stage_map = await temp_db.compute_stage_map(state.id)
    assert stage_map["wiki_data"] is True
    assert stage_map["character_profile"] is True
    assert stage_map["voice_generation"] is True
    assert stage_map["voice_selection"] is True
    assert stage_map["transcription"] is True
    assert stage_map["complete"] is True


@pytest.mark.asyncio
async def test_clear_cache(temp_db: DatabaseManager):
    state = await _bootstrap_npc(temp_db, npc_id=33)
    assert state is not None

    await temp_db.clear_cache()

    cached = await temp_db.get_cached_extraction(33)
    assert cached is None
