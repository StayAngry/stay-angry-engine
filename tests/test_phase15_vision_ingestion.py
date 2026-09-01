"""Test suite validating multimodal vision ingestion into creative editing blueprints."""

import pytest
from pathlib import Path
from sae.creative.engine import CreativeEditingEngine
from sae.creative.models import CreativeStyleType, PlatformFormat
from sae.database import DatabaseManager
from sae.events import EventBus
from sae.media.manager import MediaAssetManager
from sae.vision.engine import AdvancedVideoIntelligenceEngine


@pytest.fixture
def ingestion_env(tmp_path: Path):
    db = DatabaseManager(tmp_path / "test_ingestion.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "cache")
    vision_engine = AdvancedVideoIntelligenceEngine(media_manager=media_mgr)
    creative_engine = CreativeEditingEngine(media_manager=media_mgr, vision_engine=vision_engine)
    return creative_engine, vision_engine


def test_vision_intelligence_ingestion_blueprint(ingestion_env):
    creative_engine, _ = ingestion_env
    blueprint = creative_engine.ingest_vision_intelligence(
        asset_id="mock_action_clip_001",
        target_duration=12.0,
        style=CreativeStyleType.DARK_MANHWA,
        format_type=PlatformFormat.VERTICAL_SHORT,
    )

    assert blueprint.blueprint_id.startswith("bp_vision_")
    assert blueprint.width == 1080
    assert blueprint.height == 1920
    assert len(blueprint.video_clips) > 0
    assert blueprint.video_clips[0].energy_level > 0.0
    assert "Vision classified:" in blueprint.video_clips[0].selection_reason


def test_custom_report_ingestion(ingestion_env):
    creative_engine, vision_engine = ingestion_env
    report = vision_engine.analyze_asset("custom_clip_777")
    
    blueprint = creative_engine.ingest_vision_intelligence(
        asset_id="custom_clip_777",
        target_duration=8.0,
        report=report,
    )

    assert blueprint.title == "Vision Edit - custom_clip_777"
    assert len(blueprint.video_clips) >= 1
    assert blueprint.audio_clips[0].asset_id == "custom_clip_777"
