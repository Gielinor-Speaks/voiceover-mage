# ABOUTME: Business logic and orchestration layer
# ABOUTME: Pipeline Stage 3: Stored data → Processed business objects

"""
Core Layer: Business logic and workflow orchestration

This layer handles:
- High-level business logic and rules
- Pipeline orchestration and stage management
- Service APIs and public interfaces
- Domain models and business object creation

Data Flow: persistence/ data → Business processing → Final outputs
"""

from .models import (
    ExtractionStage,
    NPCDetails,
    NPCProfile,
    NPCWikiSourcedData,
    TrackedField,
)

# Import service on-demand to avoid circular imports
# Use: from voiceover_mage.core.service import NPCExtractionService

__all__ = [
    "ExtractionStage",
    "NPCDetails",
    "NPCProfile",
    "NPCWikiSourcedData",
    "TrackedField",
]
