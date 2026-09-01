"""Comprehensive Phase 14 test suite validating editor detection, timeline mapping, XML export, and dry-run modes."""

import pytest
from pathlib import Path
from sae.creative.engine import CreativeEditingEngine
from sae.database import DatabaseManager
from sae.effects.engine import AdvancedCreativeEngine
from sae.events import EventBus
from sae.integrations.engine import EditorIntegrationEngine
from sae.integrations.models import EditorType
from sae.media.manager import MediaAssetManager


@pytest.fixture
def editor_env(tmp_path: Path):
    db = DatabaseManager(tmp_path / "test_sae_editor.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "cache")
    creative_engine = CreativeEditingEngine(media_mgr)
    effects_engine = AdvancedCreativeEngine()
    editor_engine = EditorIntegrationEngine(media_mgr, tmp_path / "projects")
    return editor_engine, creative_engine, effects_engine


def test_editor_detection_does_not_crash(editor_env):
    editor_engine, _, _ = editor_env
    caps = editor_engine.detect_all()

    assert EditorType.PREMIERE_PRO in caps
    assert EditorType.DAVINCI_RESOLVE in caps
    assert caps[EditorType.PREMIERE_PRO].supports_multitrack is True


def test_premiere_fcpxml_export(editor_env):
    editor_engine, creative_engine, effects_engine = editor_env
    bp = creative_engine.generate_reel_blueprint("Premiere Action Test", target_duration=12.0)
    treatment = effects_engine.generate_treatment(bp)

    manifest, out_path = editor_engine.export_to_editor(
        blueprint=bp,
        treatment=treatment,
        editor_type=EditorType.PREMIERE_PRO,
        dry_run=False
    )

    assert out_path is not None
    assert out_path.exists()
    assert out_path.suffix == ".xml"
    
    xml_data = out_path.read_text(encoding="utf-8")
    assert "<xmeml version=\"4\">" in xml_data
    assert "<sequence" in xml_data
    assert len(manifest.video_clips) >= 3
    assert len(manifest.markers) >= 3


def test_davinci_export_and_dry_run_mode(editor_env):
    editor_engine, creative_engine, effects_engine = editor_env
    bp = creative_engine.generate_reel_blueprint("Resolve Test", target_duration=10.0)

    manifest, out_path = editor_engine.export_to_editor(
        blueprint=bp,
        treatment=None,
        editor_type=EditorType.DAVINCI_RESOLVE,
        dry_run=True
    )

    assert out_path is None  # Dry-run does not write to disk
    assert manifest.editor_type == EditorType.DAVINCI_RESOLVE
    assert manifest.total_duration_sec == 10.0