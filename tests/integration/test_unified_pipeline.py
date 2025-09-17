# ABOUTME: Integration tests for normalized UnifiedPipelineService
# ABOUTME: Exercises the pipeline with in-memory persistence and patched providers

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from voiceover_mage.core.unified_pipeline import UnifiedPipelineService
from voiceover_mage.extraction.analysis.synthesizer import NPCDetails
from voiceover_mage.persistence.manager import DatabaseManager, NPCPipelineState


@pytest_asyncio.fixture
async def temp_db() -> DatabaseManager:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool
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
    await db.clear_cache()
    await db.close()


async def _seed_raw_state(db: DatabaseManager, npc_id: int) -> NPCPipelineState:
    await db.ensure_npc(
        npc_id=npc_id,
        name="Hans",
        variant=None,
        wiki_url="https://oldschool.runescape.wiki/w/Hans",
    )
    await db.upsert_wiki_snapshot(
        npc_id=npc_id,
        raw_markdown="# Hans\nFaithful servant of Lumbridge Castle.",
        chathead_image_url="https://example.com/hans_chat.png",
        image_url="https://example.com/hans.png",
        raw_data=None,
        source_checksum="seed",
        fetched_at=datetime.now(UTC),
        extraction_success=True,
        error_message=None,
    )
    state = await db.get_cached_extraction(npc_id)
    assert state is not None
    return state


class _BinarySink:
    def write(self, *_):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _binary_open(*_args, **_kwargs):
    return _BinarySink()


@pytest.mark.asyncio
async def test_run_full_pipeline_with_mocked_dependencies(temp_db: DatabaseManager):
    pipeline = UnifiedPipelineService(database=temp_db, force_refresh=True, api_key=None)

    async def fake_extract(npc_id: int) -> NPCPipelineState:
        return await _seed_raw_state(temp_db, npc_id)

    pipeline.raw_service.extract_npc = AsyncMock(side_effect=fake_extract)
    pipeline.raw_service.close = AsyncMock()

    details = NPCDetails(
        npc_name="Hans",
        personality_traits="loyal",
        occupation="servant",
        social_role="guide",
        dialogue_patterns="polite",
        emotional_range="warm",
        background_lore="castle duties",
        age_category="adult",
        build_type="average",
        attire_style="simple",
        distinctive_features="bald",
        color_palette="blue",
        visual_archetype="citizen",
        chathead_image_url="https://example.com/hans_chat.png",
        image_url="https://example.com/hans.png",
        text_confidence=0.8,
        visual_confidence=0.7,
        overall_confidence=0.75,
        synthesis_notes="test",
    )

    pipeline.intelligent_extractor = Mock()
    pipeline.intelligent_extractor.aforward = AsyncMock(return_value=details)

    pipeline.voice_prompt_generator.aforward = AsyncMock(
        return_value={"description": "warm voice", "sample_text": "Greetings adventurer."}
    )
    pipeline.voice_service.generate_preview_audio = AsyncMock(return_value=[b"audio-bytes"])

    with (
        patch("pathlib.Path.mkdir", return_value=None),
        patch("builtins.open", _binary_open),
    ):
        state = await pipeline.run_full_pipeline(101)

    assert state.id == 101
    assert state.stage_flags["wiki_data"] is True
    assert state.stage_flags["character_profile"] is True
    assert state.stage_flags["voice_generation"] is True
    assert state.stage_flags["voice_selection"] is False  # selection not set without explicit choice

    previews = await temp_db.list_voice_previews(101)
    assert len(previews) == 1
    assert previews[0].voice_prompt == "warm voice"

    stage_map = await temp_db.compute_stage_map(101)
    assert stage_map["wiki_data"] and stage_map["character_profile"]
    assert stage_map["complete"] is False
