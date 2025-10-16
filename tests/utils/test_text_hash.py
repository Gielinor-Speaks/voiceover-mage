# ABOUTME: Tests for text normalization and hashing utilities


from voiceover_mage.utils.text_hash import compute_dialogue_hash, normalize_dialogue_text


class TestTextNormalization:
    """Test suite for dialogue text normalization."""

    def test_normalize_strips_whitespace(self):
        """Normalization should remove leading/trailing whitespace."""
        assert normalize_dialogue_text("  hello  ") == "hello"
        assert normalize_dialogue_text("\thello\n") == "hello"

    def test_normalize_preserves_case(self):
        """Normalization should preserve capitalization for TTS prosody."""
        assert normalize_dialogue_text("HELLO") == "HELLO"
        assert normalize_dialogue_text("HeLLo") == "HeLLo"
        assert normalize_dialogue_text("King Arthur") == "King Arthur"

    def test_normalize_preserves_punctuation(self):
        """Normalization should preserve punctuation for TTS prosody."""
        assert normalize_dialogue_text("Hello!") == "Hello!"
        assert normalize_dialogue_text("What?!") == "What?!"
        assert normalize_dialogue_text("Wait...") == "Wait..."
        assert normalize_dialogue_text("Yes, sir.") == "Yes, sir."

    def test_normalize_removes_html_tags(self):
        """Normalization should remove HTML tags (display-only formatting)."""
        assert normalize_dialogue_text("Hello<br/>world") == "Hello world"
        assert normalize_dialogue_text("<color=red>Stop!</color>") == "Stop!"
        assert normalize_dialogue_text("Line 1<br/><br/>Line 2") == "Line 1 Line 2"

    def test_normalize_collapses_whitespace(self):
        """Normalization should collapse multiple spaces to single space."""
        assert normalize_dialogue_text("hello  world") == "hello world"
        assert normalize_dialogue_text("hello   \n  world") == "hello world"
        assert normalize_dialogue_text("  hello   world  ") == "hello world"

    def test_normalize_idempotent(self):
        """Normalizing twice should produce same result."""
        text = "  Hello<br/>World!  "
        normalized_once = normalize_dialogue_text(text)
        normalized_twice = normalize_dialogue_text(normalized_once)
        assert normalized_once == normalized_twice

    def test_normalize_osrs_dialogue_examples(self):
        """Test normalization with real OSRS dialogue patterns."""
        # Common OSRS wiki formatting
        assert normalize_dialogue_text("Greetings,<br/>adventurer!") == "Greetings, adventurer!"
        assert normalize_dialogue_text("What do you want?") == "What do you want?"
        assert normalize_dialogue_text("I am the <color=blue>Wise Old Man</color>.") == "I am the Wise Old Man."


class TestDialogueHashing:
    """Test suite for dialogue hash computation."""

    def test_compute_hash_returns_sha256(self):
        """Hash should be a valid SHA256 hex digest (64 chars)."""
        hash_result = compute_dialogue_hash(3105, "hello")
        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)

    def test_compute_hash_includes_npc_id(self):
        """Hash should include NPC ID (same text, different NPC = different hash)."""
        text = "Hello, adventurer!"
        hash1 = compute_dialogue_hash(3105, text)
        hash2 = compute_dialogue_hash(9999, text)
        assert hash1 != hash2

    def test_compute_hash_normalizes_input(self):
        """Hashing should normalize input first."""
        npc_id = 3105
        # Different whitespace formatting = same hash
        assert compute_dialogue_hash(npc_id, "hello") == compute_dialogue_hash(npc_id, "  hello  ")
        assert compute_dialogue_hash(npc_id, "hello world") == compute_dialogue_hash(npc_id, "hello   world")

    def test_compute_hash_deterministic(self):
        """Same input should always produce same hash."""
        npc_id = 3105
        text = "Hello, adventurer!"
        hash1 = compute_dialogue_hash(npc_id, text)
        hash2 = compute_dialogue_hash(npc_id, text)
        assert hash1 == hash2

    def test_compute_hash_different_content_different_hash(self):
        """Different content should produce different hashes."""
        npc_id = 3105
        hash1 = compute_dialogue_hash(npc_id, "hello")
        hash2 = compute_dialogue_hash(npc_id, "goodbye")
        assert hash1 != hash2

    def test_compute_hash_case_sensitive(self):
        """Case differences SHOULD affect hash (preserves proper nouns for TTS)."""
        npc_id = 3105
        hash1 = compute_dialogue_hash(npc_id, "Hello")
        hash2 = compute_dialogue_hash(npc_id, "hello")
        assert hash1 != hash2

    def test_compute_hash_punctuation_sensitive(self):
        """Punctuation differences SHOULD affect hash (affects TTS prosody)."""
        npc_id = 3105
        hash1 = compute_dialogue_hash(npc_id, "Stop!")
        hash2 = compute_dialogue_hash(npc_id, "Stop")
        assert hash1 != hash2

    def test_compute_hash_whitespace_insensitive_edges(self):
        """Leading/trailing whitespace should not affect hash."""
        npc_id = 3105
        assert compute_dialogue_hash(npc_id, "hello") == compute_dialogue_hash(npc_id, "  hello  ")
        assert compute_dialogue_hash(npc_id, "hello") == compute_dialogue_hash(npc_id, "\nhello\t")

    def test_compute_hash_collapses_internal_whitespace(self):
        """Multiple internal spaces should be collapsed to single space."""
        npc_id = 3105
        hash1 = compute_dialogue_hash(npc_id, "hello world")
        hash2 = compute_dialogue_hash(npc_id, "hello  world")
        assert hash1 == hash2  # Both become "hello world"

    def test_compute_hash_removes_html(self):
        """HTML tags should be removed before hashing."""
        npc_id = 3105
        hash1 = compute_dialogue_hash(npc_id, "Hello<br/>world")
        hash2 = compute_dialogue_hash(npc_id, "Hello world")
        assert hash1 == hash2

    def test_compute_hash_unicode_support(self):
        """Should handle Unicode characters correctly."""
        npc_id = 3105
        hash1 = compute_dialogue_hash(npc_id, "hello 世界")
        hash2 = compute_dialogue_hash(npc_id, "hello 世界")
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_compute_hash_osrs_dialogue_examples(self):
        """Test with realistic OSRS dialogue patterns."""
        npc_id = 3105

        # Same semantic content with different HTML formatting
        hash1 = compute_dialogue_hash(npc_id, "Greetings,<br/>adventurer!")
        hash2 = compute_dialogue_hash(npc_id, "Greetings, adventurer!")
        assert hash1 == hash2

        # Different punctuation = different hash (affects TTS)
        hash3 = compute_dialogue_hash(npc_id, "What do you want?")
        hash4 = compute_dialogue_hash(npc_id, "What do you want.")
        assert hash3 != hash4
