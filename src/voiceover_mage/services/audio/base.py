# ABOUTME: Abstract base class for Text-to-Speech provider implementations
# ABOUTME: Defines the common interface that all TTS providers must implement

from abc import ABC, abstractmethod


class TTSProvider(ABC):
    """Abstract interface for a Text-to-Speech provider.

    This base class defines the contract that all TTS provider implementations
    must follow, ensuring consistent behavior across different services like
    ElevenLabs or local TTS solutions.
    """

    @abstractmethod
    async def clone_voice_from_sample(self, name: str, sample_bytes: bytes) -> str:
        """Clone a voice from audio sample bytes and return a new, permanent voice ID.

        Args:
            name: Human-readable name for the cloned voice
            sample_bytes: Raw audio data (WAV, MP3, etc.)

        Returns:
            str: Provider-specific voice ID that can be used for speech generation

        Raises:
            ValueError: If sample_bytes is empty or audio format is not supported
            Exception: Provider-specific errors during voice cloning
        """
        pass

    @abstractmethod
    async def generate_speech(self, voice_id: str, text: str) -> bytes:
        """Generate speech for the given text using the specified voice ID.

        Args:
            voice_id: Provider-specific voice ID returned from clone_voice_from_sample
            text: Text content to convert to speech

        Returns:
            bytes: Raw audio data in MP3 format

        Raises:
            ValueError: If voice_id is invalid or text is empty
            Exception: Provider-specific errors during speech generation
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the human-readable name of this TTS provider.

        Returns:
            str: Provider name (e.g., "Hume.ai", "ElevenLabs")
        """
        pass

    @property
    @abstractmethod
    def supports_voice_cloning(self) -> bool:
        """Return whether this provider supports voice cloning from samples.

        Returns:
            bool: True if voice cloning is supported, False otherwise
        """
        pass
