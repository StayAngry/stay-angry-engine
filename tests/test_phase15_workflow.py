"""Comprehensive Phase 15 test suite validating natural language parsing, state coordination, and end-to-end autonomous execution."""

import pytest
from pathlib import Path
from sae.creative.engine import CreativeEditingEngine
from sae.database import DatabaseManager
from sae.effects.engine import AdvancedCreativeEngine
from sae.events import EventBus
from sae.integrations.engine import EditorIntegrationEngine
from sae.media.manager import MediaAssetManager
from sae.orchestrator.models import AutonomyLevel, WorkflowState
from sae.orchestrator.workflow import AutonomousCreativeWorkflow
from sae.render.engine import MediaProcessingEngine
from sae.vision.engine import AdvancedVideoIntelligenceEngine


@pytest.fixture
def workflow_env(tmp_path: Path):
    db = DatabaseManager(tmp_path / "test_sae_wf.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "cache")
    creative_eng = CreativeEditingEngine(media_mgr)
    vision_eng = AdvancedVideoIntelligenceEngine(media_mgr)
    effects_eng = AdvancedCreativeEngine()
    render_eng = MediaProcessingEngine(tmp_path)
    editor_eng = EditorIntegrationEngine(media_mgr, tmp_path / "projects")

    workflow = AutonomousCreativeWorkflow(
        media_manager=media_mgr,
        creative_engine=creative_eng,
        vision_engine=vision_eng,
        effects_engine=effects_eng,
        render_engine=render_eng,
        editor_engine=editor_eng
    )
    return workflow


@pytest.mark.asyncio
async def test_autonomous_workflow_dry_run_execution(workflow_env):
    orchestrator = workflow_env
    prompt = "Make me a 15s dark cinematic manhwa reel with no shake and export to premiere"

    res = await orchestrator.execute(prompt, autonomy_level=AutonomyLevel.LEVEL_2_AUTONOMOUS, dry_run=True)

    assert res.state == WorkflowState.COMPLETED
    assert res.brief.target_duration_sec == 15.0
    assert res.brief.style_keyword == "DARK_MANHWA"
    assert res.brief.allow_shake is False
    assert res.brief.export_editor == "PREMIERE_PRO"
    assert len(res.progress_log) >= 5


@pytest.mark.asyncio
async def test_autonomous_workflow_full_execution_generates_artifacts(workflow_env):
    orchestrator = workflow_env
    prompt = "Create a 12s anime action reel"

    res = await orchestrator.execute(prompt, autonomy_level=AutonomyLevel.LEVEL_2_AUTONOMOUS, dry_run=False)

    assert res.state == WorkflowState.COMPLETED
    assert res.rendered_path is not None
    assert Path(res.rendered_path).exists()
    assert res.editor_export_path is not None
    assert Path(res.editor_export_path).exists()
    assert res.quality_score > 90.0