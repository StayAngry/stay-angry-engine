"""Test suite validating audio beat tracking and rhythm-synchronized timeline cuts."""

import pytest
from pathlib import Path
from sae.audio.engine import AudioIntelligenceEngine
from sae.audio.models import BeatStrength
from sae.creative.engine import CreativeEditingEngine
from sae.database import DatabaseManager
from sae.events import EventBus
from sae.media.manager import MediaAssetManager
from sae.vision.engine import AdvancedVideoIntelligenceEngine


@pytest.fixture
def sync_env(tmp_path: Path):
    db = DatabaseManager(tmp_path / "sync.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "cache")
    vision_engine = AdvancedVideoIntelligenceEngine(media_manager=media_mgr)
    audio_engine = AudioIntelligenceEngine(media_manager=media_mgr)
    creative_engine = CreativeEditingEngine(
        media_manager=media_mgr,
        vision_engine=vision_engine,
        audio_engine=audio_engine,
    )
    return creative_engine, audio_engine


def test_audio_engine_beat_detection(sync_env):
    _, audio_engine = sync_env
    report = audio_engine.analyze_audio_asset("music_track_01", duration_sec=10.0, bpm=120.0)

    assert report.asset_id == "music_track_01"
    assert report.estimated_bpm == 120.0
    assert len(report.beats) > 0
    assert any(b.strength == BeatStrength.DOWNBEAT for b in report.beats)

    nearest = report.find_nearest_beat(1.05, tolerance_sec=0.2)
    assert nearest == 1.0


def test_vision_beat_snapping_cuts(sync_env):
    creative_engine, _ = sync_env
    blueprint = creative_engine.ingest_vision_intelligence(
        asset_id="action_cut_beat",
        target_duration=10.0,
        snap_to_beats=True,
    )

    assert len(blueprint.video_clips) >= 1
    assert "Beat snapped: True" in blueprint.video_clips[0].selection_reason
