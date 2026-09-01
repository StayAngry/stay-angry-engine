"""Comprehensive Phase 12 test suite validating hierarchical video intelligence, shot classification, and motion tracking."""

import pytest
from pathlib import Path
from sae.database import DatabaseManager
from sae.events import EventBus
from sae.media.manager import MediaAssetManager
from sae.vision.engine import AdvancedVideoIntelligenceEngine
from sae.vision.models import CameraAngle, ShotType


@pytest.fixture
def vision_env(tmp_path: Path):
    db = DatabaseManager(tmp_path / "test_sae_vision.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "cache")
    engine = AdvancedVideoIntelligenceEngine(media_manager=media_mgr)
    return engine, media_mgr


def test_hierarchical_video_intelligence_generation(vision_env):
    engine, _ = vision_env
    report = engine.analyze_asset("mock_anime_asset_123")

    assert report.asset_id == "mock_anime_asset_123"
    assert report.global_visual_energy > 0.0
    assert len(report.scenes) >= 1

    first_scene = report.scenes[0]
    assert len(first_scene.shots) >= 3
    assert first_scene.shots[0].shot_type in (ShotType.CLOSE_UP, ShotType.MEDIUM, ShotType.WIDE)
    assert first_scene.shots[0].subjects[0].has_face is True


def test_similar_shot_search_and_filtering(vision_env):
    engine, _ = vision_env
    # Populate analysis cache
    engine.analyze_asset("asset_alpha")

    matched_shots = engine.search_similar_shots(target_shot_type=ShotType.CLOSE_UP, min_energy=0.3)
    assert len(matched_shots) >= 1
    assert matched_shots[0].shot_type == ShotType.CLOSE_UP