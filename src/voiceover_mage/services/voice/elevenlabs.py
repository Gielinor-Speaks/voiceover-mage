import base64

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
    ) -> tuple[bytes, ...]:
        """Generates voice previews and returns all decoded audio clips.

        Uses ElevenLabs SDK `text_to_voice.design` endpoint. If provided sample_text
        is shorter than API limits, auto-generates a matching text.
        """
        if not self.client:
            raise ConnectionError("ElevenLabs API key not configured")
        try:
            # If provided text is short, let ElevenLabs auto-generate matching text
            auto_generate = len(sample_text or "") < 100 or len(sample_text or "") > 1000
            resp = self.client.text_to_voice.design(
                model_id="eleven_ttv_v3",
                voice_description=voice_description,
                text=sample_text if not auto_generate else None,
                auto_generate_text=auto_generate,
            )

            # Support both object-like and dict-like SDK responses without getattr
            try:
                previews = resp.previews  # type: ignore[attr-defined]
            except Exception:
                previews = resp["previews"] if isinstance(resp, dict) else None  # type: ignore[index]
            if not previews:
                raise ValueError("No previews returned from ElevenLabs")

            # Convert all base64 audio previews to bytes
            audio_list: list[bytes] = []
            for clip in previews:
                try:
                    encoded = clip.audio_base_64  # type: ignore[attr-defined]
                except Exception:
                    encoded = clip.get("audio_base_64") if isinstance(clip, dict) else None  # type: ignore[call-overload]
                if isinstance(encoded, str | bytes):
                    audio_list.append(base64.b64decode(encoded))

            if not audio_list:
                raise ValueError("No valid audio clips found")

            return tuple(audio_list)
        except Exception as e:
            raise ConnectionError(f"Failed to generate voice preview: {e}") from e
