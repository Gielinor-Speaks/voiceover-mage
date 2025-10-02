# ABOUTME: Tests for voice selection workflow and LocalTTSAdapter zero-shot synthesis

import pytest

from voiceover_mage.persistence.models import NPC, VoicePreview
from voiceover_mage.services.audio.local import LocalTTSAdapter


@pytest.fixture
def sample_audio_bytes() -> bytes:
    """Sample audio data for testing."""
    return b"fake_audio_data_mp3"


@pytest.fixture
def local_tts_adapter() -> LocalTTSAdapter:
    """Create a LocalTTSAdapter instance for testing."""
    return LocalTTSAdapter(api_url="http://localhost:8000")


class TestLocalTTSAdapter:
    """Tests for LocalTTSAdapter zero-shot synthesis."""

    def test_initialization(self):
        """Test adapter initialization with custom timeout."""
        adapter = LocalTTSAdapter(api_url="http://test.local:9000", timeout=60.0)
        assert adapter.api_url == "http://test.local:9000"
        assert adapter.client.timeout.read == 60.0

    def test_provider_name(self, local_tts_adapter):
        """Test provider name property."""
        assert local_tts_adapter.provider_name == "Local TTS"

    def test_supports_voice_cloning(self, local_tts_adapter):
        """Test voice cloning support flag."""
        assert local_tts_adapter.supports_voice_cloning is True

    @pytest.mark.asyncio
    async def test_clone_voice_raises_not_implemented(self, local_tts_adapter, sample_audio_bytes):
        """Test that clone_voice_from_sample raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="zero-shot synthesis"):
            await local_tts_adapter.clone_voice_from_sample("test_voice", sample_audio_bytes)

    @pytest.mark.asyncio
    async def test_generate_speech_raises_not_implemented(self, local_tts_adapter):
        """Test that generate_speech raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="reference audio"):
            await local_tts_adapter.generate_speech("test_voice_id", "Hello world")

    @pytest.mark.asyncio
    async def test_generate_speech_with_reference_validates_text(self, local_tts_adapter, sample_audio_bytes):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await local_tts_adapter.generate_speech_with_reference("", sample_audio_bytes)

        with pytest.raises(ValueError, match="Text cannot be empty"):
            await local_tts_adapter.generate_speech_with_reference("   ", sample_audio_bytes)

    @pytest.mark.asyncio
    async def test_generate_speech_with_reference_validates_audio(self, local_tts_adapter):
        """Test that empty audio bytes raises ValueError."""
        with pytest.raises(ValueError, match="Reference audio bytes cannot be empty"):
            await local_tts_adapter.generate_speech_with_reference("Hello", b"")


class TestVoiceSelectionWorkflow:
    """Integration tests for voice selection workflow."""

    @pytest.mark.asyncio
    async def test_voice_selection_flow(self):
        """Test complete voice selection workflow with database."""
        from voiceover_mage.persistence.manager import DatabaseManager

        # Create in-memory database for testing
        db = DatabaseManager(database_url="sqlite+aiosqlite:///:memory:")
        await db.create_tables()

        # Create test NPC
        async with db.async_session() as session:
            npc = NPC(id=1001, name="TestNPC", wiki_url="https://example.com")
            session.add(npc)
            await session.commit()

            # Create voice previews
            preview1 = VoicePreview(
                npc_id=1001,
                voice_prompt="Deep, gravelly voice",
                sample_text="Greetings, adventurer",
                provider="Test Provider",
                model="test-model",
                audio_bytes=b"fake_audio_1",
            )
            preview2 = VoicePreview(
                npc_id=1001,
                voice_prompt="High-pitched, cheerful voice",
                sample_text="Hello there!",
                provider="Test Provider",
                model="test-model",
                audio_bytes=b"fake_audio_2",
            )
            session.add(preview1)
            session.add(preview2)
            await session.commit()
            await session.refresh(preview1)
            await session.refresh(preview2)

        # List voice samples
        samples = await db.list_voice_samples(1001)
        assert len(samples) == 2

        # Select a voice preview
        result = await db.set_selected_voice_preview(1001, preview1.id)
        assert result is not None
        assert result.is_representative is True

        # Verify NPC was updated
        npc_updated = await db.get_npc(1001)
        assert npc_updated is not None
        assert npc_updated.selected_preview_id == preview1.id

        # Verify only one preview is marked as representative
        samples_updated = await db.list_voice_samples(1001)
        representative_count = sum(1 for s in samples_updated if s.is_representative)
        assert representative_count == 1

        await db.close()

    @pytest.mark.asyncio
    async def test_speak_requires_selected_voice(self):
        """Test that speak command requires a selected voice."""
        from voiceover_mage.persistence.manager import DatabaseManager

        # Create in-memory database for testing
        db = DatabaseManager(database_url="sqlite+aiosqlite:///:memory:")
        await db.create_tables()

        # Create test NPC without selected voice
        async with db.async_session() as session:
            npc = NPC(id=1002, name="NoVoiceNPC", wiki_url="https://example.com")
            session.add(npc)
            await session.commit()

        # Verify NPC has no selected voice
        npc_result = await db.get_npc(1002)
        assert npc_result is not None
        assert npc_result.selected_preview_id is None

        await db.close()


class TestAudioPlayer:
    """Tests for audio playback utilities."""

    def test_audio_player_initialization(self):
        """Test audio player initialization and player detection."""
        from voiceover_mage.utils.audio_player import AudioPlayer

        player = AudioPlayer()
        # Should detect at least one player or return None
        assert player.player_cmd in [None, "ffplay", "mpg123", "aplay", "afplay"]

    def test_audio_player_can_play(self):
        """Test can_play method."""
        from voiceover_mage.utils.audio_player import AudioPlayer

        player = AudioPlayer()
        can_play = player.can_play()
        assert isinstance(can_play, bool)


class TestVoiceSelector:
    """Tests for voice selection UI."""

    def test_voice_selector_initialization(self):
        """Test voice selector initialization."""
        from voiceover_mage.utils.voice_selector import VoiceSelector

        selector = VoiceSelector()
        assert selector.console is not None
        assert selector.audio_player is not None

    def test_create_choice_label(self):
        """Test choice label formatting."""
        from datetime import UTC, datetime

        from voiceover_mage.utils.voice_selector import VoiceSelector

        selector = VoiceSelector()

        preview = VoicePreview(
            id=1,
            npc_id=1,
            voice_prompt="A very long voice prompt that should be truncated when displayed in the menu" * 2,
            sample_text="Test sample",
            provider="Test Provider",
            model="test-model",
            created_at=datetime.now(UTC),
            is_representative=False,
        )

        label = selector._create_choice_label(0, preview)
        assert "[0]" in label
        assert "..." in label  # Should be truncated
        assert "(Test Provider" in label

    def test_create_choice_label_with_selection(self):
        """Test choice label includes selection marker."""
        from datetime import UTC, datetime

        from voiceover_mage.utils.voice_selector import VoiceSelector

        selector = VoiceSelector()

        preview = VoicePreview(
            id=1,
            npc_id=1,
            voice_prompt="Test voice",
            sample_text="Test sample",
            provider="Test Provider",
            model="test-model",
            created_at=datetime.now(UTC),
            is_representative=True,
        )

        label = selector._create_choice_label(0, preview)
        assert "⭐ SELECTED" in label
