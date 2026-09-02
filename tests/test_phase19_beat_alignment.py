"""Test suite validating transient-aligned cut point scheduling in CreativeEditingEngine."""

from pathlib import Path
from sae.audio.models import AudioAnalysisReport, AudioBeat, BeatStrength
from sae.creative.engine import CreativeEditingEngine
from sae.creative.models import CreativeStyleType
from sae.database import DatabaseManager
from sae.events import EventBus
from sae.media.manager import MediaAssetManager


def test_timeline_cuts_snap_to_rhythmic_downbeats(tmp_path: Path):
    db = DatabaseManager(tmp_path / "nle.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "media")
    creative = CreativeEditingEngine(media_mgr)

    # Mock audio transient report with explicit downbeats at 1.8s, 3.6s, 5.4s
    mock_report = AudioAnalysisReport(
        asset_id="music_track_001.wav",
        duration_sec=6.0,
        estimated_bpm=120.0,
        beats=[
            AudioBeat(timestamp_sec=0.5, strength=BeatStrength.STANDARD, confidence=0.8, energy=0.5),
            AudioBeat(timestamp_sec=1.8, strength=BeatStrength.DOWNBEAT, confidence=0.95, energy=0.9),
            AudioBeat(timestamp_sec=2.4, strength=BeatStrength.STANDARD, confidence=0.8, energy=0.5),
            AudioBeat(timestamp_sec=3.6, strength=BeatStrength.DOWNBEAT, confidence=0.95, energy=0.92),
            AudioBeat(timestamp_sec=4.2, strength=BeatStrength.STANDARD, confidence=0.8, energy=0.5),
            AudioBeat(timestamp_sec=5.4, strength=BeatStrength.DOWNBEAT, confidence=0.95, energy=0.94),
        ],
    )

    blueprint = creative.generate_reel_blueprint(
        title="Beat-Synced Montage",
        target_duration=6.0,
        style=CreativeStyleType.DARK_MANHWA,
        audio_report=mock_report,
    )

    # Verify cut points snapped to downbeats
    cut_timestamps = [c.timeline_end_sec for c in blueprint.video_clips]
    assert 1.8 in cut_timestamps
    assert 3.6 in cut_timestamps
    assert 5.4 in cut_timestamps
    assert cut_timestamps[-1] == 6.0
    assert any("Transient beat aligned cut" in c.selection_reason for c in blueprint.video_clips)
