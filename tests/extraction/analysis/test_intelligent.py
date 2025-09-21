# ABOUTME: Tests for the normalized NPCIntelligentExtractor pipeline
# ABOUTME: Validates DSPy configuration and interaction with pipeline state inputs

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from voiceover_mage.extraction.analysis.image import NPCVisualCharacteristics
from voiceover_mage.extraction.analysis.intelligent import (
    NPCIntelligentExtractor,
    _configure_dspy_global_state,
)
from voiceover_mage.extraction.analysis.synthesizer import NPCDetails
from voiceover_mage.extraction.analysis.text import NPCTextCharacteristics
from voiceover_mage.persistence.manager import NPCPipelineState
from voiceover_mage.persistence.models import NPC, WikiSnapshot


def _make_pipeline_state(markdown: str, npc_id: int = 1, name: str = "Test NPC") -> NPCPipelineState:
    npc = NPC(id=npc_id, name=name, variant=None, wiki_url=f"https://wiki.test/{npc_id}")
    snapshot = WikiSnapshot(
        npc_id=npc_id,
        raw_markdown=markdown,
        chathead_image_url="https://cdn.test/chat.png",
        image_url="https://cdn.test/full.png",
        raw_data_json=None,
        source_checksum="checksum",
        fetched_at=datetime.now(UTC),
        extraction_success=True,
        error_message=None,
    )
    return NPCPipelineState(npc=npc, wiki_snapshot=snapshot)


class TestDSPyConfiguration:
    """Validate DSPy bootstrap helper."""

    @patch("voiceover_mage.extraction.analysis.intelligent.get_config")
    @patch("voiceover_mage.extraction.analysis.intelligent.dspy.configure")
    @patch("voiceover_mage.extraction.analysis.intelligent.dspy.LM")
    def test_configure_with_api_key(self, mock_lm, mock_configure, mock_get_config):
        config = SimpleNamespace(gemini_api_key="abc")
        mock_get_config.return_value = config
        lm_instance = Mock()
        mock_lm.return_value = lm_instance

        assert _configure_dspy_global_state() is True
        mock_lm.assert_called_once_with("gemini/gemini-2.5-flash", api_key="abc")
        mock_configure.assert_called_once_with(lm=lm_instance)

    @patch("voiceover_mage.extraction.analysis.intelligent.get_config")
    @patch("voiceover_mage.extraction.analysis.intelligent.dspy.configure")
    def test_configure_without_api_key(self, mock_configure, mock_get_config):
        config = SimpleNamespace(gemini_api_key=None)
        mock_get_config.return_value = config

        assert _configure_dspy_global_state() is False
        mock_configure.assert_not_called()


class TestNPCIntelligentExtractor:
    """Ensure the extractor cooperates with pipeline state inputs."""

    def setup_method(self):
        with patch("voiceover_mage.extraction.analysis.intelligent._configure_dspy_global_state", return_value=True):
            self.extractor = NPCIntelligentExtractor()

    def test_forward_invokes_submodules(self):
        state = _make_pipeline_state("# Test NPC\nHelpful guide.")

        mock_text = Mock()
        mock_text.aforward = AsyncMock(
            return_value=NPCTextCharacteristics(
                personality_traits="helpful",
                occupation="guide",
                social_role="assistant",
                dialogue_patterns="friendly",
                emotional_range="warm",
                background_lore="Lumbridge",
                confidence_score=0.8,
                reasoning="markdown",
            )
        )

        mock_visual = Mock()
        mock_visual.aforward = AsyncMock(
            return_value=NPCVisualCharacteristics(
                chathead_image_url=state.chathead_image_url,
                image_url=state.image_url,
                age_category="adult",
                build_type="average",
                attire_style="simple",
                distinctive_features="bald",
                color_palette="blue",
                visual_archetype="citizen",
                confidence_score=0.7,
                reasoning="images",
            )
        )

        mock_synth = Mock()
        mock_synth.aforward = AsyncMock(
            return_value=NPCDetails(
                npc_name=state.npc_name,
                personality_traits="Helpful castle servant",
                occupation="guide",
                social_role="assistant",
                dialogue_patterns="friendly",
                emotional_range="warm",
                background_lore="Lumbridge",
                age_category="adult",
                build_type="average",
                attire_style="simple",
                distinctive_features="bald",
                color_palette="blue",
                visual_archetype="citizen",
                chathead_image_url=state.chathead_image_url,
                image_url=state.image_url,
                overall_confidence=0.85,
                text_confidence=0.8,
                visual_confidence=0.7,
                synthesis_notes="coherent",
            )
        )

        self.extractor.text_extractor = mock_text
        self.extractor.image_extractor = mock_visual
        self.extractor.synthesizer = mock_synth

        result = self.extractor.forward(state)

        assert isinstance(result, NPCDetails)
        assert result.personality_traits.startswith("Helpful")
        mock_text.aforward.assert_awaited()
        mock_visual.aforward.assert_awaited()
        mock_synth.aforward.assert_awaited()

    @pytest.mark.asyncio
    async def test_extract_async_delegates(self):
        state = _make_pipeline_state("# Async NPC\nMinimal data.")
        expected = NPCDetails(
            npc_name=state.npc_name,
            personality_traits="minimal",
            occupation="guard",
            social_role="keeper",
            dialogue_patterns="short",
            emotional_range="stern",
            background_lore="",
            age_category="adult",
            build_type="average",
            attire_style="armor",
            distinctive_features="helmet",
            color_palette="steel",
            visual_archetype="guard",
            chathead_image_url=state.chathead_image_url,
            image_url=state.image_url,
            overall_confidence=0.5,
            text_confidence=0.4,
            visual_confidence=0.6,
            synthesis_notes="async",
        )

        async def mock_forward(_: NPCPipelineState) -> NPCDetails:
            return expected

        with patch.object(self.extractor, "aforward", side_effect=mock_forward) as mock_aforward:
            result = await self.extractor.extract_async(state)

        mock_aforward.assert_awaited_once()
        assert result is expected

    def test_forward_propagates_errors(self):
        state = _make_pipeline_state("# Error NPC")

        failing_text = Mock()
        failing_text.aforward = AsyncMock(side_effect=RuntimeError("text failure"))
        self.extractor.text_extractor = failing_text

        safe_image = Mock()
        safe_image.aforward = AsyncMock(return_value=NPCVisualCharacteristics())
        self.extractor.image_extractor = safe_image

        safe_synth = Mock()
        safe_synth.aforward = AsyncMock()
        self.extractor.synthesizer = safe_synth

        with pytest.raises(RuntimeError, match="text failure"):
            self.extractor.forward(state)
