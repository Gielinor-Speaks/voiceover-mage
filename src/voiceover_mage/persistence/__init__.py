# ABOUTME: Database operations and data persistence layer
# ABOUTME: Pipeline Stage 2: Structured data → Database storage with checkpointing

"""
Persistence Layer: Save and retrieve data with checkpointing

This layer handles:
- SQLModel database tables and relationships
- Checkpoint-based pipeline state management
- Caching and retrieval of processed data
- Database connection and transaction management

Data Flow: extraction/ data → Database → core/ business logic
"""

from .json_types import PydanticJson
from .manager import DatabaseManager, NPCPipelineState
from .models import AudioTranscript, CharacterProfile, NPC, VoicePreview, WikiSnapshot

__all__ = [
    "DatabaseManager",
    "AudioTranscript",
    "CharacterProfile",
    "NPCPipelineState",
    "NPC",
    "VoicePreview",
    "WikiSnapshot",
    "PydanticJson",
]
