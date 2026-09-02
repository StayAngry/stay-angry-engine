"""Test suite verifying end-to-end autonomous synthesis via DirectorPipeline."""

from pathlib import Path
import pytest

from sae.audio.engine import AudioIntelligenceEngine
from sae.audio.loudness_engine import AudioLoudnessEngine
from sae.creative.engine import CreativeEditingEngine
from sae.creative.models import CreativeStyleType, PlatformFormat
from sae.database import DatabaseManager
from sae.effects.color import CinematicColorEngine
from sae.effects.engine import AdvancedCreativeEngine
from sae.effects.typography_engine import KineticTypographyEngine
from sae.events import EventBus
from sae.media.manager import MediaAssetManager
from sae.orchestrator.engine import DirectorPipeline
from sae.render.backend import MockMediaBackend
from sae.render.engine import MediaProcessingEngine
from sae.vision.engine import AdvancedVideoIntelligenceEngine


@pytest.mark.asyncio
async def test_director_pipeline_produces_manifest_and_render(tmp_path: Path):
    db = DatabaseManager(tmp_path / "director.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "media")

    creative = CreativeEditingEngine(media_mgr)
    vision = AdvancedVideoIntelligenceEngine(media_mgr)
    audio = AudioIntelligenceEngine(media_mgr)
    loudness = AudioLoudnessEngine(media_mgr)
    color_engine = CinematicColorEngine()
    effects = AdvancedCreativeEngine(color_engine)
    typography = KineticTypographyEngine(media_mgr, output_dir=tmp_path / "subs")

    mock_backend = MockMediaBackend(output_dir=tmp_path / "output")
    render_engine = MediaProcessingEngine(workspace_root=tmp_path, backend=mock_backend)

    director = DirectorPipeline(
        media_manager=media_mgr,
        creative_engine=creative,
        vision_engine=vision,
        audio_engine=audio,
        loudness_engine=loudness,
        effects_engine=effects,
        typography_engine=typography,
        render_engine=render_engine,
    )

    manifest = await director.produce_reel(
        title="Solo Leveling Anthem",
        target_duration=5.0,
        style=CreativeStyleType.DARK_MANHWA,
        format_type=PlatformFormat.VERTICAL_SHORT,
        sample_transcript=["AWAKEN", "THE", "SHADOW", "MONARCH"],
    )

    assert manifest.pipeline_id.startswith("dir_")
    assert manifest.blueprint.title == "Solo Leveling Anthem"
    assert manifest.loudness_calibrated is True
    assert manifest.total_clips > 0
    assert manifest.subtitle_track_path is not None
    assert manifest.subtitle_track_path.exists()
    assert manifest.rendered_video_path.exists()
