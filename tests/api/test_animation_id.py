# ABOUTME: Tests for animation ID parameter flow through the voice generation pipeline
# ABOUTME: Verifies that animation_id is properly passed from API to TTS service

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from voiceover_mage.api.main import app
from voiceover_mage.api.services import VoiceGenerationResult


class TestAnimationIDFlow:
    """Test suite for animation_id parameter propagation."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_post_speak_passes_animation_id_to_service(self, client):
        """Test that POST /speak endpoint passes animation_id to VoiceGenerationService."""
        with patch("voiceover_mage.api.routes.generation.VoiceGenerationService") as mock_service_class:
            # Setup mock service instance
            mock_service = MagicMock()
            mock_service.generate_speech = AsyncMock(
                return_value=VoiceGenerationResult(
                    npc_id=1,
                    npc_name="Test Guard",
                    text="Hello there!",
                    audio_bytes=b"generated_audio",
                    cached=False,
                    provider="local",
                    generation_metadata={},
                )
            )
            mock_service_class.return_value = mock_service

            # Make request with animation_id
            response = client.post(
                "/api/v1/npc/1/speak",
                json={"text": "Hello there!", "animation_id": 588},
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["npc_id"] == 1
            assert data["text"] == "Hello there!"

            # Verify service was called with animation_id
            mock_service.generate_speech.assert_called_once_with(1, "Hello there!", animation_id=588)

    def test_post_speak_without_animation_id(self, client):
        """Test that POST /speak works without animation_id (backward compatibility)."""
        with patch("voiceover_mage.api.routes.generation.VoiceGenerationService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.generate_speech = AsyncMock(
                return_value=VoiceGenerationResult(
                    npc_id=1,
                    npc_name="Test Guard",
                    text="Hello there!",
                    audio_bytes=b"generated_audio",
                    cached=False,
                    provider="local",
                    generation_metadata={},
                )
            )
            mock_service_class.return_value = mock_service

            # Make request WITHOUT animation_id
            response = client.post(
                "/api/v1/npc/1/speak",
                json={"text": "Hello there!"},
            )

            # Verify response
            assert response.status_code == 200

            # Verify service was called with animation_id=None
            mock_service.generate_speech.assert_called_once_with(1, "Hello there!", animation_id=None)

    def test_get_speak_audio_passes_animation_id(self, client):
        """Test that GET /speak/audio endpoint passes animation_id to service."""
        with patch("voiceover_mage.api.routes.generation.VoiceGenerationService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.generate_speech = AsyncMock(
                return_value=VoiceGenerationResult(
                    npc_id=1,
                    npc_name="Test Guard",
                    text="Hello there!",
                    audio_bytes=b"generated_audio",
                    cached=False,
                    provider="local",
                    generation_metadata={},
                )
            )
            mock_service_class.return_value = mock_service

            # Make GET request with animation_id as query parameter
            response = client.get("/api/v1/npc/1/speak/audio?text=Hello there!&animation_id=589")

            # Verify response
            assert response.status_code == 200
            assert response.headers["content-type"] == "audio/mpeg"

            # Verify service was called with animation_id
            mock_service.generate_speech.assert_called_once_with(1, "Hello there!", animation_id=589)

    @pytest.mark.asyncio
    async def test_service_passes_animation_id_to_tts_adapter(self):
        """Test that VoiceGenerationService passes animation_id to LocalTTSAdapter."""
        from voiceover_mage.api.services import VoiceGenerationService
        from voiceover_mage.persistence.manager import DatabaseManager
        from voiceover_mage.persistence.models import NPC, VoicePreview

        # Create in-memory test database
        db = DatabaseManager(database_url="sqlite+aiosqlite:///:memory:")
        await db.create_tables()

        try:
            # Create NPC with voice preview
            npc = await db.ensure_npc(
                npc_id=1, name="Test NPC", wiki_url="https://oldschool.runescape.wiki/w/Test"
            )

            preview = VoicePreview(
                npc_id=1,
                provider="local",
                model="test-model",
                voice_prompt="Test voice",
                sample_text="Test sample text",
                audio_bytes=b"test_audio_data",
            )
            async with db.async_session() as session:
                session.add(preview)
                await session.commit()
                await session.refresh(preview)

            await db.set_selected_voice_preview(1, preview.id)  # type: ignore[arg-type]

            # Mock LocalTTSAdapter
            with patch("voiceover_mage.api.services.LocalTTSAdapter") as mock_tts_class:
                mock_tts_instance = MagicMock()
                mock_tts_instance.generate_speech_with_reference = AsyncMock(
                    return_value=b"generated_audio"
                )
                mock_tts_class.return_value = mock_tts_instance

                service = VoiceGenerationService(db)
                result = await service.generate_speech(1, "Test text", animation_id=590)

                # Verify animation_id was passed to TTS adapter
                call_kwargs = mock_tts_instance.generate_speech_with_reference.call_args.kwargs
                assert call_kwargs["animation_id"] == 590
                assert call_kwargs["text"] == "Test text"
                assert call_kwargs["reference_audio_bytes"] == b"test_audio_data"
                assert result.audio_bytes == b"generated_audio"

        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_animation_id_maps_to_emotion_settings(self):
        """Test that animation_id is used to determine emotion settings in LocalTTSAdapter."""
        from voiceover_mage.services.audio.local import LocalTTSAdapter

        adapter = LocalTTSAdapter()

        # Test with animation ID
        emotion_settings_588 = adapter._get_emotion_settings(588)
        assert "emotion_mode" in emotion_settings_588
        assert "emotion_weight" in emotion_settings_588

        # Test with None (should use fallback)
        emotion_settings_none = adapter._get_emotion_settings(None)
        assert emotion_settings_none["emotion_mode"] == "text_description"
        assert emotion_settings_none["emotion_weight"] == 0.6

    @pytest.mark.asyncio
    async def test_tts_adapter_sends_animation_id_to_api(self, httpx_mock):
        """Test that LocalTTSAdapter includes animation_id in the API request."""
        from voiceover_mage.services.audio.local import LocalTTSAdapter

        adapter = LocalTTSAdapter("http://localhost:8000")

        # Mock the TTS API response
        httpx_mock.add_response(
            url="http://localhost:8000/synthesize",
            method="POST",
            json={
                "audio": "ZmFrZV9hdWRpbw==",  # base64 "fake_audio"
                "audio_duration_seconds": 2.5,
                "inference_time_seconds": 1.2,
            },
        )

        # Call with animation_id
        audio = await adapter.generate_speech_with_reference(
            text="Hello",
            reference_audio_bytes=b"reference",
            animation_id=588,
        )

        assert audio == b"fake_audio"

        # Verify the request included animation_id in emotion settings
        request = httpx_mock.get_request()
        assert request is not None
        payload = request.read()
        import json

        payload_dict = json.loads(payload)

        # Should have emotion settings from animation ID 588
        # (either emotion_vector or text_description depending on mapping)
        assert "emotion_mode" in payload_dict
        assert "emotion_weight" in payload_dict

        await adapter.close()

    @pytest.mark.asyncio
    async def test_animation_id_stored_in_generation_metadata(self):
        """Test that animation_id is saved to the database in generation metadata."""
        from voiceover_mage.api.services import VoiceGenerationService
        from voiceover_mage.persistence.manager import DatabaseManager

        # Create in-memory test database
        db = DatabaseManager(database_url="sqlite+aiosqlite:///:memory:")
        await db.create_tables()

        try:
            # Create NPC with voice preview
            npc = await db.ensure_npc(
                npc_id=1, name="Test NPC", wiki_url="https://oldschool.runescape.wiki/w/Test"
            )

            from voiceover_mage.persistence.models import VoicePreview

            preview = VoicePreview(
                npc_id=1,
                provider="local",
                model="test-model",
                voice_prompt="Test voice",
                sample_text="Test sample text",
                audio_bytes=b"test_audio_data",
            )
            async with db.async_session() as session:
                session.add(preview)
                await session.commit()
                await session.refresh(preview)

            await db.set_selected_voice_preview(1, preview.id)  # type: ignore[arg-type]

            # Mock LocalTTSAdapter
            with patch("voiceover_mage.api.services.LocalTTSAdapter") as mock_tts_class:
                mock_tts_instance = MagicMock()
                mock_tts_instance.generate_speech_with_reference = AsyncMock(
                    return_value=b"generated_audio"
                )
                mock_tts_class.return_value = mock_tts_instance

                service = VoiceGenerationService(db)
                result = await service.generate_speech(1, "Test text", animation_id=588)

                # Verify animation_id was stored in metadata
                assert result.generation_metadata["animation_id"] == 588

                # Verify it was saved to database
                dialogue = await db.get_cached_dialogue(1, "Test text")
                assert dialogue is not None
                assert dialogue.generation_metadata["animation_id"] == 588

        finally:
            await db.close()
