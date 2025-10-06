# ABOUTME: Tests for API error handling and exception hierarchy

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from voiceover_mage.api.exceptions import (
    AudioServiceError,
    NPCNotFoundError,
    PipelineExecutionError,
    TTSGenerationError,
    VoiceNotConfiguredError,
)
from voiceover_mage.api.main import app
from voiceover_mage.persistence.manager import DatabaseManager


class TestErrorResponses:
    """Test suite for API error handling."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest_asyncio.fixture
    async def mock_db(self):
        """Create a mock database manager."""
        db = AsyncMock(spec=DatabaseManager)
        return db

    def test_npc_not_found_returns_404(self, client):
        """NPC not found should return 404 with specific error."""
        with patch("voiceover_mage.api.routes.generation.VoiceGenerationService") as mock_service:
            mock_service.return_value.generate_speech = AsyncMock(side_effect=NPCNotFoundError(npc_id=99999))

            response = client.post("/api/v1/npc/99999/speak", json={"text": "Hello"})

            assert response.status_code == 404
            data = response.json()
            assert data["detail"]["error"] == "NPC_NOT_FOUND"
            assert data["detail"]["npc_id"] == 99999
            assert "does not exist" in data["detail"]["message"]

    def test_voice_not_configured_returns_503(self, client):
        """Voice not configured should return 503 with helpful message."""
        with patch("voiceover_mage.api.routes.generation.VoiceGenerationService") as mock_service:
            mock_service.return_value.generate_speech = AsyncMock(
                side_effect=VoiceNotConfiguredError(npc_id=123, npc_name="Guard")
            )

            response = client.post("/api/v1/npc/123/speak", json={"text": "Hello"})

            assert response.status_code == 503
            data = response.json()
            assert data["detail"]["error"] == "VOICE_NOT_CONFIGURED"
            assert data["detail"]["npc_id"] == 123
            assert data["detail"]["npc_name"] == "Guard"
            assert "suggestion" in data["detail"]

    def test_tts_service_unavailable_returns_503(self, client):
        """TTS service unavailable should return 503 with retryable flag."""
        with patch("voiceover_mage.api.routes.generation.VoiceGenerationService") as mock_service:
            mock_service.return_value.generate_speech = AsyncMock(
                side_effect=AudioServiceError(service_url="http://localhost:8001", reason="Connection refused")
            )

            response = client.post("/api/v1/npc/1/speak", json={"text": "Hello"})

            assert response.status_code == 503
            data = response.json()
            assert data["detail"]["error"] == "TTS_SERVICE_UNAVAILABLE"
            assert data["detail"]["retryable"] is True
            assert data["detail"]["service_url"] == "http://localhost:8001"

    def test_tts_generation_failed_returns_500(self, client):
        """TTS generation failure should return 500 with retryable flag."""
        with patch("voiceover_mage.api.routes.generation.VoiceGenerationService") as mock_service:
            mock_service.return_value.generate_speech = AsyncMock(
                side_effect=TTSGenerationError(npc_id=1, reason="Audio encoding failed")
            )

            response = client.post("/api/v1/npc/1/speak", json={"text": "Hello"})

            assert response.status_code == 500
            data = response.json()
            assert data["detail"]["error"] == "TTS_GENERATION_FAILED"
            assert data["detail"]["retryable"] is True
            assert "Audio encoding failed" in data["detail"]["reason"]

    def test_pipeline_failed_returns_500(self, client):
        """Pipeline execution failure should return 500 with stage info."""
        with patch("voiceover_mage.api.routes.generation.VoiceGenerationService") as mock_service:
            mock_service.return_value.generate_speech = AsyncMock(
                side_effect=PipelineExecutionError(npc_id=1, stage="voice_generation", reason="API quota exceeded")
            )

            response = client.post("/api/v1/npc/1/speak", json={"text": "Hello"})

            assert response.status_code == 500
            data = response.json()
            assert data["detail"]["error"] == "PIPELINE_EXECUTION_FAILED"
            assert data["detail"]["stage"] == "voice_generation"
            assert data["detail"]["retryable"] is False
            assert "quota exceeded" in data["detail"]["reason"]

    def test_unexpected_error_returns_500(self, client):
        """Unexpected errors should return generic 500."""
        with patch("voiceover_mage.api.routes.generation.VoiceGenerationService") as mock_service:
            mock_service.return_value.generate_speech = AsyncMock(side_effect=RuntimeError("Something went wrong"))

            response = client.post("/api/v1/npc/1/speak", json={"text": "Hello"})

            assert response.status_code == 500
            data = response.json()
            assert data["detail"]["error"] == "INTERNAL_SERVER_ERROR"
            assert "unexpected error" in data["detail"]["message"].lower()


class TestExceptionHierarchy:
    """Test suite for custom exception classes."""

    def test_npc_not_found_exception(self):
        """NPCNotFoundError should store NPC ID."""
        exc = NPCNotFoundError(npc_id=123)
        assert exc.npc_id == 123
        assert "123" in str(exc)

    def test_voice_not_configured_exception(self):
        """VoiceNotConfiguredError should store NPC details."""
        exc = VoiceNotConfiguredError(npc_id=456, npc_name="Wise Old Man")
        assert exc.npc_id == 456
        assert exc.npc_name == "Wise Old Man"
        assert "456" in str(exc)
        assert "Wise Old Man" in str(exc)

    def test_tts_generation_error_exception(self):
        """TTSGenerationError should store reason and original error."""
        original = ValueError("Invalid audio format")
        exc = TTSGenerationError(npc_id=1, reason="Format error", original_error=original)
        assert exc.npc_id == 1
        assert exc.reason == "Format error"
        assert exc.original_error is original

    def test_pipeline_execution_error_exception(self):
        """PipelineExecutionError should store stage and reason."""
        exc = PipelineExecutionError(npc_id=789, stage="extraction", reason="Network timeout")
        assert exc.npc_id == 789
        assert exc.stage == "extraction"
        assert exc.reason == "Network timeout"
        assert "extraction" in str(exc)

    def test_audio_service_error_exception(self):
        """AudioServiceError should store service URL and reason."""
        exc = AudioServiceError(service_url="http://tts:8000", reason="Connection refused")
        assert exc.service_url == "http://tts:8000"
        assert exc.reason == "Connection refused"
        assert "http://tts:8000" in str(exc)


class TestHttpxExceptionHandling:
    """Test suite for httpx-specific exception handling in VoiceGenerationService."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_httpx_connect_error_returns_503(self, client):
        """httpx.ConnectError should be caught and return 503 AudioServiceError."""
        with patch("voiceover_mage.api.services.VoiceGenerationService.generate_speech") as mock_generate:
            # Simulate httpx.ConnectError being raised during TTS call
            mock_generate.side_effect = AudioServiceError(
                service_url="http://localhost:8000", reason="[Errno 111] Connection refused"
            )

            response = client.post("/api/v1/npc/1/speak", json={"text": "Test dialogue"})

            assert response.status_code == 503
            data = response.json()
            assert data["detail"]["error"] == "TTS_SERVICE_UNAVAILABLE"
            assert data["detail"]["retryable"] is True
            assert "unavailable" in data["detail"]["message"].lower()

    def test_httpx_timeout_error_returns_503(self, client):
        """httpx.TimeoutException should be caught and return 503 AudioServiceError."""
        with patch("voiceover_mage.api.services.VoiceGenerationService.generate_speech") as mock_generate:
            # Simulate httpx.TimeoutException being raised during TTS call
            mock_generate.side_effect = AudioServiceError(
                service_url="http://localhost:8000", reason="Request timeout after 30s"
            )

            response = client.post("/api/v1/npc/1/speak", json={"text": "Test dialogue"})

            assert response.status_code == 503
            data = response.json()
            assert data["detail"]["error"] == "TTS_SERVICE_UNAVAILABLE"
            assert data["detail"]["retryable"] is True

    def test_httpx_http_error_returns_503(self, client):
        """httpx.HTTPError (4xx/5xx from TTS service) should return 503 AudioServiceError."""
        with patch("voiceover_mage.api.services.VoiceGenerationService.generate_speech") as mock_generate:
            # Simulate httpx.HTTPError being raised during TTS call
            mock_generate.side_effect = AudioServiceError(
                service_url="http://localhost:8000", reason="HTTP error: Server returned 500 Internal Server Error"
            )

            response = client.post("/api/v1/npc/1/speak", json={"text": "Test dialogue"})

            assert response.status_code == 503
            data = response.json()
            assert data["detail"]["error"] == "TTS_SERVICE_UNAVAILABLE"
            assert data["detail"]["retryable"] is True

    @pytest.mark.asyncio
    async def test_service_catches_httpx_connect_error(self):
        """VoiceGenerationService should catch httpx.ConnectError and raise AudioServiceError."""
        from voiceover_mage.api.services import VoiceGenerationService
        from voiceover_mage.persistence.models import NPC, VoicePreview

        # Create mock database manager without strict spec
        mock_db = AsyncMock()

        # Mock NPC with selected preview ID
        mock_npc = NPC(id=1, name="Test Guard", wiki_url="http://example.com", selected_preview_id=1)
        mock_preview = VoicePreview(
            id=1,
            npc_id=1,
            provider="elevenlabs",
            voice_prompt="deep male voice",
            audio_bytes=b"fake_audio_data",
            sample_text="Test sample",
            model="eleven_multilingual_v2",
        )

        # Setup mocks
        mock_db.get_cached_dialogue = AsyncMock(return_value=None)
        mock_db.get_npc = AsyncMock(return_value=mock_npc)

        # Mock the async session context manager
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_preview)
        mock_db.async_session = Mock()
        mock_db.async_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.async_session.return_value.__aexit__ = AsyncMock(return_value=None)

        service = VoiceGenerationService(mock_db)

        # Patch LocalTTSAdapter to raise httpx.ConnectError
        with patch("voiceover_mage.api.services.LocalTTSAdapter") as mock_tts:
            mock_tts.return_value.generate_speech_with_reference = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            # Should raise AudioServiceError, not TTSGenerationError
            with pytest.raises(AudioServiceError) as exc_info:
                await service.generate_speech(npc_id=1, text="Hello adventurer")

            assert exc_info.value.service_url == service.config.local_tts_api_url
            assert "Connection refused" in exc_info.value.reason

    @pytest.mark.asyncio
    async def test_service_catches_httpx_http_error(self):
        """VoiceGenerationService should catch httpx.HTTPError and raise AudioServiceError."""
        from voiceover_mage.api.services import VoiceGenerationService
        from voiceover_mage.persistence.models import NPC, VoicePreview

        # Create mock database manager without strict spec
        mock_db = AsyncMock()

        # Mock NPC with selected preview ID
        mock_npc = NPC(id=1, name="Test Guard", wiki_url="http://example.com", selected_preview_id=1)
        mock_preview = VoicePreview(
            id=1,
            npc_id=1,
            provider="elevenlabs",
            voice_prompt="deep male voice",
            audio_bytes=b"fake_audio_data",
            sample_text="Test sample",
            model="eleven_multilingual_v2",
        )

        # Setup mocks
        mock_db.get_cached_dialogue = AsyncMock(return_value=None)
        mock_db.get_npc = AsyncMock(return_value=mock_npc)

        # Mock the async session context manager
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_preview)
        mock_db.async_session = Mock()
        mock_db.async_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.async_session.return_value.__aexit__ = AsyncMock(return_value=None)

        service = VoiceGenerationService(mock_db)

        # Patch LocalTTSAdapter to raise httpx.HTTPError
        with patch("voiceover_mage.api.services.LocalTTSAdapter") as mock_tts:
            # Create a mock request for HTTPError
            mock_request = Mock(spec=httpx.Request)
            mock_request.url = "http://localhost:8000/generate"
            mock_request.method = "POST"

            mock_tts.return_value.generate_speech_with_reference = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "500 Internal Server Error", request=mock_request, response=Mock(status_code=500)
                )
            )

            # Should raise AudioServiceError, not TTSGenerationError
            with pytest.raises(AudioServiceError) as exc_info:
                await service.generate_speech(npc_id=1, text="Hello adventurer")

            assert exc_info.value.service_url == service.config.local_tts_api_url
            assert "HTTP error" in exc_info.value.reason
