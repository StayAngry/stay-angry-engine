"""Test suite validating ASS subtitle injection and filtergraph burn-in integration."""

import pytest
from pathlib import Path
from sae.creative.engine import CreativeEditingEngine
from sae.creative.models import CreativeStyleType
from sae.database import DatabaseManager
from sae.effects.typography_engine import KineticTypographyEngine
from sae.effects.typography_models import SubtitleSegment, TypographyConfig, WordTiming
from sae.events import EventBus
from sae.media.manager import MediaAssetManager
from sae.render.backend import FFmpegMediaBackend, MockMediaBackend


@pytest.mark.asyncio
async def test_backend_filtergraph_burns_ass_subtitles(tmp_path: Path):
    db = DatabaseManager(tmp_path / "burn.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "media")
    creative = CreativeEditingEngine(media_mgr)
    typo_engine = KineticTypographyEngine(media_mgr, output_dir=tmp_path / "subs")

    blueprint = creative.generate_reel_blueprint(
        title="Burn-In Reel",
        target_duration=4.0,
        style=CreativeStyleType.DARK_MANHWA,
    )

    # Export a test subtitle track
    segments = [
        SubtitleSegment(
            segment_id="sub_1",
            start_sec=0.0,
            end_sec=2.0,
            text="ACTION TRIGGER",
            words=[WordTiming(word="ACTION", start_sec=0.0, end_sec=1.0)],
        )
    ]
    ass_path = typo_engine.export_subtitles(segments, blueprint, TypographyConfig())

    backend = FFmpegMediaBackend(output_dir=tmp_path / "output")
    out_video = tmp_path / "output" / "reel_burned.mp4"

    result = await backend.render(
        target=blueprint,
        output_path=out_video,
        subtitle_path=ass_path,
    )

    assert result.status.value == "COMPLETED"
    assert out_video.exists()

    content = out_video.read_text(encoding="utf-8")
    assert "Subtitles:" in content or "MOCK_RENDER" in content
    assert str(ass_path.name) in content or "ass=" in content


@pytest.mark.asyncio
async def test_mock_backend_records_subtitle_path(tmp_path: Path):
    db = DatabaseManager(tmp_path / "mock_burn.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "media")
    creative = CreativeEditingEngine(media_mgr)

    blueprint = creative.generate_reel_blueprint(
        title="Mock Subtitle Reel",
        target_duration=3.0,
    )

    mock_backend = MockMediaBackend(output_dir=tmp_path / "output")
    dummy_sub = tmp_path / "sample.ass"
    dummy_sub.write_text("dummy ass content", encoding="utf-8")

    out_file = tmp_path / "output" / "mock_out.mp4"
    result = await mock_backend.render(blueprint, output_path=out_file, subtitle_path=dummy_sub)

    assert result.status.value == "COMPLETED"
    assert f"SUBS={dummy_sub}" in out_file.read_text(encoding="utf-8")
