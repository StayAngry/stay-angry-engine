"""Test suite validating TimelinePreviewEngine and frame caching."""

import pytest
from pathlib import Path
from sae.creative.engine import CreativeEditingEngine
from sae.creative.models import CreativeStyleType
from sae.database import DatabaseManager
from sae.events import EventBus
from sae.media.manager import MediaAssetManager
from sae.render.preview_engine import TimelinePreviewEngine


@pytest.mark.asyncio
async def test_preview_engine_resolves_and_caches_frames(tmp_path: Path):
    db = DatabaseManager(tmp_path / "preview.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "media")
    creative = CreativeEditingEngine(media_mgr)

    # Generate test blueprint with multiple cuts
    blueprint = creative.generate_reel_blueprint(
        title="Preview Test",
        target_duration=7.5,
        style=CreativeStyleType.CINEMATIC_ANIME,
    )

    cache_dir = tmp_path / "preview_cache"
    preview_engine = TimelinePreviewEngine(media_manager=media_mgr, cache_dir=cache_dir)

    # 1. Test Single Frame Extraction & Active Clip Mapping
    frame_at_1s = await preview_engine.extract_preview_frame(blueprint, timestamp_sec=1.0)
    assert frame_at_1s.timestamp_sec == 1.0
    assert frame_at_1s.active_clip_id is not None
    assert frame_at_1s.cached_path is not None
    assert frame_at_1s.cached_path.exists()

    # 2. Test Cache Hit (Memory and Deterministic Key)
    frame_repeat = await preview_engine.extract_preview_frame(blueprint, timestamp_sec=1.0)
    assert frame_repeat.cached_path == frame_at_1s.cached_path

    # 3. Test Precache Cut Points Manifest
    manifest = await preview_engine.precache_cut_points(blueprint)
    assert manifest.blueprint_id == blueprint.blueprint_id
    assert manifest.total_cached_frames == len(manifest.cut_point_timestamps)
    assert 0.0 in manifest.cut_point_timestamps
    assert 7.5 in manifest.cut_point_timestamps

    # Verify manifest JSON persisted
    manifest_file = cache_dir / f"manifest_{blueprint.blueprint_id}.json"
    assert manifest_file.exists()
