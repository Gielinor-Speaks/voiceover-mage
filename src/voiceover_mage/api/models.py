# ABOUTME: Pydantic request/response models for FastAPI endpoints
# ABOUTME: Defines API contracts for voice generation operations

from pydantic import BaseModel, Field


class SpeakRequest(BaseModel):
    """Request model for NPC speech generation."""

    text: str = Field(
        ...,
        description="Text to synthesize into speech using the NPC's voice",
        min_length=1,
        max_length=5000,
        examples=["Hello, adventurer! What brings you to my shop today?"],
    )
    animation_id: int | None = Field(
        None,
        description="Optional OSRS animation ID to determine emotion/tone for speech synthesis",
        examples=[588, 589, 590],
    )


class SpeakResponse(BaseModel):
    """Response model for successful speech generation."""

    npc_id: int = Field(..., description="NPC identifier")
    npc_name: str = Field(..., description="NPC name")
    text: str = Field(..., description="Original text that was synthesized")
    audio_url: str | None = Field(None, description="URL to download the audio file (if using file storage)")
    audio_base64: str | None = Field(None, description="Base64-encoded audio data (if using inline response)")
    cached: bool = Field(..., description="Whether this was served from cache")
    provider: str = Field(..., description="TTS provider used for generation")
    generation_metadata: dict = Field(default_factory=dict, description="Additional generation metadata")


class ErrorResponse(BaseModel):
    """Standard error response model.

    Error Types:
    - NPC_NOT_FOUND (404): NPC does not exist in database
    - VOICE_NOT_CONFIGURED (503): NPC exists but has no voice
    - TTS_SERVICE_UNAVAILABLE (503): TTS service is down or unreachable
    - TTS_GENERATION_FAILED (500): TTS generation failed (retryable)
    - PIPELINE_EXECUTION_FAILED (500): Voice pipeline failed (may need intervention)
    - INTERNAL_SERVER_ERROR (500): Unexpected error occurred
    """

    error: str = Field(
        ...,
        description="Error type or category",
        examples=[
            "NPC_NOT_FOUND",
            "VOICE_NOT_CONFIGURED",
            "TTS_GENERATION_FAILED",
            "PIPELINE_EXECUTION_FAILED",
        ],
    )
    message: str = Field(
        ..., description="Human-readable error message", examples=["NPC 123 does not exist in the database"]
    )
    details: dict | None = Field(None, description="Additional error context (npc_id, reason, retryable flag, etc.)")


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status", examples=["healthy"])
    version: str = Field(..., description="API version")
    database: str = Field(..., description="Database connection status")
