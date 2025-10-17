# ABOUTME: Local TTS provider implementation for zero-shot voice synthesis
# ABOUTME: Handles voice synthesis using our custom IndexTTSv2 API with reference audio samples

import base64
from typing import Any

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import TTSProvider


class LocalTTSAdapter(TTSProvider):
    """Adapter for local TTS APIs that support zero-shot voice synthesis.

    Designed for our custom IndexTTSv2 REST API. Works entirely with bytes
    from the database rather than files on disk. No persistent voice cloning -
    reference audio is sent with each synthesis request.
    """

    def __init__(self, api_url: str = "http://localhost:8000", timeout: float = 30.0):
        """Initialize the local TTS adapter.

        Args:
            api_url: URL of the local TTS API service
            timeout: HTTP timeout in seconds for API requests
        """
        self.api_url = api_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=timeout)

    async def clone_voice_from_sample(self, name: str, sample_bytes: bytes) -> str:
        """NOT SUPPORTED - Local TTS uses zero-shot synthesis, not persistent cloning.

        This method exists for interface compatibility but should not be used.
        Use generate_speech_with_reference() instead.

        Args:
            name: Human-readable identifier for the voice
            sample_bytes: Raw audio data (MP3, WAV, etc.)

        Returns:
            str: The name parameter (no actual cloning occurs)

        Raises:
            NotImplementedError: Always raises - use generate_speech_with_reference() instead
        """
        raise NotImplementedError(
            "Local TTS does not support persistent voice cloning. "
            "Use generate_speech_with_reference() to perform zero-shot synthesis with reference audio."
        )

    async def generate_speech(self, voice_id: str, text: str) -> bytes:
        """NOT SUPPORTED - Local TTS requires reference audio for each synthesis.

        This method exists for interface compatibility but should not be used.
        Use generate_speech_with_reference() instead.

        Args:
            voice_id: Voice ID (not used for local TTS)
            text: Text to convert to speech

        Returns:
            bytes: WAV audio data

        Raises:
            NotImplementedError: Always raises - use generate_speech_with_reference() instead
        """
        raise NotImplementedError(
            "Local TTS requires reference audio for each synthesis request. "
            "Use generate_speech_with_reference() with audio bytes from the database."
        )

    async def generate_speech_with_reference(
        self, text: str, reference_audio_bytes: bytes, audio_format: str = ".wav"
    ) -> bytes:
        """Generate speech using a reference voice sample via zero-shot synthesis.

        Args:
            text: Text to convert to speech
            reference_audio_bytes: Raw audio data to use as voice reference
            audio_format: Format of the reference audio (e.g., '.wav', '.mp3')

        Returns:
            bytes: WAV audio data

        Raises:
            ValueError: If text or reference_audio_bytes is empty
            Exception: API or network errors
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if not reference_audio_bytes:
            raise ValueError("Reference audio bytes cannot be empty")

        logger.info(
            f"Generating speech with {len(reference_audio_bytes)} bytes reference audio for text: {text[:50]}..."
        )

        try:
            # Encode the audio bytes for API transmission
            audio_base64 = base64.b64encode(reference_audio_bytes).decode("utf-8")

            # Call the local TTS API
            response = await self._synthesize_with_voice_sample(
                text=text, audio_base64=audio_base64, audio_format=audio_format
            )

            # Decode the response audio
            audio_data = base64.b64decode(response["audio"])

            logger.debug(f"Generated {len(audio_data)} bytes of audio data")
            logger.info("Speech generation completed")

            return audio_data

        except Exception as e:
            logger.error(f"Failed to generate speech: {e}")
            raise

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "Local TTS"

    @property
    def supports_voice_cloning(self) -> bool:
        """Return voice cloning support status."""
        return True

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _synthesize_with_voice_sample(self, text: str, audio_base64: str, audio_format: str) -> dict[str, Any]:
        """Call the local TTS API to synthesize speech with voice reference.

        Uses our custom IndexTTSv2 API format.

        Args:
            text: Text to synthesize
            audio_base64: Base64-encoded reference audio
            audio_format: Audio format (e.g., 'mp3', 'wav')

        Returns:
            Dict containing the API response with audio_base64 and metadata
        """
        payload = {
            "text": text,
            "prompt_audio": audio_base64,
            # "audio_format": audio_format, --- This field is not used by the API ---
            "output_audio_format": "mp3",
            "emotion_mode": "text_description",
            "do_sample": True,
            "top_p": 0.8,
            "top_k": 30,
            "temperature": 0.8,
            "length_penalty": 0.0,
            "num_beams": 3,
            "repetition_penalty": 10.0,
            "max_mel_tokens": 1500,
            "interval_silence": 200,
            "max_text_tokens_per_segment": 200,
        }

        logger.debug(f"Calling local TTS API at {self.api_url}/synthesize")

        response = await self.client.post(
            f"{self.api_url}/synthesize", json=payload, headers={"Content-Type": "application/json"}
        )

        if response.status_code != 200:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("detail", error_detail)
            except Exception:
                pass
            raise ValueError(f"Local TTS API error ({response.status_code}): {error_detail}")

        result = response.json()
        logger.debug(
            f"Local TTS API response: duration={result.get('audio_duration_seconds', 'unknown')}s, "
            f"inference_time={result.get('inference_time_seconds', 'unknown')}s"
        )

        return result

    async def close(self):
        """Clean up the HTTP client."""
        await self.client.aclose()
