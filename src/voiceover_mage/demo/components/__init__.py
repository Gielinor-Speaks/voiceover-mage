# ABOUTME: Demo UI components package

"""UI components for the demo interface."""

from voiceover_mage.demo.components.demo_tab import create_demo_tab
from voiceover_mage.demo.components.event_handlers import handle_load_npcs, handle_npc_selection
from voiceover_mage.demo.components.interactive_tab import create_interactive_tab

__all__ = ["create_demo_tab", "create_interactive_tab", "handle_load_npcs", "handle_npc_selection"]
