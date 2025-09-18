# ABOUTME: Model-level tests for normalized NPC persistence schema
# ABOUTME: Ensures SQLModel definitions expose expected defaults and relationships

from __future__ import annotations

from datetime import UTC, datetime

from voiceover_mage.persistence.models import NPC, AudioTranscript, CharacterProfile, VoicePreview, WikiSnapshot


def test_npc_defaults():
    npc = NPC(id=1, name="Hans", variant=None, wiki_url="https://oldschool.runescape.wiki/w/Hans")

    assert npc.id == 1
    assert npc.name == "Hans"
    assert npc.selected_preview_id is None
    assert npc.created_at.tzinfo is UTC
    assert npc.updated_at.tzinfo is UTC


def test_wiki_snapshot_fields():
    now = datetime.now(UTC)
    snapshot = WikiSnapshot(
        npc_id=1,
        raw_markdown="# Hans\nNPC description",
        chathead_image_url="https://example.com/chat.png",
        image_url="https://example.com/full.png",
        raw_data_json=None,
        source_checksum="abc123",
        fetched_at=now,
        extraction_success=True,
        error_message=None,
    )

    assert snapshot.npc_id == 1
    assert snapshot.raw_markdown.startswith("# Hans")
    assert snapshot.source_checksum == "abc123"
    assert snapshot.fetched_at == now
    assert snapshot.extraction_success is True


def test_character_profile_optional_json():
    profile = CharacterProfile(
        npc_id=1,
        profile_json=None,
        text_analysis_json=None,
        visual_analysis_json=None,
        pipeline_version="v0",
        updated_at=datetime.now(UTC),
    )

    assert profile.npc_id == 1
    assert profile.profile_json is None
    assert profile.pipeline_version == "v0"


def test_voice_preview_storage():
    preview = VoicePreview(
        npc_id=1,
        voice_prompt="warm and friendly",
        sample_text="Hello adventurer!",
        provider="elevenlabs",
        model="eleven_ttv_v3",
        generation_metadata={"attempt": 1},
        audio_path="/tmp/sample.mp3",
        audio_bytes=b"123",
        is_representative=False,
        created_at=datetime.now(UTC),
    )

    assert preview.npc_id == 1
    assert preview.audio_path == "/tmp/sample.mp3"
    assert preview.is_representative is False
    assert preview.generation_metadata["attempt"] == 1


def test_audio_transcript_metadata():
    transcript = AudioTranscript(
        npc_id=1,
        preview_id=2,
        provider="whisper",
        text="Hello adventurer!",
        metadata_json={"language": "en"},
        created_at=datetime.now(UTC),
    )

    assert transcript.npc_id == 1
    assert transcript.preview_id == 2
    assert transcript.metadata_json["language"] == "en"
