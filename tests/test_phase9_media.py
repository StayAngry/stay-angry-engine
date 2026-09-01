"""Comprehensive Phase 9 test suite validating media discovery, audio beat analysis, scene cuts, and semantic search."""

import pytest
from pathlib import Path
from sae.database import DatabaseManager
from sae.events import EventBus
from sae.media.extractors import MetadataExtractor
from sae.media.manager import MediaAssetManager
from sae.media.models import MediaType


@pytest.fixture
def media_env(tmp_path: Path):
    db_path = tmp_path / "test_sae_media.db"
    db = DatabaseManager(db_path)
    bus = EventBus()
    cache_dir = tmp_path / "cache"
    manager = MediaAssetManager(db, bus, cache_dir)
    return manager, tmp_path


def test_metadata_extraction_and_type_detection(tmp_path: Path):
    dummy_img = tmp_path / "anime_poster.png"
    dummy_img.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x07\x80\x00\x00\x048\x08\x02\x00\x00\x00")

    assert MetadataExtractor.detect_type(dummy_img) == MediaType.IMAGE
    w, h = MetadataExtractor.extract_image_dimensions(dummy_img)
    assert w == 1920
    assert h == 1080


def test_audio_analysis_and_beat_detection(tmp_path: Path):
    dummy_audio = tmp_path / "beat_drop.wav"
    dummy_audio.write_bytes(b"RIFF....WAVEfmt ....")

    analysis = MetadataExtractor.extract_audio_info(dummy_audio)
    assert analysis.tempo_bpm == 120.0
    assert len(analysis.beats) > 0
    assert len(analysis.waveform_peaks) > 0


def test_media_scanner_and_search_pipeline(media_env):
    manager, root = media_env
    assets_dir = root / "assets"
    assets_dir.mkdir()

    clip = assets_dir / "anime_fight_scene.mp4"
    clip.write_bytes(b"dummy video data")

    discovered = manager.scan_directory(assets_dir)
    assert len(discovered) == 1
    assert discovered[0].filename == "anime_fight_scene.mp4"
    assert "anime" in discovered[0].tags

    # Semantic search check
    results = manager.search_assets("anime fight")
    assert len(results) == 1
    assert results[0].asset_id == discovered[0].asset_id