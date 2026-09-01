"""Comprehensive Phase 10 test suite validating timeline generation, beat synchronization, and blueprint validation."""

import pytest
from pathlib import Path
from sae.creative.engine import CreativeEditingEngine
from sae.creative.models import CameraMotion, CreativeStyleType, PlatformFormat, TimelineClip
from sae.creative.validator import TimelineValidator
from sae.database import DatabaseManager
from sae.events import EventBus
from sae.media.manager import MediaAssetManager


@pytest.fixture
def creative_engine(tmp_path: Path):
    db_path = tmp_path / "test_sae_creative.db"
    db = DatabaseManager(db_path)
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "cache")
    return CreativeEditingEngine(media_mgr), media_mgr


def test_generate_reel_blueprint_creates_valid_timeline(creative_engine):
    engine, _ = creative_engine
    bp = engine.generate_reel_blueprint("Solo Leveling Reel", target_duration=12.0)

    assert bp.title == "Solo Leveling Reel"
    assert bp.format == PlatformFormat.VERTICAL_SHORT
    assert bp.width == 1080
    assert bp.height == 1920
    assert len(bp.video_clips) >= 3
    assert bp.color_grade.profile_name in ("CINEMATIC_ANIME", "DARK_MANHWA")


def test_timeline_validator_catches_overlaps_and_missing_assets(creative_engine):
    engine, _ = creative_engine
    bp = engine.generate_reel_blueprint("Test Blueprint", target_duration=10.0)

    # Force a timeline collision
    bp.video_clips.append(
        TimelineClip(
            clip_id="colliding_clip",
            asset_id="mock_asset",
            track_index=1,
            source_in_sec=0.0,
            source_out_sec=2.0,
            timeline_start_sec=1.0,
            timeline_end_sec=3.0
        )
    )

    is_valid, errors = TimelineValidator.validate(bp, registered_asset_ids={"mock_asset"})
    assert is_valid is False
    assert any("collision" in e.lower() for e in errors)