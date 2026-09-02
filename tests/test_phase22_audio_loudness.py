"""Test suite validating LUFS loudness normalization and sidechain ducking filter generation."""

from pathlib import Path
from sae.audio.loudness_engine import AudioLoudnessEngine
from sae.audio.loudness_models import (
    DuckingConfig,
    LoudnessProfile,
    LoudnessTargetStandard,
)
from sae.creative.engine import CreativeEditingEngine
from sae.creative.models import CreativeStyleType
from sae.database import DatabaseManager
from sae.events import EventBus
from sae.media.manager import MediaAssetManager


def test_loudnorm_filter_generation(tmp_path: Path):
    db = DatabaseManager(tmp_path / "loudness.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "media")
    loudness_engine = AudioLoudnessEngine(media_mgr)

    # 1. Test Social Short Standard (-14 LUFS, -1.0 dBTP)
    report = loudness_engine.analyze_and_normalize(
        asset_id="music_track_01.wav",
        profile=loudness_engine.STANDARD_PRESETS[LoudnessTargetStandard.REELS_TIKTOK_SHORT],
        ducking=DuckingConfig(enabled=True),
        input_i_lufs=-22.0,
        input_tp_db=-0.5,
    )

    assert report.asset_id == "music_track_01.wav"
    assert report.output_i_lufs == -14.0
    assert report.output_tp_db == -1.0
    assert report.ducking_applied is True
    assert "loudnorm=I=-14.0:TP=-1.0:LRA=7.0" in report.filter_string
    assert "sidechaincompress=" in report.filter_string


def test_blueprint_loudness_calibration(tmp_path: Path):
    db = DatabaseManager(tmp_path / "loudness_bp.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "media")
    creative = CreativeEditingEngine(media_mgr)
    loudness_engine = AudioLoudnessEngine(media_mgr)

    blueprint = creative.generate_reel_blueprint(
        title="Audio Calibration Test",
        target_duration=6.0,
        style=CreativeStyleType.CINEMATIC_ANIME,
    )

    original_volume = blueprint.audio_clips[0].volume
    calibrated_bp = loudness_engine.apply_loudness_to_blueprint(
        blueprint,
        standard=LoudnessTargetStandard.REELS_TIKTOK_SHORT,
    )

    assert len(calibrated_bp.audio_clips) > 0
    assert calibrated_bp.audio_clips[0].volume <= original_volume
