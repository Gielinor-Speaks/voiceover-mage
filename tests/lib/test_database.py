# ABOUTME: Tests for database manager and async SQLite operations
# ABOUTME: Validates caching, persistence, and error handling for NPC extractions

import asyncio
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.pool import StaticPool

from voiceover_mage.persistence.manager import DatabaseManager
from voiceover_mage.persistence.models import NPCRawExtraction


@pytest_asyncio.fixture
async def temp_db():
    """Create a temporary in-memory database for testing."""
    # Use in-memory database with StaticPool for testing
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlmodel.ext.asyncio.session import AsyncSession

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    db.engine = engine
    db.async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    await db.create_tables()

    yield db

    await db.close()


@pytest.fixture
def sample_extraction():
    """Create a sample NPCRawExtraction for testing."""
    return NPCRawExtraction(
        npc_id=1,
        npc_name="Hans",
        wiki_url="https://oldschool.runescape.wiki/w/Hans",
        raw_markdown="# Hans\n\nHans is the servant of Duke Horacio...",
        chathead_image_url="https://example.com/hans_chathead.png",
        image_url="https://example.com/hans.png",
        extraction_success=True,
    )


class TestDatabaseManager:
    """Test database manager functionality."""

    @pytest.mark.asyncio
    async def test_create_tables(self, temp_db: DatabaseManager):
        """Test that tables are created successfully."""
        # Tables should be created by fixture
        # Try to query to verify table exists
        result = await temp_db.get_cached_extraction(999)
        assert result is None  # No data yet, but query should work

    @pytest.mark.asyncio
    async def test_save_extraction(self, temp_db: DatabaseManager, sample_extraction: NPCRawExtraction):
        """Test saving an extraction to the database."""
        saved = await temp_db.save_extraction(sample_extraction)

        assert saved.id is not None
        assert saved.npc_id == sample_extraction.npc_id
        assert saved.npc_name == sample_extraction.npc_name
        assert saved.created_at is not None

    @pytest.mark.asyncio
    async def test_get_cached_extraction(self, temp_db: DatabaseManager, sample_extraction: NPCRawExtraction):
        """Test retrieving a cached extraction."""
        # Save first
        await temp_db.save_extraction(sample_extraction)

        # Retrieve
        cached = await temp_db.get_cached_extraction(sample_extraction.npc_id)

        assert cached is not None
        assert cached.npc_id == sample_extraction.npc_id
        assert cached.npc_name == sample_extraction.npc_name
        assert cached.raw_markdown == sample_extraction.raw_markdown

    @pytest.mark.asyncio
    async def test_cache_miss(self, temp_db: DatabaseManager):
        """Test cache miss returns None."""
        result = await temp_db.get_cached_extraction(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_duplicate_npc_id_handling(self, temp_db: DatabaseManager, sample_extraction: NPCRawExtraction):
        """Test handling of duplicate npc_id entries."""
        # Save first extraction
        first = await temp_db.save_extraction(sample_extraction)

        # Try to save another extraction with same npc_id
        sample_extraction.raw_markdown = "Updated content"
        await temp_db.save_extraction(sample_extraction)

        # Should update existing or create new based on implementation
        # For caching, we want to keep the first one
        cached = await temp_db.get_cached_extraction(sample_extraction.npc_id)
        assert cached is not None
        assert cached.id == first.id  # Should return the first one

    @pytest.mark.asyncio
    async def test_error_extraction_persistence(self, temp_db: DatabaseManager):
        """Test saving extraction with error."""
        error_extraction = NPCRawExtraction(
            npc_id=404,
            npc_name="Unknown",
            wiki_url="https://oldschool.runescape.wiki/w/Unknown",
            raw_markdown="",
            extraction_success=False,
            error_message="Page not found",
        )

        saved = await temp_db.save_extraction(error_extraction)
        assert saved.extraction_success is False
        assert saved.error_message == "Page not found"

        # Should still be retrievable from cache
        cached = await temp_db.get_cached_extraction(404)
        assert cached is not None
        assert cached.extraction_success is False

    @pytest.mark.asyncio
    async def test_large_markdown_storage(self, temp_db: DatabaseManager):
        """Test storing large markdown content."""
        large_markdown = "# Test\n" + ("Lorem ipsum " * 1000)

        extraction = NPCRawExtraction(
            npc_id=2,
            npc_name="Test NPC",
            wiki_url="https://example.com",
            raw_markdown=large_markdown,
            extraction_success=True,
        )

        await temp_db.save_extraction(extraction)
        cached = await temp_db.get_cached_extraction(2)

        assert cached is not None
        assert cached.raw_markdown == large_markdown

    @pytest.mark.asyncio
    async def test_clear_cache(self, temp_db: DatabaseManager, sample_extraction: NPCRawExtraction):
        """Test clearing the cache."""
        # Save some data
        await temp_db.save_extraction(sample_extraction)

        # Clear cache
        await temp_db.clear_cache()

        # Should be empty now
        cached = await temp_db.get_cached_extraction(sample_extraction.npc_id)
        assert cached is None

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, temp_db: DatabaseManager):
        """Test concurrent database operations."""
        extractions = [
            NPCRawExtraction(
                npc_id=i,
                npc_name=f"NPC {i}",
                wiki_url=f"https://example.com/{i}",
                raw_markdown=f"Content for NPC {i}",
                extraction_success=True,
            )
            for i in range(10)
        ]

        # Save all concurrently
        tasks = [temp_db.save_extraction(e) for e in extractions]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(r.id is not None for r in results)

        # Retrieve all concurrently
        tasks = [temp_db.get_cached_extraction(i) for i in range(10)]
        cached = await asyncio.gather(*tasks)

        assert len(cached) == 10
        assert all(c is not None for c in cached)


class TestNPCRawExtraction:
    """Test the NPCRawExtraction model."""

    def test_model_creation(self):
        """Test creating an NPCRawExtraction model."""
        extraction = NPCRawExtraction(
            npc_id=1,
            npc_name="Hans",
            wiki_url="https://example.com",
            raw_markdown="# Hans",
            extraction_success=True,
        )

        assert extraction.npc_id == 1
        assert extraction.npc_name == "Hans"
        assert extraction.chathead_image_url is None
        assert extraction.image_url is None
        assert extraction.error_message is None

    def test_model_with_images(self):
        """Test model with image URLs."""
        extraction = NPCRawExtraction(
            npc_id=1,
            npc_name="Hans",
            wiki_url="https://example.com",
            raw_markdown="# Hans",
            chathead_image_url="https://example.com/chathead.png",
            image_url="https://example.com/image.png",
            extraction_success=True,
        )

        assert extraction.chathead_image_url == "https://example.com/chathead.png"
        assert extraction.image_url == "https://example.com/image.png"

    def test_model_with_error(self):
        """Test model with error state."""
        extraction = NPCRawExtraction(
            npc_id=1,
            npc_name="Unknown",
            wiki_url="https://example.com",
            raw_markdown="",
            extraction_success=False,
            error_message="Failed to extract",
        )

        assert extraction.extraction_success is False
        assert extraction.error_message == "Failed to extract"

    def test_datetime_default(self):
        """Test that created_at has a proper default."""
        before = datetime.now(UTC)
        extraction = NPCRawExtraction(
            npc_id=1,
            npc_name="Hans",
            wiki_url="https://example.com",
            raw_markdown="# Hans",
            extraction_success=True,
        )
        after = datetime.now(UTC)

        # The created_at should be set automatically with a default factory
        assert extraction.created_at is not None
        assert isinstance(extraction.created_at, datetime)
        # Should be between before and after creation
        assert before <= extraction.created_at <= after
        # Should be timezone-aware (UTC)
        assert extraction.created_at.tzinfo is not None
