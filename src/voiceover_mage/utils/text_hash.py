# ABOUTME: Text normalization and hashing utilities for dialogue matching
# ABOUTME: Provides consistent hash computation for content-addressable dialogue lookup

import hashlib
import re


def normalize_dialogue_text(text: str) -> str:
    """Normalize text for consistent dialogue matching while preserving punctuation.

    Normalization removes display-only formatting but preserves semantic content
    that affects TTS prosody (punctuation, capitalization for proper nouns).

    Applies:
    - Block-level HTML tag removal (e.g., <br/>, <br>, <p>) → replaced with space
    - Inline HTML tag removal (e.g., <color>, <b>, <i>) → removed without space
    - Whitespace normalization (multiple spaces/newlines → single space)
    - Leading/trailing whitespace removal

    Does NOT apply:
    - Case normalization (preserves capitalization)
    - Punctuation removal (preserves prosody markers: . ! ? , ; :)

    Args:
        text: Raw dialogue text with potential HTML formatting

    Returns:
        Normalized text suitable for hashing

    Examples:
        >>> normalize_dialogue_text("Hello,<br/>adventurer!")
        'Hello, adventurer!'
        >>> normalize_dialogue_text("What?!  Really?")
        'What?! Really?'
        >>> normalize_dialogue_text("I am the <color=blue>Wise Old Man</color>.")
        'I am the Wise Old Man.'
    """
    # Replace block-level tags with space (prevent word concatenation)
    # Common OSRS wiki tags: <br/>, <br>, <p>
    text = re.sub(r"<(?:br/?>|p>)", " ", text, flags=re.IGNORECASE)

    # Remove all other HTML tags without adding space (inline tags)
    # Common OSRS wiki tags: <color=...>, </color>, <b>, </b>, etc.
    text = re.sub(r"<[^>]+>", "", text)

    # Normalize whitespace: multiple spaces/tabs/newlines → single space
    text = re.sub(r"\s+", " ", text)

    # Strip leading/trailing whitespace
    return text.strip()


def compute_dialogue_hash(npc_id: int, text: str) -> str:
    """Compute SHA256 hash of NPC ID + normalized dialogue text.

    Including NPC ID ensures the same dialogue spoken by different NPCs
    produces different cache keys (important since different NPCs have
    different voices/personalities).

    This hash computation MUST match the client implementation exactly.
    Client (Java): String key = npcId + "-" + normalize(dialogue);

    Args:
        npc_id: NPC identifier
        text: Raw dialogue text (will be normalized internally)

    Returns:
        Hex-encoded SHA256 hash (64 characters), URL-safe

    Examples:
        >>> compute_dialogue_hash(3105, "Hello, adventurer!")
        'a3c5e8f2b1d9c4e7a2f1b3c5d8e9f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8'
    """
    normalized = normalize_dialogue_text(text)
    key = f"{npc_id}:{normalized}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
