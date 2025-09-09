import base64
from typing import Any

from elevenlabs import ElevenLabs

from voiceover_mage.config import get_config


class ElevenLabsVoiceService:
    """Service for ElevenLabs API integration, focused on generating previews."""

    def __init__(self):
        config = get_config()
        if not config.elevenlabs_api_key:
            # Defer error to call site so pipeline can continue gracefully
            self.client: ElevenLabs | None = None
        else:
            self.client = ElevenLabs(api_key=config.elevenlabs_api_key)

    async def generate_preview_audio(
        self,
        voice_description: str,
        sample_text: str,
        **kwargs: Any,
    ) -> tuple[bytes | None]:
        """Generates a voice preview and returns the audio as bytes.

        Uses ElevenLabs SDK `text_to_voice.design` endpoint. If provided sample_text
        is shorter than API limits, auto-generates a matching text.
        """
        if not self.client:
            raise ConnectionError("ElevenLabs API key not configured")
        try:
            resp = self.client.text_to_voice.design(
                model_id="eleven_ttv_v3",
                voice_description=voice_description,
                text=sample_text,
            )
            # Support both dict-like and object-like SDK responses
            previews = getattr(resp, "previews", None) or (resp.get("previews") if isinstance(resp, dict) else None)
            if not previews:
                raise ValueError("No previews returned from ElevenLabs")

            # Convert each base64 audio to bytes
            audio_bytes = [
                base64.b64decode(
                    getattr(clip, "audio_base_64", None)
                    or (clip.get("audio_base_64") if isinstance(clip, dict) else None)
                )
                for clip in previews
            ]

            if not audio_bytes:
                raise ValueError("No valid audio clips found")

            return tuple(audio_bytes)
        except Exception as e:
            raise ConnectionError(f"Failed to generate voice preview: {e}") from e
