# ABOUTME: Tests for NPC persistence models
# ABOUTME: Validates SQLModel definitions and field constraints

from datetime import UTC, datetime

from voiceover_mage.persistence.models import NPCData


class TestNPCDataValidation:
    """Test NPCData model validation and constraints."""

    def test_minimal_required_fields(self):
        """Test creation with only required fields."""
        extraction = NPCData(
            npc_id=1,
            npc_name="Hans",
            wiki_url="https://oldschool.runescape.wiki/w/Hans",
            raw_markdown="# Hans\nContent here",
        )

        assert extraction.npc_id == 1
        assert extraction.npc_name == "Hans"
        assert extraction.wiki_url == "https://oldschool.runescape.wiki/w/Hans"
        assert extraction.raw_markdown == "# Hans\nContent here"
        assert extraction.extraction_success is True  # Default value
        assert extraction.chathead_image_url is None
        assert extraction.image_url is None
        assert extraction.error_message is None

    def test_all_fields(self):
        """Test creation with all fields."""
        now = datetime.now(UTC)
        extraction = NPCData(
            id=1,
            npc_id=2,
            npc_name="Wise Old Man",
            wiki_url="https://oldschool.runescape.wiki/w/Wise_Old_Man",
            raw_markdown="# Wise Old Man\nA powerful wizard...",
            chathead_image_url="https://example.com/wom_chathead.png",
            image_url="https://example.com/wom.png",
            created_at=now,
            extraction_success=True,
            error_message=None,
        )

        assert extraction.id == 1
        assert extraction.npc_id == 2
        assert extraction.npc_name == "Wise Old Man"
        assert extraction.created_at == now
        assert extraction.extraction_success is True

    def test_error_state(self):
        """Test extraction in error state."""
        extraction = NPCData(
            npc_id=404,
            npc_name="Missing NPC",
            wiki_url="https://oldschool.runescape.wiki/w/Missing",
            raw_markdown="",  # Empty markdown for failed extraction
            extraction_success=False,
            error_message="HTTP 404: Page not found",
        )

        assert extraction.extraction_success is False
        assert extraction.error_message == "HTTP 404: Page not found"
        assert extraction.raw_markdown == ""

    def test_large_markdown_content(self):
        """Test handling of large markdown content."""
        # Create a large markdown string (simulating a full wiki page)
        large_content = "# NPC Name\n\n"
        large_content += "## Description\n" + ("Lorem ipsum dolor sit amet. " * 100) + "\n\n"
        large_content += "## Dialogue\n" + ("'Hello there!' " * 50) + "\n\n"
        large_content += "## Trivia\n" + ("Interesting fact. " * 200)

        extraction = NPCData(
            npc_id=1,
            npc_name="Verbose NPC",
            wiki_url="https://example.com",
            raw_markdown=large_content,
        )

        assert len(extraction.raw_markdown) > 5000
        assert extraction.raw_markdown == large_content

    def test_empty_optional_fields(self):
        """Test that optional fields can be None."""
        extraction = NPCData(
            npc_id=1,
            npc_name="Simple NPC",
            wiki_url="https://example.com",
            raw_markdown="Content",
            chathead_image_url=None,
            image_url=None,
            error_message=None,
        )

        assert extraction.chathead_image_url is None
        assert extraction.image_url is None
        assert extraction.error_message is None

    def test_special_characters_in_strings(self):
        """Test handling of special characters in string fields."""
        extraction = NPCData(
            npc_id=1,
            npc_name="TzHaar-Ket-Rak",  # Special characters in name
            wiki_url="https://oldschool.runescape.wiki/w/TzHaar-Ket-Rak",
            raw_markdown="# TzHaar-Ket-Rak\n\n*Italic* **Bold** `Code` [Link](url)",
            error_message="Connection failed: ñ€øŧ føüñđ",  # Unicode in error
        )

        assert extraction.npc_name == "TzHaar-Ket-Rak"
        assert "*Italic*" in extraction.raw_markdown
        assert extraction.error_message is not None
        assert "ñ€øŧ føüñđ" in extraction.error_message

    def test_url_validation(self):
        """Test URL field handling."""
        extraction = NPCData(
            npc_id=1,
            npc_name="Test",
            wiki_url="https://oldschool.runescape.wiki/w/Test_(npc)",  # Parentheses in URL
            raw_markdown="Content",
            chathead_image_url="https://cdn.wiki.com/images/Test_chathead.png?v=12345",  # Query params
            image_url="https://cdn.wiki.com/images/Test.png#anchor",  # Fragment
        )

        assert "(npc)" in extraction.wiki_url
        assert extraction.chathead_image_url is not None
        assert "?v=12345" in extraction.chathead_image_url
        assert extraction.image_url is not None
        assert "#anchor" in extraction.image_url

    def test_model_dict_export(self):
        """Test exporting model to dictionary."""
        extraction = NPCData(
            npc_id=1,
            npc_name="Hans",
            wiki_url="https://example.com",
            raw_markdown="Content",
        )

        data = extraction.model_dump()

        assert data["npc_id"] == 1
        assert data["npc_name"] == "Hans"
        assert data["wiki_url"] == "https://example.com"
        assert data["raw_markdown"] == "Content"
        assert "extraction_success" in data
        assert "chathead_image_url" in data

    def test_model_json_export(self):
        """Test exporting model to JSON string."""
        extraction = NPCData(
            npc_id=1,
            npc_name="Hans",
            wiki_url="https://example.com",
            raw_markdown="Content",
        )

        json_str = extraction.model_dump_json()

        assert '"npc_id":1' in json_str or '"npc_id": 1' in json_str
        assert '"npc_name":"Hans"' in json_str or '"npc_name": "Hans"' in json_str

    def test_model_copy_with_update(self):
        """Test creating a copy with updates."""
        original = NPCData(
            npc_id=1,
            npc_name="Hans",
            wiki_url="https://example.com",
            raw_markdown="Original content",
        )

        updated = original.model_copy(
            update={
                "raw_markdown": "Updated content",
                "extraction_success": False,
                "error_message": "Test error",
            }
        )

        assert updated.npc_id == original.npc_id
        assert updated.npc_name == original.npc_name
        assert updated.raw_markdown == "Updated content"
        assert updated.extraction_success is False
        assert updated.error_message == "Test error"
        assert original.raw_markdown == "Original content"  # Original unchanged
