# ABOUTME: Voice generation API endpoints
# ABOUTME: Handles NPC speech synthesis with caching and fallback logic

import base64

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from voiceover_mage.api.dependencies import get_db_manager
from voiceover_mage.api.exceptions import (
    AudioServiceError,
    NPCNotFoundError,
    PipelineExecutionError,
    TTSGenerationError,
    VoiceNotConfiguredError,
)
from voiceover_mage.api.models import ErrorResponse, SpeakRequest, SpeakResponse
from voiceover_mage.api.services import VoiceGenerationService
from voiceover_mage.persistence.manager import DatabaseManager
from voiceover_mage.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/npc/{npc_id}/speak",
    response_model=SpeakResponse,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "NPC not found in database",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "error": "NPC_NOT_FOUND",
                            "message": "NPC 99999 does not exist in the database",
                            "npc_id": 99999,
                        }
                    }
                }
            },
        },
        503: {
            "model": ErrorResponse,
            "description": "Voice not configured or TTS service unavailable (retryable)",
            "content": {
                "application/json": {
                    "examples": {
                        "voice_not_configured": {
                            "summary": "Voice not configured",
                            "value": {
                                "detail": {
                                    "error": "VOICE_NOT_CONFIGURED",
                                    "message": "NPC 'Guard' exists but has no voice configured",
                                    "npc_id": 3105,
                                    "npc_name": "Guard",
                                    "suggestion": "Voice generation pipeline failed or was not run for this NPC",
                                }
                            },
                        },
                        "tts_service_unavailable": {
                            "summary": "TTS service down",
                            "value": {
                                "detail": {
                                    "error": "TTS_SERVICE_UNAVAILABLE",
                                    "message": "Text-to-speech service is unavailable",
                                    "service_url": "http://localhost:8001",
                                    "reason": "Connection refused",
                                    "retryable": True,
                                }
                            },
                        },
                    }
                }
            },
        },
        500: {
            "model": ErrorResponse,
            "description": "TTS generation or pipeline execution failed",
            "content": {
                "application/json": {
                    "examples": {
                        "tts_generation_failed": {
                            "summary": "TTS generation failed (retryable)",
                            "value": {
                                "detail": {
                                    "error": "TTS_GENERATION_FAILED",
                                    "message": "Text-to-speech generation failed",
                                    "npc_id": 3105,
                                    "reason": "Audio encoding failed",
                                    "retryable": True,
                                }
                            },
                        },
                        "pipeline_failed": {
                            "summary": "Pipeline execution failed",
                            "value": {
                                "detail": {
                                    "error": "PIPELINE_EXECUTION_FAILED",
                                    "message": "Voice generation pipeline failed at stage: voice_generation",
                                    "npc_id": 3105,
                                    "stage": "voice_generation",
                                    "reason": "API quota exceeded",
                                    "retryable": False,
                                }
                            },
                        },
                    }
                }
            },
        },
    },
    summary="Generate NPC speech",
    description="""Synthesize text into speech using an NPC's voice.

**Voice Selection Priority:**
1. Return cached dialogue if text matches (case-insensitive)
2. Use cloned voice if available
3. Use selected voice preview
4. Pick random preview and set as selected
5. Run full pipeline if no previews exist

**Error Handling:**
- Check `retryable` flag in error responses
- 404: NPC doesn't exist - verify NPC ID
- 503: Voice not configured - run CLI pipeline
- 503: TTS service down - retry with backoff
- 500: Generation failed - check `retryable` flag

See [error codes documentation](https://github.com/your-repo/docs/api/error-codes.md) for details.
""",
)
async def speak(
    npc_id: int,
    request: SpeakRequest,
    db_manager: DatabaseManager = Depends(get_db_manager),
    return_audio: bool = False,
) -> SpeakResponse | Response:
    """Generate speech for an NPC.

    The service follows this priority:
    1. Return cached dialogue if text matches exactly
    2. Use cloned voice if available
    3. Use selected voice preview
    4. Pick random preview and set as selected
    5. Run full pipeline if no previews exist

    Args:
        npc_id: NPC identifier
        request: Speech generation request with text
        db_manager: Database manager dependency
        return_audio: If True, return raw audio bytes instead of JSON

    Returns:
        SpeakResponse with audio metadata or raw audio Response
    """
    try:
        service = VoiceGenerationService(db_manager)
        result = await service.generate_speech(npc_id, request.text, animation_id=request.animation_id)

        logger.info(
            "Speech generation complete",
            npc_id=npc_id,
            cached=result.cached,
            audio_size=len(result.audio_bytes),
        )

        # Return raw audio if requested
        if return_audio:
            return Response(
                content=result.audio_bytes,
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f'attachment; filename="{result.npc_name}_{npc_id}.mp3"',
                },
            )

        # Return JSON response with base64-encoded audio
        return SpeakResponse(
            npc_id=result.npc_id,
            npc_name=result.npc_name,
            text=result.text,
            audio_url=None,
            audio_base64=base64.b64encode(result.audio_bytes).decode("utf-8"),
            cached=result.cached,
            provider=result.provider,
            generation_metadata=result.generation_metadata,
        )

    except NPCNotFoundError as e:
        logger.error("NPC not found", npc_id=npc_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NPC_NOT_FOUND",
                "message": f"NPC {npc_id} does not exist in the database",
                "npc_id": npc_id,
            },
        ) from e

    except VoiceNotConfiguredError as e:
        logger.warning("NPC has no voice configured", npc_id=npc_id, npc_name=e.npc_name)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "VOICE_NOT_CONFIGURED",
                "message": f"NPC '{e.npc_name}' exists but has no voice configured",
                "npc_id": npc_id,
                "npc_name": e.npc_name,
                "suggestion": "Voice generation pipeline failed or was not run for this NPC",
            },
        ) from e

    except AudioServiceError as e:
        logger.error("TTS service unavailable", npc_id=npc_id, service_url=e.service_url, reason=e.reason)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "TTS_SERVICE_UNAVAILABLE",
                "message": "Text-to-speech service is unavailable",
                "service_url": e.service_url,
                "reason": e.reason,
                "retryable": True,
            },
        ) from e

    except TTSGenerationError as e:
        logger.error("TTS generation failed", npc_id=npc_id, reason=e.reason, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "TTS_GENERATION_FAILED",
                "message": "Text-to-speech generation failed",
                "npc_id": npc_id,
                "reason": e.reason,
                "retryable": True,
            },
        ) from e

    except PipelineExecutionError as e:
        logger.error("Pipeline failed", npc_id=npc_id, stage=e.stage, reason=e.reason)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PIPELINE_EXECUTION_FAILED",
                "message": f"Voice generation pipeline failed at stage: {e.stage}",
                "npc_id": npc_id,
                "stage": e.stage,
                "reason": e.reason,
                "retryable": False,
            },
        ) from e

    except Exception as e:
        logger.error("Unexpected error during speech generation", npc_id=npc_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during speech generation",
                "npc_id": npc_id,
            },
        ) from e


@router.get(
    "/npc/{npc_id}/speak/audio",
    response_class=Response,
    responses={
        404: {"model": ErrorResponse, "description": "NPC not found"},
        500: {"model": ErrorResponse, "description": "Generation failed"},
    },
    summary="Generate NPC speech (audio response)",
    description="Same as POST /speak but returns raw audio bytes instead of JSON",
)
async def speak_audio(
    npc_id: int,
    text: str,
    animation_id: int | None = None,
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> Response:
    """Generate speech and return raw audio.

    Args:
        npc_id: NPC identifier
        text: Text to synthesize
        animation_id: Optional OSRS animation ID for emotion/tone control
        db_manager: Database manager dependency

    Returns:
        Raw MP3 audio response
    """
    request = SpeakRequest(text=text, animation_id=animation_id)
    return await speak(npc_id, request, db_manager, return_audio=True)  # type: ignore[return-value]
