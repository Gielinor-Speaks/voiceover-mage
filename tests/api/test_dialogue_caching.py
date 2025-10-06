# ABOUTME: Integration tests for dialogue caching and hash-based lookup

import pytest
import pytest_asyncio

from voiceover_mage.persistence.manager import DatabaseManager


@pytest.mark.asyncio
class TestDialogueCaching:
    """Test suite for dialogue caching with hash-based lookups."""

    @pytest_asyncio.fixture
    async def db_manager(self):
        """Create an in-memory test database."""
        db = DatabaseManager(database_url="sqlite+aiosqlite:///:memory:")
        await db.create_tables()
        yield db
        await db.close()

    @pytest_asyncio.fixture
    async def test_npc(self, db_manager):
        """Create a test NPC."""
        npc = await db_manager.ensure_npc(
            npc_id=1,
            name="Test Wise Old Man",
            wiki_url="https://oldschool.runescape.wiki/w/Wise_Old_Man",
        )
        return npc

    async def test_save_dialogue_computes_hash(self, db_manager, test_npc):
        """Saving dialogue should automatically compute and store hash."""
        dialogue = await db_manager.save_generated_dialogue(
            npc_id=test_npc.id,
            source_text="Hello, adventurer!",
            audio_bytes=b"fake_audio_data",
            generation_metadata={"provider": "test"},
        )

        assert dialogue.source_text_hash is not None
        assert len(dialogue.source_text_hash) == 64  # SHA256 hex length

    async def test_lookup_cached_dialogue_exact_match(self, db_manager, test_npc):
        """Looking up dialogue with exact text should return cached entry."""
        # Save original dialogue
        original = await db_manager.save_generated_dialogue(
            npc_id=test_npc.id,
            source_text="Hello, adventurer!",
            audio_bytes=b"original_audio",
            generation_metadata={"provider": "test"},
        )

        # Lookup with exact same text
        cached = await db_manager.get_cached_dialogue(test_npc.id, "Hello, adventurer!")

        assert cached is not None
        assert cached.id == original.id
        assert cached.audio_bytes == b"original_audio"

    async def test_lookup_cached_dialogue_normalized_match(self, db_manager, test_npc):
        """Lookup should match despite whitespace/case differences."""
        # Save with specific formatting
        await db_manager.save_generated_dialogue(
            npc_id=test_npc.id,
            source_text="Hello, adventurer!",
            audio_bytes=b"cached_audio",
        )

        # Lookup with different formatting but same normalized text
        test_cases = [
            "  Hello, adventurer!  ",  # Extra whitespace
            "HELLO, ADVENTURER!",  # Different case
            "  HELLO, ADVENTURER!  ",  # Both
        ]

        for text in test_cases:
            cached = await db_manager.get_cached_dialogue(test_npc.id, text)
            assert cached is not None, f"Failed to match: {text!r}"
            assert cached.audio_bytes == b"cached_audio"

    async def test_lookup_no_match_returns_none(self, db_manager, test_npc):
        """Lookup with non-existent text should return None."""
        cached = await db_manager.get_cached_dialogue(test_npc.id, "This text doesn't exist")
        assert cached is None

    async def test_lookup_different_npc_no_match(self, db_manager, test_npc):
        """Dialogue for one NPC shouldn't match another NPC."""
        # Save for NPC 1
        await db_manager.save_generated_dialogue(
            npc_id=test_npc.id,
            source_text="Hello!",
            audio_bytes=b"npc1_audio",
        )

        # Create NPC 2
        npc2 = await db_manager.ensure_npc(
            npc_id=2,
            name="Test Guard",
            wiki_url="https://oldschool.runescape.wiki/w/Guard",
        )

        # Lookup same text for NPC 2 should return None
        cached = await db_manager.get_cached_dialogue(npc2.id, "Hello!")
        assert cached is None

    async def test_multiple_dialogues_same_npc(self, db_manager, test_npc):
        """NPC can have multiple cached dialogues."""
        # Save multiple dialogues
        dialogue1 = await db_manager.save_generated_dialogue(
            npc_id=test_npc.id,
            source_text="Hello!",
            audio_bytes=b"audio1",
        )

        dialogue2 = await db_manager.save_generated_dialogue(
            npc_id=test_npc.id,
            source_text="Goodbye!",
            audio_bytes=b"audio2",
        )

        # Both should be retrievable
        cached1 = await db_manager.get_cached_dialogue(test_npc.id, "Hello!")
        cached2 = await db_manager.get_cached_dialogue(test_npc.id, "Goodbye!")

        assert cached1 is not None
        assert cached2 is not None
        assert cached1.id == dialogue1.id
        assert cached2.id == dialogue2.id
        assert cached1.audio_bytes == b"audio1"
        assert cached2.audio_bytes == b"audio2"

    async def test_hash_collision_prevention(self, db_manager, test_npc):
        """Similar but different texts should have different hashes."""
        dialogue1 = await db_manager.save_generated_dialogue(
            npc_id=test_npc.id,
            source_text="hello world",
            audio_bytes=b"audio1",
        )

        dialogue2 = await db_manager.save_generated_dialogue(
            npc_id=test_npc.id,
            source_text="helloworld",  # No space
            audio_bytes=b"audio2",
        )

        # Different hashes
        assert dialogue1.source_text_hash != dialogue2.source_text_hash

        # Correct lookups
        cached1 = await db_manager.get_cached_dialogue(test_npc.id, "hello world")
        cached2 = await db_manager.get_cached_dialogue(test_npc.id, "helloworld")

        assert cached1.id == dialogue1.id  # type: ignore[union-attr]
        assert cached2.id == dialogue2.id  # type: ignore[union-attr]
