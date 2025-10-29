# ABOUTME: Demo UI components package

"""UI components for the demo interface."""

from voiceover_mage.demo.components.demo_tab import create_demo_tab
from voiceover_mage.demo.components.event_handlers import handle_load_npcs, handle_npc_selection
from voiceover_mage.demo.components.interactive_tab import create_interactive_tab
from voiceover_mage.demo.components.pipeline_tab import create_pipeline_tab
from voiceover_mage.demo.components.pipeline_handlers import (
    handle_batch_process,
    handle_emotion_mode_change,
    handle_generate_dialogue,
    handle_load_npcs_for_voice_management,
    handle_regenerate_voices,
    handle_run_pipeline,
    handle_select_voice,
    handle_voice_npc_selection,
)

__all__ = [
    "create_demo_tab",
    "create_interactive_tab",
    "create_pipeline_tab",
    "handle_load_npcs",
    "handle_npc_selection",
    "handle_run_pipeline",
    "handle_load_npcs_for_voice_management",
    "handle_voice_npc_selection",
    "handle_select_voice",
    "handle_regenerate_voices",
    "handle_generate_dialogue",
    "handle_emotion_mode_change",
    "handle_batch_process",
]
