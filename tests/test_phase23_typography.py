"""Test suite validating KineticTypographyEngine script compilation and beat snapping."""

from pathlib import Path
from sae.audio.models import AudioAnalysisReport, AudioBeat, BeatStrength
from sae.creative.engine import CreativeEditingEngine
from sae.creative.models import CreativeStyleType
from sae.database import DatabaseManager
from sae.effects.typography_engine import KineticTypographyEngine
from sae.effects.typography_models import (
    SubtitleAnimationStyle,
    SubtitleSegment,
    TypographyConfig,
    WordTiming,
)
from sae.events import EventBus
from sae.media.manager import MediaAssetManager


def test_kinetic_ass_generation_and_beat_alignment(tmp_path: Path):
    db = DatabaseManager(tmp_path / "typo.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "media")
    creative = CreativeEditingEngine(media_mgr)
    typo_engine = KineticTypographyEngine(media_mgr, output_dir=tmp_path / "subs")

    blueprint = creative.generate_reel_blueprint(
        title="Kinetic Reel",
        target_duration=5.0,
        style=CreativeStyleType.DARK_MANHWA,
    )

    # Audio report containing a downbeat near the word "POWER" at 1.0s
    audio_report = AudioAnalysisReport(
        asset_id="audio_test.wav",
        duration_sec=5.0,
        estimated_bpm=120.0,
        beats=[
            AudioBeat(timestamp_sec=1.0, strength=BeatStrength.DOWNBEAT, confidence=0.98, energy=0.95),
        ],
    )

    segments = [
        SubtitleSegment(
            segment_id="seg_01",
            start_sec=0.2,
            end_sec=2.5,
            text="Unleash the power within",
            words=[
                WordTiming(word="Unleash", start_sec=0.2, end_sec=0.6),
                WordTiming(word="the", start_sec=0.6, end_sec=0.9),
                WordTiming(word="power", start_sec=1.05, end_sec=1.7),  # close to 1.0s downbeat
                WordTiming(word="within", start_sec=1.7, end_sec=2.4),
            ],
        )
    ]

    config = TypographyConfig(
        animation_style=SubtitleAnimationStyle.POP_IN,
        all_caps=True,
    )

    ass_path = typo_engine.export_subtitles(
        segments=segments,
        blueprint=blueprint,
        config=config,
        audio_report=audio_report,
    )

    assert ass_path.exists()
    content = ass_path.read_text(encoding="utf-8")

    # Verify ASS header and metadata
    assert "[Script Info]" in content
    assert f"PlayResX: {blueprint.width}" in content
    assert f"PlayResY: {blueprint.height}" in content

    # Verify beat snap and emphasis tag injection
    assert segments[0].words[2].is_emphasized is True
    assert segments[0].words[2].start_sec == 1.0
    assert "\\fscx115\\fscy115" in content
    assert "POWER" in content
