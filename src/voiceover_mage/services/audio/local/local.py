# ABOUTME: Local TTS provider implementation for zero-shot voice synthesis
# ABOUTME: Handles voice synthesis using our custom IndexTTSv2 API with reference audio samples

import base64
import json
from typing import Any

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from voiceover_mage.services.audio.base import TTSProvider

from .animation_id_to_emotion import AnimationEmotionMapper


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
        self.emotion_mapper = AnimationEmotionMapper()

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
        self,
        text: str,
        reference_audio_bytes: bytes,
        audio_format: str = ".wav",
        animation_id: int | None = None,
        # Optional generation parameters (will override defaults)
        do_sample: bool | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
        temperature: float | None = None,
        length_penalty: float | None = None,
        num_beams: int | None = None,
        repetition_penalty: float | None = None,
        max_mel_tokens: int | None = None,
        interval_silence: int | None = None,
        max_text_tokens_per_segment: int | None = None,
        # Optional emotion control (will override animation_id-based emotion)
        emotion_mode: str | None = None,
        emotion_vector: list[float] | None = None,
        emotion_weight: float | None = None,
        emotion_prompt_text: str | None = None,
    ) -> bytes:
        """Generate speech using a reference voice sample via zero-shot synthesis.

        Args:
            text: Text to convert to speech
            reference_audio_bytes: Raw audio data to use as voice reference
            audio_format: Format of the reference audio (e.g., '.wav', '.mp3')
            animation_id: Optional OSRS animation ID for emotion/tone control

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

            # Build kwargs for optional parameters
            kwargs = {}
            if do_sample is not None:
                kwargs["do_sample"] = do_sample
            if top_p is not None:
                kwargs["top_p"] = top_p
            if top_k is not None:
                kwargs["top_k"] = top_k
            if temperature is not None:
                kwargs["temperature"] = temperature
            if length_penalty is not None:
                kwargs["length_penalty"] = length_penalty
            if num_beams is not None:
                kwargs["num_beams"] = num_beams
            if repetition_penalty is not None:
                kwargs["repetition_penalty"] = repetition_penalty
            if max_mel_tokens is not None:
                kwargs["max_mel_tokens"] = max_mel_tokens
            if interval_silence is not None:
                kwargs["interval_silence"] = interval_silence
            if max_text_tokens_per_segment is not None:
                kwargs["max_text_tokens_per_segment"] = max_text_tokens_per_segment
            if emotion_mode is not None:
                kwargs["emotion_mode"] = emotion_mode
            if emotion_vector is not None:
                kwargs["emotion_vector"] = emotion_vector
            if emotion_weight is not None:
                kwargs["emotion_weight"] = emotion_weight
            if emotion_prompt_text is not None:
                kwargs["emotion_prompt_text"] = emotion_prompt_text

            # Call the local TTS API
            response = await self._synthesize_with_voice_sample(
                text=text,
                audio_base64=audio_base64,
                audio_format=audio_format,
                animation_id=animation_id,
                **kwargs,
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
    

    def _get_emotion_settings(self, animation_id: int | None) -> dict[str, str | list[float] | float]:
        """Get emotion settings based on animation ID.

        Args:
            animation_id: Optional animation ID for emotion context

        Returns:
            Dict with emotion settings for the API request
        """

        # INTENTIONAL EARLY RETURN: Force text_description mode to avoid emotion vector corruption
        #
        # The IndexTTS API applies bias factors and sum constraints to emotion vectors that
        # distort our carefully designed emotion ratios:
        #
        # 1. Bias application: Each emotion dimension is multiplied by a bias factor to
        #    "de-emphasize emotions that cause strange results":
        #    - happy: ×0.9375, angry: ×0.875, sad: ×1.0, afraid: ×1.0
        #    - disgusted: ×0.9375, melancholic: ×0.9375, surprised: ×0.6875, calm: ×0.5625
        #
        # 2. Sum constraint: After bias, the vector sum must be ≤ 0.8. If exceeded, the entire
        #    vector is scaled down proportionally.
        #
        # Problem: Our emotion vectors (e.g., LAUGHING = 70% happy + 30% surprised) become
        # distorted after bias application (becomes 76% happy + 24% surprised), destroying
        # the intended emotional expression and causing inconsistent pacing.
        #
        # Solution: Use text_description mode, which:
        # - Infers emotion from the dialogue text using the Qwen emotion model
        # - Bypasses bias factors and normalization constraints
        # - Produces consistent, natural pacing (verified to fix pacing issues)
        # - Works well for short NPC dialogue phrases
        #
        # Future improvement: Consider mapping animation_id → emotion text descriptions
        # for explicit control without vector normalization issues.
        #
        # See: indextts/infer_v2.py:323 (normalize_emo_vec) and api.py:179 (normalize_emotion_vector)
        # fallback_settings = {
        return {
            "emotion_mode": "text_description",
            # Should be 0.6 or less for best results with text_description mode
            "emotion_weight": 0.6,
        }

        # if animation_id is None:
        #     logger.debug("No animation ID provided, using fallback emotion settings")
        #     return fallback_settings

        # # Map animation ID to emotion vector
        # result = self.emotion_mapper.map_animation_to_emotion(animation_id)

        # if result is None:
        #     logger.debug(
        #         f"No emotion vector found for animation ID {animation_id}, "
        #         f"falling back to text-based inference"
        #     )
        #     return fallback_settings

        # emotion_vector, source = result
        # logger.debug(
        #     f"Using emotion vector for animation ID {animation_id} "
        #     f"(source: {source}): {emotion_vector}"
        # )
        # return {
        #     "emotion_mode": "emotion_vector",
        #     "emotion_vector": emotion_vector,
        #     "emotion_weight": 0.6,
        # }
    

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _synthesize_with_voice_sample(
        self,
        text: str,
        audio_base64: str,
        audio_format: str,
        animation_id: int | None = None,
        **generation_params: Any,
    ) -> dict[str, Any]:
        """Call the local TTS API to synthesize speech with voice reference.

        Uses our custom IndexTTSv2 API format.

        Args:
            text: Text to synthesize
            audio_base64: Base64-encoded reference audio
            audio_format: Audio format (e.g., 'mp3', 'wav')
            animation_id: Optional animation ID for emotion context 

        Returns:
            Dict containing the API response with audio_base64 and metadata
        """
        # Start with default payload
        payload = {
            "text": text,
            "prompt_audio": audio_base64,
            # "audio_format": audio_format, --- This field is not used by the API ---
            "output_audio_format": "mp3",
            "do_sample": generation_params.get("do_sample", True),
            "top_p": generation_params.get("top_p", 0.8),
            "top_k": generation_params.get("top_k", 30),
            "temperature": generation_params.get("temperature", 0.8),
            "length_penalty": generation_params.get("length_penalty", 0.0),
            "num_beams": generation_params.get("num_beams", 3),
            "repetition_penalty": generation_params.get("repetition_penalty", 10.0),
            "max_mel_tokens": generation_params.get("max_mel_tokens", 1500),
            "interval_silence": generation_params.get("interval_silence", 200),
            "max_text_tokens_per_segment": generation_params.get("max_text_tokens_per_segment", 200),
        }

        # Add emotion settings - either from generation_params or animation_id
        if "emotion_mode" in generation_params:
            # Use explicit emotion control from parameters
            payload["emotion_mode"] = generation_params["emotion_mode"]
            if "emotion_weight" in generation_params:
                payload["emotion_weight"] = generation_params["emotion_weight"]
            if "emotion_vector" in generation_params:
                payload["emotion_vector"] = generation_params["emotion_vector"]
            if "emotion_prompt_text" in generation_params:
                # For text description mode: emotion prompt text
                # Map to the IndexTTS API field name: emotion_text
                # If None, API will use the main text; if empty string, same behavior
                payload["emotion_text"] = generation_params["emotion_prompt_text"]
        else:
            # Use default emotion settings based on animation_id
            payload.update(self._get_emotion_settings(animation_id))

        logger.debug(f"Calling local TTS API at {self.api_url}/synthesize...")

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
