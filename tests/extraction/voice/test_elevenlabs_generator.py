from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from voiceover_mage.core.models import NPCProfile
from voiceover_mage.extraction.voice.elevenlabs import ElevenLabsVoicePromptGenerator


@pytest.mark.asyncio
async def test_elevenlabs_prompt_generation(monkeypatch):
    # Arrange
    mock_acall = AsyncMock(
        return_value=SimpleNamespace(
            voice_description="A test voice prompt.", sample_text="Test sample text for the voice."
        )
    )
    monkeypatch.setattr("dspy.ChainOfThought.acall", mock_acall)
    generator = ElevenLabsVoicePromptGenerator()
    npc_profile = NPCProfile(
        id=1,
        npc_name="Test NPC",
        personality="Brave",
        voice_description="Deep",
        age_range="Adult",
        emotional_profile="Calm",
        character_archetype="Warrior",
        speaking_style="Formal",
        confidence_score=0.9,
    )

    # Act
    result = await generator.aforward(npc_profile)

    # Assert
    assert result == {"description": "A test voice prompt.", "sample_text": "Test sample text for the voice."}
    mock_acall.assert_called_once()
