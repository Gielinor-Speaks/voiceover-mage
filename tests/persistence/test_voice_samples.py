import pytest

from voiceover_mage.persistence import DatabaseManager


@pytest.mark.asyncio
async def test_save_and_list_voice_samples():
    db = DatabaseManager(database_url="sqlite+aiosqlite://")
    await db.create_tables()

    # Save three samples for npc 42
    for i in range(3):
        await db.save_voice_sample(
            npc_id=42,
            voice_prompt=f"prompt {i + 1}",
            sample_text=f"text {i + 1}",
            audio_bytes=b"1234567890" * (i + 1),
            provider="elevenlabs",
            generator="text_to_voice.design:eleven_ttv_v3",
            is_representative=False,
            provider_metadata={"model_id": "eleven_ttv_v3", "preview_index": i + 1, "total_previews": 3},
        )

    samples = await db.list_voice_samples(42)
    assert len(samples) == 3
    assert {s.provider_metadata.get("preview_index") for s in samples} == {1, 2, 3}
    assert all(s.npc_id == 42 for s in samples)


@pytest.mark.asyncio
async def test_set_representative_sample_demotes_others():
    db = DatabaseManager(database_url="sqlite+aiosqlite://")
    await db.create_tables()

    s1 = await db.save_voice_sample(
        npc_id=7,
        voice_prompt="p1",
        sample_text="t1",
        audio_bytes=b"a" * 100,
        provider="elevenlabs",
        generator="text_to_voice.design:eleven_ttv_v3",
    )
    s2 = await db.save_voice_sample(
        npc_id=7,
        voice_prompt="p2",
        sample_text="t2",
        audio_bytes=b"b" * 200,
        provider="elevenlabs",
        generator="text_to_voice.design:eleven_ttv_v3",
    )

    assert s2.id is not None
    result = await db.set_representative_sample(7, s2.id)
    assert result is not None and result.is_representative is True

    samples = await db.list_voice_samples(7)
    reps = [s for s in samples if s.is_representative]
    assert len(reps) == 1 and reps[0].id == s2.id
    assert any(s.id == s1.id and not s.is_representative for s in samples)


@pytest.mark.asyncio
async def test_provider_metadata_and_blob_persisted():
    db = DatabaseManager(database_url="sqlite+aiosqlite://")
    await db.create_tables()

    blob = b"\x00\x01\x02" * 123
    await db.save_voice_sample(
        npc_id=5,
        voice_prompt="prompt",
        sample_text="text",
        audio_bytes=blob,
        provider="elevenlabs",
        generator="text_to_voice.design:eleven_ttv_v3",
        provider_metadata={"model_id": "eleven_ttv_v3", "setting": "test"},
    )

    samples = await db.list_voice_samples(5)
    assert len(samples) == 1
    s = samples[0]
    assert len(s.audio_bytes) == len(blob)
    assert s.provider_metadata.get("model_id") == "eleven_ttv_v3"
