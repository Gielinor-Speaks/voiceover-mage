# ABOUTME: Demo services package - data fetching logic

"""Services for fetching and managing NPC data."""

from voiceover_mage.demo.services.npc_data_service import (
    find_npc_id_by_display_name,
    get_available_npcs,
    get_npc_display_data,
    get_npcs_with_voices,
)
from voiceover_mage.demo.services.pipeline_service import (
    generate_dialogue,
    regenerate_voice_candidates,
    run_full_pipeline,
    select_voice_candidate,
)

__all__ = [
    "get_available_npcs",
    "get_npcs_with_voices",
    "get_npc_display_data",
    "find_npc_id_by_display_name",
    "run_full_pipeline",
    "regenerate_voice_candidates",
    "select_voice_candidate",
    "generate_dialogue",
]
