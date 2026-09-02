"""Test suite validating multimodal synthesis of vision intelligence and audio transients."""

from pathlib import Path
from sae.audio.engine import AudioIntelligenceEngine
from sae.audio.models import AudioAnalysisReport, AudioBeat, BeatStrength
from sae.creative.engine import CreativeEditingEngine
from sae.creative.models import CreativeStyleType, TransitionType
from sae.database import DatabaseManager
from sae.events import EventBus
from sae.media.manager import MediaAssetManager
from sae.vision.models import (
    CameraAngle,
    CameraShotType,
    SceneDecomposition,
    ShotDecomposition,
    VideoAnalysisReport,
)


def test_multimodal_director_synthesizes_shots_and_beats(tmp_path: Path):
    db = DatabaseManager(tmp_path / "director.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "media")
    creative = CreativeEditingEngine(media_mgr)

    # 1. Mock Video Intelligence with distinct high and low energy shots
    shot_high = ShotDecomposition(
        shot_id="shot_action_01",
        start_sec=0.0,
        end_sec=2.0,
        shot_type=CameraShotType.CLOSE_UP,
        camera_angle=CameraAngle.LOW_ANGLE,
        visual_energy=0.95,
        has_impact=True,
    )
    shot_calm = ShotDecomposition(
        shot_id="shot_calm_02",
        start_sec=2.0,
        end_sec=6.0,
        shot_type=CameraShotType.WIDE,
        camera_angle=CameraAngle.EYE_LEVEL,
        visual_energy=0.35,
        has_impact=False,
    )
    mock_video_report = VideoAnalysisReport(
        asset_id="action_sequence.mp4",
        global_visual_energy=0.75,
        scenes=[
            SceneDecomposition(
                scene_id="scene_01",
                start_sec=0.0,
                end_sec=6.0,
                shots=[shot_high, shot_calm],
            )
        ],
    )

    # 2. Mock Audio Intelligence with downbeat and varied transient energies
    mock_audio_report = AudioAnalysisReport(
        asset_id="action_sequence.mp4",
        duration_sec=6.0,
        estimated_bpm=128.0,
        beats=[
            AudioBeat(timestamp_sec=2.0, strength=BeatStrength.DOWNBEAT, confidence=0.98, energy=0.95),
            AudioBeat(timestamp_sec=4.5, strength=BeatStrength.DOWNBEAT, confidence=0.90, energy=0.40),
        ],
    )

    # Assign pre-calculated mock report to the audio engine
    creative.audio_engine.analyze_audio_asset = lambda *args, **kwargs: mock_audio_report

    blueprint = creative.ingest_vision_intelligence(
        asset_id="action_sequence.mp4",
        target_duration=6.0,
        style=CreativeStyleType.DARK_MANHWA,
        report=mock_video_report,
        snap_to_beats=True,
    )

    # Validate output structure and multimodal rules
    assert blueprint.blueprint_id.startswith("bp_vision_")
    assert blueprint.title == "Vision Edit - action_sequence.mp4"
    assert len(blueprint.video_clips) >= 2

    # High energy downbeat correlation
    high_impact_clip = blueprint.video_clips[0]
    assert high_impact_clip.timeline_end_sec == 2.0
    assert high_impact_clip.energy_level >= 0.75
    assert high_impact_clip.transition_in in (TransitionType.WHIP_PAN, TransitionType.HARD_CUT)
    assert "CLOSE_UP" in high_impact_clip.selection_reason
    assert "Beat snapped: True" in high_impact_clip.selection_reason
