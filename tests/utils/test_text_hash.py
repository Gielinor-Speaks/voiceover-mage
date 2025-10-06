# ABOUTME: Tests for text normalization and hashing utilities


from voiceover_mage.utils.text_hash import compute_dialogue_hash, normalize_dialogue_text


class TestTextNormalization:
    """Test suite for dialogue text normalization."""

    def test_normalize_strips_whitespace(self):
        """Normalization should remove leading/trailing whitespace."""
        assert normalize_dialogue_text("  hello  ") == "hello"
        assert normalize_dialogue_text("\thello\n") == "hello"

    def test_normalize_converts_to_lowercase(self):
        """Normalization should convert text to lowercase."""
        assert normalize_dialogue_text("HELLO") == "hello"
        assert normalize_dialogue_text("HeLLo") == "hello"

    def test_normalize_preserves_internal_spaces(self):
        """Normalization should preserve spaces within text."""
        assert normalize_dialogue_text("hello world") == "hello world"
        assert normalize_dialogue_text("  hello   world  ") == "hello   world"

    def test_normalize_idempotent(self):
        """Normalizing twice should produce same result."""
        text = "  HELLO World  "
        normalized_once = normalize_dialogue_text(text)
        normalized_twice = normalize_dialogue_text(normalized_once)
        assert normalized_once == normalized_twice


class TestDialogueHashing:
    """Test suite for dialogue hash computation."""

    def test_compute_hash_returns_sha256(self):
        """Hash should be a valid SHA256 hex digest (64 chars)."""
        hash_result = compute_dialogue_hash("hello")
        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)

    def test_compute_hash_normalizes_input(self):
        """Hashing should normalize input first."""
        # Different formatting, same normalized text = same hash
        assert compute_dialogue_hash("hello") == compute_dialogue_hash("  HELLO  ")
        assert compute_dialogue_hash("hello world") == compute_dialogue_hash("  HELLO WORLD  ")

    def test_compute_hash_deterministic(self):
        """Same input should always produce same hash."""
        text = "Hello, adventurer!"
        hash1 = compute_dialogue_hash(text)
        hash2 = compute_dialogue_hash(text)
        assert hash1 == hash2

    def test_compute_hash_different_content_different_hash(self):
        """Different content should produce different hashes."""
        hash1 = compute_dialogue_hash("hello")
        hash2 = compute_dialogue_hash("goodbye")
        assert hash1 != hash2

    def test_compute_hash_case_insensitive(self):
        """Case differences should not affect hash."""
        assert compute_dialogue_hash("Hello") == compute_dialogue_hash("hello")
        assert compute_dialogue_hash("HELLO") == compute_dialogue_hash("hello")

    def test_compute_hash_whitespace_insensitive_edges(self):
        """Leading/trailing whitespace should not affect hash."""
        assert compute_dialogue_hash("hello") == compute_dialogue_hash("  hello  ")
        assert compute_dialogue_hash("hello") == compute_dialogue_hash("\nhello\t")

    def test_compute_hash_preserves_internal_whitespace(self):
        """Internal whitespace differences should create different hashes."""
        hash1 = compute_dialogue_hash("hello world")
        hash2 = compute_dialogue_hash("helloworld")
        assert hash1 != hash2

    def test_compute_hash_unicode_support(self):
        """Should handle Unicode characters correctly."""
        hash1 = compute_dialogue_hash("hello 世界")
        hash2 = compute_dialogue_hash("hello 世界")
        assert hash1 == hash2
        assert len(hash1) == 64
