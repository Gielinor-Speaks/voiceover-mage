# ABOUTME: Business logic services for API endpoints
# ABOUTME: Handles voice generation workflow with dialogue caching and pipeline fallbacks

import random
from dataclasses import dataclass

import httpx

from voiceover_mage.api.exceptions import (
    AudioServiceError,
    NPCNotFoundError,
    PipelineExecutionError,
    TTSGenerationError,
    VoiceNotConfiguredError,
)
from voiceover_mage.config import get_config
from voiceover_mage.core.unified_pipeline import UnifiedPipelineService
from voiceover_mage.persistence.manager import DatabaseManager
from voiceover_mage.services.audio.local import LocalTTSAdapter
from voiceover_mage.utils.logging import get_logger


@dataclass
class VoiceGenerationResult:
    """Result of voice generation operation."""

    npc_id: int
    npc_name: str
    text: str
    audio_bytes: bytes
    cached: bool
    provider: str
    generation_metadata: dict


class VoiceGenerationService:
    """Service for NPC voice generation with intelligent caching and fallbacks."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.logger = get_logger(__name__)
        self.config = get_config()

    async def generate_speech(
        self, npc_id: int, text: str, animation_id: int | None = None
    ) -> VoiceGenerationResult:
        """Generate speech for an NPC with the following priority:

        1. Check cached dialogue (hash-based lookup)
        2. Use cloned voice if available
        3. Use selected preview for generation
        4. Pick random preview and set as selected
        5. Run full pipeline, pick random preview, generate

        Args:
            npc_id: NPC identifier
            text: Text to synthesize
            animation_id: Optional OSRS animation ID for emotion/tone control

        Returns:
            VoiceGenerationResult with audio bytes and metadata

        Raises:
            NPCNotFoundError: NPC does not exist in database
            VoiceNotConfiguredError: NPC exists but has no voice
            TTSGenerationError: TTS generation failed
            PipelineExecutionError: Pipeline execution failed
            AudioServiceError: Audio service unavailable
        """
        # Step 1: Check cache
        cached_dialogue = await self.db.get_cached_dialogue(npc_id, text)
        if cached_dialogue:
            npc = await self.db.get_npc(npc_id)
            if not npc:
                # Orphaned dialogue entry - log warning and fail
                self.logger.warning("Found cached dialogue for non-existent NPC", npc_id=npc_id)
                raise NPCNotFoundError(npc_id)

            self.logger.info("Serving cached dialogue", npc_id=npc_id, dialogue_id=cached_dialogue.id)
            return VoiceGenerationResult(
                npc_id=npc_id,
                npc_name=npc.name,
                text=text,
                audio_bytes=cached_dialogue.audio_bytes,
                cached=True,
                provider=cached_dialogue.generation_metadata.get("provider", "unknown"),
                generation_metadata=cached_dialogue.generation_metadata,
            )

        # Step 2: Get NPC and check for selected preview
        npc = await self.db.get_npc(npc_id)
        if not npc:
            self.logger.error("NPC lookup failed", npc_id=npc_id)
            raise NPCNotFoundError(npc_id)

        selected_preview = None
        if npc.selected_preview_id:
            from voiceover_mage.persistence.models import VoicePreview

            async with self.db.async_session() as session:
                selected_preview = await session.get(VoicePreview, npc.selected_preview_id)

        # Step 3: No selected preview? Check for any previews
        if not selected_preview:
            previews = await self.db.list_voice_previews(npc_id)
            if previews:
                # Pick random preview (later: use LLM)
                selected_preview = random.choice(previews)
                # Set as selected
                await self.db.set_selected_voice_preview(npc_id, selected_preview.id)  # type: ignore[arg-type]
                self.logger.info(
                    "Selected random preview",
                    npc_id=npc_id,
                    preview_id=selected_preview.id,
                )

        # Step 4: Still no preview? Run full pipeline
        if not selected_preview:
            self.logger.info("No previews found, running full pipeline", npc_id=npc_id)
            try:
                pipeline = UnifiedPipelineService(
                    database=self.db,
                    api_key=self.config.gemini_api_key,
                )
                await pipeline.run_full_pipeline(npc_id)

                # Fetch previews after pipeline
                previews = await self.db.list_voice_previews(npc_id)
                if not previews:
                    self.logger.error("Pipeline completed but no previews generated", npc_id=npc_id)
                    raise VoiceNotConfiguredError(npc_id, npc.name)

                selected_preview = random.choice(previews)
                await self.db.set_selected_voice_preview(npc_id, selected_preview.id)  # type: ignore[arg-type]

            except VoiceNotConfiguredError:
                raise  # Re-raise our own exception
            except Exception as e:
                self.logger.error("Pipeline execution failed", npc_id=npc_id, error=str(e), exc_info=True)
                raise PipelineExecutionError(npc_id, "voice_generation", str(e)) from e

        # Step 5: Generate speech using selected preview
        if not selected_preview.audio_bytes:
            self.logger.error("Selected preview has no audio data", preview_id=selected_preview.id)
            raise VoiceNotConfiguredError(npc_id, npc.name)

        # Step 6: Call TTS service
        try:
            tts_adapter = LocalTTSAdapter(self.config.local_tts_api_url)
            audio_bytes = await tts_adapter.generate_speech_with_reference(
                text=text,
                reference_audio_bytes=selected_preview.audio_bytes,
                audio_format=".mp3",
                animation_id=animation_id,
            )
        except (httpx.ConnectError, httpx.TimeoutException, ConnectionError) as e:
            # Connection/network errors - service is down or unreachable
            self.logger.error("TTS service connection failed", npc_id=npc_id, error=str(e))
            raise AudioServiceError(self.config.local_tts_api_url, str(e)) from e
        except httpx.HTTPError as e:
            # HTTP-level errors (4xx, 5xx from TTS service)
            self.logger.error("TTS service HTTP error", npc_id=npc_id, error=str(e))
            raise AudioServiceError(self.config.local_tts_api_url, f"HTTP error: {e}") from e
        except Exception as e:
            # Other errors (processing, encoding, etc.)
            self.logger.error("TTS generation failed", npc_id=npc_id, error=str(e), exc_info=True)
            raise TTSGenerationError(npc_id, str(e), e) from e

        # Step 7: Save to database
        generation_metadata = {
            "preview_id": selected_preview.id,
            "provider": selected_preview.provider,
            "voice_prompt": selected_preview.voice_prompt,
            "text_length": len(text),
            "audio_size": len(audio_bytes),
            "animation_id": animation_id,
        }

        await self.db.save_generated_dialogue(
            npc_id=npc_id,
            source_text=text,
            audio_bytes=audio_bytes,
            generation_metadata=generation_metadata,
        )

        self.logger.info(
            "Generated new dialogue",
            npc_id=npc_id,
            text_length=len(text),
            audio_size=len(audio_bytes),
        )

        return VoiceGenerationResult(
            npc_id=npc_id,
            npc_name=npc.name,
            text=text,
            audio_bytes=audio_bytes,
            cached=False,
            provider=selected_preview.provider,
            generation_metadata=generation_metadata,
        )
