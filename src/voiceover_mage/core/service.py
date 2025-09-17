# ABOUTME: High-level service API for orchestrating normalized NPC persistence
# ABOUTME: Handles raw extraction, caching, and stage-aware status reporting

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Iterable

from voiceover_mage.extraction.base import RawNPCExtractor, RawExtractionResult
from voiceover_mage.extraction.wiki.markdown import MarkdownNPCExtractor
from voiceover_mage.persistence import DatabaseManager, NPCPipelineState
from voiceover_mage.utils.logging import get_logger


def _compute_checksum(markdown: str) -> str | None:
    """Compute a stable checksum for wiki markdown content."""
    if not markdown:
        return None
    sha = hashlib.sha256()
    sha.update(markdown.encode("utf-8"))
    return sha.hexdigest()


class NPCExtractionService:
    """Service for extracting NPC data with cache-first logic."""

    def __init__(
        self,
        extractor: RawNPCExtractor | None = None,
        database: DatabaseManager | None = None,
        force_refresh: bool = False,
    ):
        self.extractor = extractor or MarkdownNPCExtractor()
        self.database = database or DatabaseManager()
        self.force_refresh = force_refresh
        self.logger = get_logger(__name__)

    async def extract_npc(self, npc_id: int) -> NPCPipelineState:
        """Extract NPC data and persist the normalized snapshot."""
        await self.database.create_tables()

        if not self.force_refresh:
            cached = await self.database.get_cached_extraction(npc_id)
            if cached:
                self.logger.info(
                    "Using cached extraction",
                    npc_id=npc_id,
                    npc_name=cached.npc_name,
                    stage_flags=cached.stage_flags,
                    extraction_success=cached.extraction_success,
                )
                return cached

        self.logger.info("Extracting fresh NPC data", npc_id=npc_id, force_refresh=self.force_refresh)

        raw_result = await self.extractor.extract(npc_id)

        await self.database.ensure_npc(
            npc_id=raw_result.npc_id,
            name=raw_result.npc_name,
            variant=raw_result.npc_variant,
            wiki_url=raw_result.wiki_url,
        )

        checksum = _compute_checksum(raw_result.raw_markdown)

        await self.database.upsert_wiki_snapshot(
            npc_id=raw_result.npc_id,
            raw_markdown=raw_result.raw_markdown,
            chathead_image_url=raw_result.chathead_image_url,
            image_url=raw_result.image_url,
            raw_data=None,
            source_checksum=checksum,
            fetched_at=datetime.now(UTC),
            extraction_success=raw_result.extraction_success,
            error_message=raw_result.error_message,
        )

        state = await self.database.get_cached_extraction(npc_id)
        if not state:
            raise RuntimeError("Failed to assemble NPC pipeline state after raw extraction")

        self.logger.info(
            "Raw extraction stored",
            npc_id=npc_id,
            npc_name=state.npc_name,
            markdown_length=len(state.raw_markdown),
            stage_flags=state.stage_flags,
            extraction_success=state.extraction_success,
        )

        return state

    async def extract_multiple_npcs(
        self, npc_ids: Iterable[int], progress_callback=None
    ) -> list[NPCPipelineState]:
        """Extract data for multiple NPCs with optional progress reporting."""
        npc_ids = list(npc_ids)
        total = len(npc_ids)
        results: list[NPCPipelineState] = []

        self.logger.info("Starting batch extraction", npc_count=total, force_refresh=self.force_refresh)

        for index, npc_id in enumerate(npc_ids, start=1):
            try:
                if progress_callback:
                    progress_callback(npc_id, index, total)
                state = await self.extract_npc(npc_id)
                results.append(state)
            except Exception as exc:  # pragma: no cover - logged for operator awareness
                self.logger.error(
                    "Failed to extract NPC in batch",
                    npc_id=npc_id,
                    error=str(exc),
                    current_index=index,
                    total=total,
                )
                await self._persist_failed_extraction(npc_id=npc_id, error=str(exc))
                cached = await self.database.get_cached_extraction(npc_id)
                if cached:
                    results.append(cached)

        successful = sum(1 for r in results if r.extraction_success)
        self.logger.info(
            "Batch extraction completed", total=total, successful=successful, failed=total - successful
        )

        return results

    async def _persist_failed_extraction(self, npc_id: int, error: str) -> None:
        """Ensure failure details are persisted for observability."""
        await self.database.ensure_npc(
            npc_id=npc_id,
            name=f"NPC_{npc_id}",
            variant=None,
            wiki_url="",
        )
        await self.database.upsert_wiki_snapshot(
            npc_id=npc_id,
            raw_markdown="",
            chathead_image_url=None,
            image_url=None,
            raw_data=None,
            source_checksum=None,
            fetched_at=datetime.now(UTC),
            extraction_success=False,
            error_message=error,
        )

    async def get_extraction_status(self, npc_id: int) -> dict[str, object]:
        """Return cached extraction status information."""
        state = await self.database.get_cached_extraction(npc_id)
        stage_flags = state.stage_flags if state else await self.database.compute_stage_map(npc_id)

        if not state:
            return {
                "npc_id": npc_id,
                "cached": False,
                "extraction_success": None,
                "npc_name": None,
                "stage_flags": stage_flags,
            }

        completed = state.completed_stages if state else [stage for stage, done in stage_flags.items() if done]

        return {
            "npc_id": npc_id,
            "cached": True,
            "npc_name": state.npc_name,
            "extraction_success": state.extraction_success,
            "stage_flags": stage_flags,
            "completed_stages": completed,
            "has_chathead": state.chathead_image_url is not None,
            "has_image": state.image_url is not None,
            "markdown_length": len(state.raw_markdown),
            "error_message": state.error_message,
        }

    async def clear_cache(self) -> None:
        """Clear all cached NPC pipeline data."""
        await self.database.clear_cache()
        self.logger.info("Cleared all cached extractions")

    async def close(self) -> None:
        """Clean up database resources."""
        await self.database.close()
