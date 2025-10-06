# ABOUTME: Custom exception hierarchy for API error handling
# ABOUTME: Provides specific exceptions for different failure modes

"""API Exception Hierarchy

Exceptions map to HTTP status codes and error responses:

- NPCNotFoundError          → 404 (not retryable)
- VoiceNotConfiguredError   → 503 (retryable after pipeline run)
- AudioServiceError         → 503 (retryable - TTS service down)
- TTSGenerationError        → 500 (retryable - generation failed)
- PipelineExecutionError    → 500 (not retryable - pipeline failed)

All exceptions include context for detailed error responses.
See docs/api/error-codes.md for client-facing error code reference.
"""


class VoiceoverMageAPIError(Exception):
    """Base exception for all API-specific errors."""

    pass


class NPCNotFoundError(VoiceoverMageAPIError):
    """Raised when an NPC does not exist in the database."""

    def __init__(self, npc_id: int):
        self.npc_id = npc_id
        super().__init__(f"NPC {npc_id} not found in database")


class VoiceNotConfiguredError(VoiceoverMageAPIError):
    """Raised when an NPC exists but has no voice configured."""

    def __init__(self, npc_id: int, npc_name: str):
        self.npc_id = npc_id
        self.npc_name = npc_name
        super().__init__(f"NPC {npc_id} ({npc_name}) has no voice configured")


class TTSGenerationError(VoiceoverMageAPIError):
    """Raised when TTS generation fails."""

    def __init__(self, npc_id: int, reason: str, original_error: Exception | None = None):
        self.npc_id = npc_id
        self.reason = reason
        self.original_error = original_error
        super().__init__(f"TTS generation failed for NPC {npc_id}: {reason}")


class PipelineExecutionError(VoiceoverMageAPIError):
    """Raised when the voice generation pipeline fails."""

    def __init__(self, npc_id: int, stage: str, reason: str):
        self.npc_id = npc_id
        self.stage = stage
        self.reason = reason
        super().__init__(f"Pipeline failed at {stage} for NPC {npc_id}: {reason}")


class AudioServiceError(VoiceoverMageAPIError):
    """Raised when audio service is unavailable or fails."""

    def __init__(self, service_url: str, reason: str):
        self.service_url = service_url
        self.reason = reason
        super().__init__(f"Audio service at {service_url} failed: {reason}")
