# ABOUTME: Recording service for voice generation in the Recording Studio tab.
# Handles TTS generation via LocalTTSAdapter, animation-to-emotion mapping,
# and saving generated samples to the database.

from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import select

from voiceover_mage.config import Config
from voiceover_mage.persistence.manager import DatabaseManager
from voiceover_mage.persistence.models import GeneratedDialogue, NPC, VoicePreview
from voiceover_mage.services.audio.local import LocalTTSAdapter
from voiceover_mage.services.audio.local.animation_id_to_emotion import (
    AnimationEmotionMapper,
    EmotionVector,
)


class RecordingService:
    """Service for Recording Studio operations."""

    def __init__(self, db: DatabaseManager, config: Config):
        self.db = db
        self.config = config
        self.tts_adapter = LocalTTSAdapter(config.local_tts_api_url)
        self.emotion_mapper = AnimationEmotionMapper()

    async def get_npcs_with_voices(self) -> list[dict[str, Any]]:
        """Get all NPCs that have a selected voice."""
        async with self.db.async_session() as session:
            stmt = (
                select(NPC)
                .where(NPC.selected_preview_id != None)  # noqa: E711
                .order_by(NPC.name)
            )
            result = await session.exec(stmt)
            npcs = result.scalars().all()

            return [
                {"id": npc.id, "name": npc.name, "wiki_url": npc.wiki_url}
                for npc in npcs
            ]

    def get_animation_choices(self) -> list[tuple[str, int]]:
        """Get list of animation choices for dropdown."""
        animations = self.emotion_mapper.get_supported_animations()
        # Return list of (label, value) tuples
        return [
            (f"{anim_id}: {name}", anim_id) for anim_id, name in animations.items()
        ]

    def get_emotion_for_animation(self, animation_id: int) -> list[float] | None:
        """Get emotion vector for a specific animation ID as a list of 8 floats."""
        result = self.emotion_mapper.map_animation_to_emotion(animation_id)
        if result:
            emotion_vec, _source = result
            return emotion_vec  # Already a list[float]
        return None

    async def generate_speech(
        self,
        npc_id: int,
        text: str,
        animation_id: int | None = None,
        emotion_mode: str = "text_description",
        emotion_vector: list[float] | None = None,
        emotion_weight: float = 0.6,
        emotion_prompt_text: str | None = None,
        # Generation parameters
        do_sample: bool = True,
        top_p: float = 0.8,
        top_k: int = 30,
        temperature: float = 0.8,
        length_penalty: float = 0.0,
        num_beams: int = 3,
        repetition_penalty: float = 10.0,
        max_mel_tokens: int = 1500,
        interval_silence: int = 200,
        max_text_tokens_per_segment: int = 200,
    ) -> tuple[bytes, dict[str, Any]]:
        """
        Generate speech for given text using NPC's selected voice.

        Args:
            npc_id: NPC database ID
            text: Text to synthesize
            animation_id: Optional animation ID for emotion control
            emotion_mode: "text_description" or "emotion_vector" or "none"
            emotion_vector: Manual 8D emotion vector [happy, angry, sad, afraid, disgusted, melancholic, surprised, calm]
            emotion_weight: Weight for emotion influence (0.0-1.0)
            emotion_prompt_text: Text description for emotion (text_description mode). If None, uses main text.
            ... generation parameters ...

        Returns:
            Tuple of (audio_bytes, metadata_dict)
        """
        async with self.db.async_session() as session:
            # Get NPC
            npc_stmt = select(NPC).where(NPC.id == npc_id)
            npc_result = await session.exec(npc_stmt)
            npc = npc_result.scalar_one_or_none()

            if not npc:
                raise ValueError(f"NPC {npc_id} not found")

            if not npc.selected_preview_id:
                raise ValueError(f"NPC {npc.name} has no selected voice")

            # Get selected voice preview
            preview_stmt = select(VoicePreview).where(
                VoicePreview.id == npc.selected_preview_id
            )
            preview_result = await session.exec(preview_stmt)
            preview = preview_result.scalar_one_or_none()

            if not preview:
                raise ValueError(f"Voice preview {npc.selected_preview_id} not found")

            logger.info(
                f"Generating speech for NPC '{npc.name}' with voice preview {preview.id}"
            )

            # Determine emotion settings
            emotion_settings: dict[str, Any] = {}

            if emotion_mode == "emotion_vector":
                # Use provided vector or animation vector
                if emotion_vector:
                    emotion_settings = {
                        "emotion_mode": "emotion_vector",
                        "emotion_weight": emotion_weight,
                        "emotion_vector": emotion_vector,
                    }
                elif animation_id:
                    # Get emotion from animation
                    emotion_vec = self.get_emotion_for_animation(animation_id)
                    if emotion_vec:
                        emotion_settings = {
                            "emotion_mode": "emotion_vector",
                            "emotion_weight": emotion_weight,
                            "emotion_vector": emotion_vec,  # Already a list of 8 floats
                        }
            elif emotion_mode == "text_description":
                emotion_settings = {
                    "emotion_mode": "text_description",
                    "emotion_weight": emotion_weight,
                }
                # Add emotion prompt text if provided (None means use main text in API)
                if emotion_prompt_text is not None:
                    emotion_settings["emotion_prompt_text"] = emotion_prompt_text
            # else: emotion_mode == "none" → no emotion settings

            # Generate speech
            generation_params = {
                "do_sample": do_sample,
                "top_p": top_p,
                "top_k": top_k if top_k > 0 else None,
                "temperature": temperature,
                "length_penalty": length_penalty,
                "num_beams": num_beams,
                "repetition_penalty": repetition_penalty,
                "max_mel_tokens": max_mel_tokens,
                "interval_silence": interval_silence,
                "max_text_tokens_per_segment": max_text_tokens_per_segment,
            }

            audio_bytes = await self.tts_adapter.generate_speech_with_reference(
                text=text,
                reference_audio_bytes=preview.audio_bytes,
                audio_format="wav",
                animation_id=animation_id,
                **emotion_settings,
                **generation_params,
            )

            # Prepare metadata
            metadata = {
                "preview_id": preview.id,
                "provider": preview.provider,
                "voice_prompt": preview.voice_prompt,
                "text_length": len(text),
                "audio_size": len(audio_bytes),
                "animation_id": animation_id,
                "emotion_mode": emotion_mode,
                "emotion_weight": emotion_weight,
                "generation_params": generation_params,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            if emotion_vector:
                metadata["emotion_vector"] = emotion_vector

            logger.info(
                f"Generated {len(audio_bytes)} bytes of audio for text: {text[:50]}..."
            )

            return audio_bytes, metadata

    async def save_to_database(
        self, npc_id: int, text: str, audio_bytes: bytes, metadata: dict[str, Any]
    ) -> int:
        """
        Save generated dialogue to database.

        Returns:
            Database ID of saved dialogue
        """
        dialogue = await self.db.save_generated_dialogue(
            npc_id=npc_id,
            source_text=text,
            audio_bytes=audio_bytes,
            generation_metadata=metadata,
        )

        logger.info(f"Saved generated dialogue with ID {dialogue.id} to database")
        return dialogue.id  # type: ignore[return-value]

    async def get_sample_history(
        self, npc_id: int, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get recent generated samples for an NPC."""
        from sqlalchemy import desc

        async with self.db.async_session() as session:
            stmt = (
                select(GeneratedDialogue)
                .where(GeneratedDialogue.npc_id == npc_id)
                .order_by(desc(GeneratedDialogue.created_at))  # type: ignore[arg-type]
                .limit(limit)
            )
            result = await session.exec(stmt)
            samples = result.scalars().all()

            return [
                {
                    "id": sample.id,
                    "text": sample.source_text,
                    "created_at": sample.created_at.isoformat(),
                    "metadata": sample.generation_metadata,
                    "audio_size": len(sample.audio_bytes),
                }
                for sample in samples
            ]

    async def load_sample_audio(self, sample_id: int) -> bytes | None:
        """Load audio bytes for a saved sample."""
        async with self.db.async_session() as session:
            stmt = select(GeneratedDialogue).where(GeneratedDialogue.id == sample_id)
            result = await session.exec(stmt)
            sample = result.scalar_one_or_none()

            if sample:
                return sample.audio_bytes
            return None
