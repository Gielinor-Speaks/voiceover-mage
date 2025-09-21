import base64
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from voiceover_mage.services.voice.elevenlabs import ElevenLabsVoiceService


@pytest.fixture
def mock_elevenlabs_sdk(monkeypatch):
    fake_client = MagicMock()
    # Attach nested attribute text_to_voice.design
    fake_client.text_to_voice.design = MagicMock()
    monkeypatch.setattr("voiceover_mage.services.voice.elevenlabs.ElevenLabs", lambda *a, **k: fake_client)
    return fake_client


@pytest.mark.asyncio
async def test_generate_preview_audio_success(mock_elevenlabs_sdk):
    # Arrange
    audio_bytes = b"audio_bytes"
    mock_preview = SimpleNamespace(
        audio_base_64=base64.b64encode(audio_bytes).decode("ascii"),
        generated_voice_id="abc123",
        media_type="audio/mpeg",
        duration_secs=1.23,
        language="en",
    )
    mock_response = SimpleNamespace(previews=[mock_preview], text="Generated preview text")
    mock_elevenlabs_sdk.text_to_voice.design.return_value = mock_response

    service = ElevenLabsVoiceService()
    voice_desc = "A test voice."
    sample_text = "Hello world."  # short; service should auto-generate text

    # Act
    result = await service.generate_preview_audio(voice_desc, sample_text)

    # Assert
    assert isinstance(result, tuple)
    assert result and result[0] == audio_bytes
    mock_elevenlabs_sdk.text_to_voice.design.assert_called_once()
    _, kwargs = mock_elevenlabs_sdk.text_to_voice.design.call_args
    assert kwargs["voice_description"] == voice_desc
    assert kwargs.get("auto_generate_text") is True
