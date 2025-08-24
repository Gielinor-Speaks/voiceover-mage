# ABOUTME: Integration tests for the unified NPC extraction pipeline
# ABOUTME: End-to-end testing of the complete pipeline from raw extraction to character profiles

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from voiceover_mage.core.models import ExtractionStage
from voiceover_mage.core.unified_pipeline import UnifiedPipelineService
from voiceover_mage.persistence.manager import DatabaseManager
from voiceover_mage.persistence.models import NPCRawExtraction


class TestUnifiedPipelineService:
    """Integration tests for the UnifiedPipelineService."""

    @pytest.fixture
    def mock_database(self):
        """Create a mock database manager."""
        db = Mock(spec=DatabaseManager)
        db.create_tables = AsyncMock()
        db.async_session = AsyncMock()
        return db

    @pytest.fixture
    def mock_extraction_service(self):
        """Create a mock NPCExtractionService."""
        service = Mock()
        service.extract_npc = AsyncMock()
        service.close = AsyncMock()
        return service

    @pytest.fixture
    def mock_intelligent_extractor(self):
        """Create a mock NPCIntelligentExtractor."""
        extractor = Mock()

        # Mock sub-extractors
        extractor.text_extractor = Mock()
        extractor.image_extractor = Mock()
        extractor.synthesizer = Mock()

        return extractor

    @pytest.fixture
    def sample_raw_extraction(self):
        """Create a sample raw extraction for testing."""
        return NPCRawExtraction(
            npc_id=1001,
            npc_name="Integration Test NPC",
            wiki_url="https://wiki.com/Integration_Test_NPC",
            raw_markdown="""
            # Integration Test NPC
            
            ![Test NPC](https://wiki.com/images/test_npc.png)
            
            **Integration Test NPC** is a character created for testing the pipeline.
            They have a friendly personality and serve as a helpful guide.
            
            ## Dialogue
            - "Welcome to the integration test!"
            - "I'm here to help test the pipeline."
            - "Everything seems to be working correctly!"
            """,
            chathead_image_url="https://wiki.com/images/test_npc_chathead.png",
            image_url="https://wiki.com/images/test_npc.png",
            extraction_success=True,
            created_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, mock_database):
        """Test pipeline service initialization."""
        pipeline = UnifiedPipelineService(database=mock_database, force_refresh=False, api_key="test-api-key")

        assert pipeline.database == mock_database
        assert pipeline.force_refresh is False
        assert pipeline.api_key == "test-api-key"
        assert pipeline.raw_service is not None
        assert pipeline.intelligent_extractor is not None

    @pytest.mark.asyncio
    async def test_full_pipeline_without_api_key(self, mock_database, sample_raw_extraction):
        """Test full pipeline execution without API key (skips Crawl4AI LLM extraction)."""
        with (
            patch("voiceover_mage.core.unified_pipeline.NPCExtractionService") as mock_service_class,
            patch("voiceover_mage.core.unified_pipeline.NPCIntelligentExtractor") as mock_extractor_class,
        ):
            mock_service = Mock()
            mock_service.extract_npc = AsyncMock(return_value=sample_raw_extraction)
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service

            # Mock the intelligent extractor
            mock_extractor = Mock()
            mock_extractor.extract = AsyncMock(return_value=sample_raw_extraction)
            mock_extractor_class.return_value = mock_extractor

            # Create pipeline without API key
            pipeline = UnifiedPipelineService(database=mock_database, force_refresh=False, api_key=None)

            # Mock database operations
            mock_database.save_extraction = AsyncMock(return_value=sample_raw_extraction)
            mock_database.get_cached_extraction = AsyncMock(return_value=None)

            result = await pipeline.run_full_pipeline(1001)

            # Verify raw extraction completed
            assert result.npc_id == 1001
            assert result.npc_name == "Integration Test NPC"
            assert ExtractionStage.RAW.value in result.completed_stages

            # Verify intelligent analysis stages completed (DSPy doesn't require API key)
            assert ExtractionStage.TEXT.value in result.completed_stages
            assert ExtractionStage.VISUAL.value in result.completed_stages
            assert ExtractionStage.PROFILE.value in result.completed_stages
            assert ExtractionStage.COMPLETE.value in result.completed_stages

            mock_service.extract_npc.assert_called_once_with(1001)

    @pytest.mark.asyncio
    async def test_full_pipeline_with_api_key_success(self, mock_database, sample_raw_extraction):
        """Test successful full pipeline execution with API key (all phases)."""
        with (
            patch("voiceover_mage.core.unified_pipeline.NPCExtractionService") as mock_service_class,
            patch("voiceover_mage.core.unified_pipeline.Crawl4AINPCExtractor") as mock_crawl_class,
            patch("voiceover_mage.core.unified_pipeline.NPCIntelligentExtractor") as mock_extractor_class,
        ):
            # Setup raw service mock
            mock_service = Mock()
            mock_service.extract_npc = AsyncMock(return_value=sample_raw_extraction)
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service

            # Setup Crawl4AI mock
            mock_crawl = Mock()
            mock_wiki_data = Mock()
            mock_wiki_data.name.value = "Integration Test NPC"
            mock_wiki_data.model_dump.return_value = {"name": "Integration Test NPC"}
            mock_crawl.extract_npc_data = AsyncMock(return_value=mock_wiki_data)
            mock_crawl_class.return_value = mock_crawl

            # Setup intelligent extractor mock
            mock_extractor = Mock()
            mock_extractor.text_extractor = Mock()
            mock_extractor.image_extractor = Mock()
            mock_extractor.synthesizer = Mock()
            mock_extractor_class.return_value = mock_extractor

            # Create pipeline with API key
            pipeline = UnifiedPipelineService(database=mock_database, force_refresh=False, api_key="test-api-key")

            # Mock intelligent extractor components
            mock_text_result = Mock()
            mock_text_result.model_dump.return_value = {"personality": "friendly, helpful"}

            mock_visual_result = Mock()
            mock_visual_result.model_dump.return_value = {"age_category": "young adult"}

            mock_synthesis_result = Mock()
            mock_synthesis_result.model_dump.return_value = {
                "npc_name": "Integration Test NPC",
                "personality_traits": "friendly and helpful guide",
                "overall_confidence": 0.85,
            }
            mock_synthesis_result.personality_traits = "friendly and helpful guide"
            mock_synthesis_result.occupation = "helpful guide"
            mock_synthesis_result.overall_confidence = 0.85

            # Properly mock the DSPy module methods
            with (
                patch.object(pipeline.intelligent_extractor, "text_extractor", return_value=mock_text_result),
                patch.object(pipeline.intelligent_extractor, "image_extractor", return_value=mock_visual_result),
                patch.object(pipeline.intelligent_extractor, "synthesizer", return_value=mock_synthesis_result),
            ):
                # Mock database operations
                mock_database.async_session.return_value.__aenter__ = AsyncMock()
                mock_database.async_session.return_value.__aexit__ = AsyncMock()
                session_mock = Mock()

                # Track extraction object through pipeline stages
                current_extraction = sample_raw_extraction

                def mock_merge(extraction):
                    # Update the extraction object with new data
                    current_extraction.raw_data = getattr(extraction, "raw_data", {})
                    current_extraction.text_analysis = getattr(extraction, "text_analysis", {})
                    current_extraction.visual_analysis = getattr(extraction, "visual_analysis", {})
                    current_extraction.character_profile = getattr(extraction, "character_profile", {})
                    current_extraction.completed_stages = getattr(extraction, "completed_stages", [])
                    return current_extraction

                session_mock.merge = AsyncMock(side_effect=mock_merge)
                session_mock.commit = AsyncMock()
                session_mock.refresh = AsyncMock()
                mock_database.async_session.return_value.__aenter__.return_value = session_mock

                result = await pipeline.run_full_pipeline(1001)

                # Verify all phases completed
                assert result.npc_id == 1001
                assert ExtractionStage.RAW.value in result.completed_stages
                assert ExtractionStage.TEXT.value in result.completed_stages
                assert ExtractionStage.VISUAL.value in result.completed_stages
                assert ExtractionStage.SYNTHESIS.value in result.completed_stages
                assert ExtractionStage.COMPLETE.value in result.completed_stages

                # Verify analysis results are stored
                assert result.text_analysis is not None
                assert result.visual_analysis is not None
                assert result.character_profile is not None

                mock_service.extract_npc.assert_called_once_with(1001)
                mock_crawl.extract_npc_data.assert_called_once_with(1001)

    @pytest.mark.asyncio
    async def test_pipeline_with_llm_extraction_failure(self, mock_database, sample_raw_extraction):
        """Test pipeline handling LLM extraction failure gracefully."""
        with (
            patch("voiceover_mage.core.unified_pipeline.NPCExtractionService") as mock_service_class,
            patch("voiceover_mage.core.unified_pipeline.Crawl4AINPCExtractor") as mock_crawl_class,
            patch("voiceover_mage.core.unified_pipeline.NPCIntelligentExtractor") as mock_extractor_class,
        ):
            # Setup raw service mock
            mock_service = Mock()
            mock_service.extract_npc = AsyncMock(return_value=sample_raw_extraction)
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service

            # Setup Crawl4AI to fail
            mock_crawl = Mock()
            mock_crawl.extract_npc_data = AsyncMock(side_effect=Exception("LLM extraction failed"))
            mock_crawl_class.return_value = mock_crawl

            # Setup intelligent extractor mock
            mock_extractor = Mock()
            mock_extractor.text_extractor = Mock()
            mock_extractor.image_extractor = Mock()
            mock_extractor.synthesizer = Mock()
            mock_extractor_class.return_value = mock_extractor

            pipeline = UnifiedPipelineService(database=mock_database, api_key="test-api-key")

            # Mock database operations
            mock_database.async_session.return_value.__aenter__ = AsyncMock()
            mock_database.async_session.return_value.__aexit__ = AsyncMock()
            session_mock = Mock()
            session_mock.merge = AsyncMock(return_value=sample_raw_extraction)
            session_mock.commit = AsyncMock()
            session_mock.refresh = AsyncMock()
            mock_database.async_session.return_value.__aenter__.return_value = session_mock

            # Pipeline should continue despite LLM failure
            result = await pipeline.run_full_pipeline(1001)

            # Should have completed raw extraction but not LLM stages
            assert ExtractionStage.RAW.value in result.completed_stages
            # Intelligent analysis might still run if raw markdown is available
            # Pipeline should be resilient to individual stage failures

    @pytest.mark.asyncio
    async def test_pipeline_with_intelligent_analysis_failure(self, mock_database, sample_raw_extraction):
        """Test pipeline handling intelligent analysis failure."""
        with patch("voiceover_mage.core.unified_pipeline.NPCExtractionService") as mock_service_class:
            with patch("voiceover_mage.core.unified_pipeline.NPCIntelligentExtractor") as mock_extractor_class:
                # Setup raw service mock
                mock_service = Mock()
                mock_service.extract_npc = AsyncMock(return_value=sample_raw_extraction)
                mock_service.close = AsyncMock()
                mock_service_class.return_value = mock_service

                # Setup intelligent extractor mock
                mock_extractor = Mock()
                mock_extractor.text_extractor = Mock()
                mock_extractor.image_extractor = Mock()
                mock_extractor.synthesizer = Mock()
                mock_extractor_class.return_value = mock_extractor

                pipeline = UnifiedPipelineService(
                    database=mock_database,
                    api_key=None,  # No LLM extraction, just intelligent analysis
                )

            # Mock intelligent extractor to fail
            with patch.object(
                pipeline.intelligent_extractor, "text_extractor", side_effect=Exception("Text analysis failed")
            ):
                # Mock database operations
                mock_database.save_extraction = AsyncMock(return_value=sample_raw_extraction)
                mock_database.get_cached_extraction = AsyncMock(return_value=None)

                # Pipeline should continue and complete what it can
                result = await pipeline.run_full_pipeline(1001)

                # Should have basic extraction even if analysis fails
                assert result.npc_id == 1001
                assert ExtractionStage.RAW.value in result.completed_stages

    @pytest.mark.asyncio
    async def test_get_extraction_status(self, mock_database):
        """Test getting extraction status."""
        with patch("voiceover_mage.core.unified_pipeline.NPCIntelligentExtractor") as mock_extractor_class:
            # Setup intelligent extractor mock
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor

            # Mock cached extraction
            cached_extraction = NPCRawExtraction(
                npc_id=1001,
                npc_name="Status Test NPC",
                wiki_url="https://wiki.com/Status_Test_NPC",
                raw_markdown="# Status Test NPC\n\nMinimal test content.",
                completed_stages=[ExtractionStage.RAW.value, ExtractionStage.TEXT.value],
            )

            mock_database.get_cached_extraction = AsyncMock(return_value=cached_extraction)

            pipeline = UnifiedPipelineService(database=mock_database)

        status = await pipeline.get_extraction_status(1001)

        assert status["npc_id"] == 1001
        assert status["exists"] is True
        assert status["npc_name"] == "Status Test NPC"
        assert ExtractionStage.RAW.value in status["completed_stages"]
        assert ExtractionStage.TEXT.value in status["completed_stages"]
        assert status["is_complete"] is False  # Not complete stage

    @pytest.mark.asyncio
    async def test_get_extraction_status_not_found(self, mock_database):
        """Test getting status for non-existent extraction."""
        with patch("voiceover_mage.core.unified_pipeline.NPCIntelligentExtractor") as mock_extractor_class:
            # Setup intelligent extractor mock
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor

            mock_database.get_cached_extraction = AsyncMock(return_value=None)

            pipeline = UnifiedPipelineService(database=mock_database)

        status = await pipeline.get_extraction_status(9999)

        assert status["npc_id"] == 9999
        assert status["exists"] is False
        assert status["completed_stages"] == []
        assert status["has_character_profile"] is False

    @pytest.mark.asyncio
    async def test_pipeline_close(self, mock_database):
        """Test pipeline cleanup."""
        with patch("voiceover_mage.core.unified_pipeline.NPCExtractionService") as mock_service_class:
            with patch("voiceover_mage.core.unified_pipeline.NPCIntelligentExtractor") as mock_extractor_class:
                mock_service = Mock()
                mock_service.close = AsyncMock()
                mock_service_class.return_value = mock_service

                # Setup intelligent extractor mock
                mock_extractor = Mock()
                mock_extractor_class.return_value = mock_extractor

                pipeline = UnifiedPipelineService(database=mock_database)

            await pipeline.close()

            mock_service.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_with_empty_markdown(self, mock_database):
        """Test pipeline behavior with empty markdown content."""
        empty_extraction = NPCRawExtraction(
            npc_id=1002,
            npc_name="Empty Test NPC",
            wiki_url="https://wiki.com/Empty_Test_NPC",
            raw_markdown="",  # Empty markdown
            extraction_success=True,
        )

        with patch("voiceover_mage.core.unified_pipeline.NPCExtractionService") as mock_service_class:
            with patch("voiceover_mage.core.unified_pipeline.NPCIntelligentExtractor") as mock_extractor_class:
                mock_service = Mock()
                mock_service.extract_npc = AsyncMock(return_value=empty_extraction)
                mock_service.close = AsyncMock()
                mock_service_class.return_value = mock_service

                # Setup intelligent extractor mock
                mock_extractor = Mock()
                mock_extractor_class.return_value = mock_extractor

                pipeline = UnifiedPipelineService(database=mock_database)

            # Mock database operations
            mock_database.async_session.return_value.__aenter__ = AsyncMock()
            mock_database.async_session.return_value.__aexit__ = AsyncMock()
            session_mock = Mock()
            session_mock.merge = AsyncMock(return_value=empty_extraction)
            session_mock.commit = AsyncMock()
            session_mock.refresh = AsyncMock()
            mock_database.async_session.return_value.__aenter__.return_value = session_mock

            result = await pipeline.run_full_pipeline(1002)

            # Should complete raw extraction but skip intelligent analysis
            assert result.npc_id == 1002
            assert ExtractionStage.RAW.value in result.completed_stages
            # Intelligent analysis should be skipped due to empty markdown
