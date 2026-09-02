"""Phase 29 test suite: AutonomousCreativeWorkflow end-to-end multimodal execution."""

from pathlib import Path
import pytest

from sae.audio.engine import AudioIntelligenceEngine
from sae.audio.loudness_engine import AudioLoudnessEngine
from sae.creative.engine import CreativeEditingEngine
from sae.database import DatabaseManager
from sae.effects.color import CinematicColorEngine
from sae.effects.engine import AdvancedCreativeEngine
from sae.effects.typography_engine import KineticTypographyEngine
from sae.events import EventBus
from sae.integrations.engine import EditorIntegrationEngine
from sae.media.manager import MediaAssetManager
from sae.orchestrator.models import AutonomyLevel, WorkflowState
from sae.orchestrator.workflow import AutonomousCreativeWorkflow
from sae.render.backend import MockMediaBackend
from sae.render.engine import MediaProcessingEngine
from sae.vision.engine import AdvancedVideoIntelligenceEngine


@pytest.fixture
def multimodal_workflow_env(tmp_path: Path):
    db = DatabaseManager(tmp_path / "test_phase29.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "media")
    audio_eng = AudioIntelligenceEngine(media_mgr)
    creative_eng = CreativeEditingEngine(media_mgr, audio_engine=audio_eng)
    vision_eng = AdvancedVideoIntelligenceEngine(media_mgr)
    color_eng = CinematicColorEngine()
    effects_eng = AdvancedCreativeEngine(color_eng)

    mock_backend = MockMediaBackend(output_dir=tmp_path / "rendered")
    render_eng = MediaProcessingEngine(workspace_root=tmp_path, backend=mock_backend)
    editor_eng = EditorIntegrationEngine(media_mgr, tmp_path / "editor_exports")
    loudness_eng = AudioLoudnessEngine(media_mgr)
    typography_eng = KineticTypographyEngine(media_mgr, output_dir=tmp_path / "subtitles")

    workflow = AutonomousCreativeWorkflow(
        media_manager=media_mgr,
        creative_engine=creative_eng,
        vision_engine=vision_eng,
        effects_engine=effects_eng,
        render_engine=render_eng,
        editor_engine=editor_eng,
        loudness_engine=loudness_eng,
        typography_engine=typography_eng,
    )
    return workflow


@pytest.mark.asyncio
async def test_autonomous_workflow_multimodal_execution(multimodal_workflow_env):
    prompt = "Produce an 8s dark manhwa action reel with kinetic typography and export to davinci"
    result = await multimodal_workflow_env.execute(
        command=prompt,
        autonomy_level=AutonomyLevel.LEVEL_2_AUTONOMOUS,
        dry_run=False,
    )

    assert result.state == WorkflowState.COMPLETED
    assert result.rendered_path is not None
    assert result.editor_export_path is not None
    assert "davinci" in result.editor_export_path.lower()
    assert result.loudness_calibrated is True
    print("LOGS:", result.progress_log)
    assert result.subtitle_track_path is not None
    assert Path(result.subtitle_track_path).exists()