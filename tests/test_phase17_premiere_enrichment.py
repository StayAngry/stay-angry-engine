"""Test suite validating Premiere Pro FCPXML enriched marker, audio track, and color filter exports."""

from pathlib import Path
from sae.creative.engine import CreativeEditingEngine
from sae.database import DatabaseManager
from sae.effects.engine import AdvancedCreativeEngine
from sae.effects.models import CreativeLookType
from sae.events import EventBus
from sae.integrations.engine import EditorIntegrationEngine
from sae.integrations.models import EditorType
from sae.media.manager import MediaAssetManager


def test_fcpxml_contains_markers_audio_and_color_filters(tmp_path: Path):
    db = DatabaseManager(tmp_path / "nle.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "media")
    creative = CreativeEditingEngine(media_mgr)
    effects = AdvancedCreativeEngine()
    editor_engine = EditorIntegrationEngine(media_mgr, export_root=tmp_path / "exports")

    blueprint = creative.generate_reel_blueprint(title="Cinematic Beat Sequence", target_duration=6.0)
    treatment = effects.generate_treatment(blueprint=blueprint, look=CreativeLookType.DARK_CINEMATIC)

    manifest, out_path = editor_engine.export_to_editor(
        blueprint=blueprint,
        treatment=treatment,
        editor_type=EditorType.PREMIERE_PRO,
    )

    assert out_path.exists()
    xml_content = out_path.read_text(encoding="utf-8")

    # Assert sequence structure
    assert "<xmeml version=\"4\">" in xml_content
    assert f"<name>{blueprint.title}</name>" in xml_content

    # Assert enriched timeline markers
    assert "<marker>" in xml_content
    assert "<color>CYAN</color>" in xml_content

    # Assert discrete audio track and video filter
    assert "<audio>" in xml_content
    assert "<filter>" in xml_content
    assert "ColorGrade_" in xml_content
