# ABOUTME: Text normalization and hashing utilities for dialogue matching
# ABOUTME: Provides consistent hash computation for content-addressable dialogue lookup

import hashlib


def normalize_dialogue_text(text: str) -> str:
    """Normalize text for consistent dialogue matching.

    Applies canonical normalization to ensure identical text produces
    identical hashes regardless of minor formatting differences.

    Args:
        text: Raw dialogue text

    Returns:
        Normalized text suitable for hashing
    """
    return text.strip().lower()


def compute_dialogue_hash(text: str) -> str:
    """Compute SHA256 hash of normalized dialogue text.

    This hash is used as a content-addressable key for fast dialogue
    lookups in the database.

    Args:
        text: Raw dialogue text (will be normalized internally)

    Returns:
        Hex-encoded SHA256 hash (64 characters)
    """
    normalized = normalize_dialogue_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
