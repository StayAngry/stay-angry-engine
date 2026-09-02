"""Phase 27 test suite: DaVinci Resolve ASC-CDL color decisions and marker enrichment."""

from pathlib import Path
import pytest

from sae.creative.engine import CreativeEditingEngine
from sae.creative.models import PlatformFormat
from sae.database import DatabaseManager
from sae.effects.color import CinematicColorEngine
from sae.effects.engine import AdvancedCreativeEngine
from sae.effects.models import CreativeLookType
from sae.events import EventBus
from sae.integrations.davinci import DaVinciResolveAdapter
from sae.integrations.models import EditorProjectManifest, EditorType
from sae.media.manager import MediaAssetManager


def test_davinci_edl_embeds_asc_cdl_and_markers(tmp_path: Path):
    db = DatabaseManager(tmp_path / "test.db")
    bus = EventBus()
    media_dir = tmp_path / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    media_mgr = MediaAssetManager(db, bus, media_dir)

    # Ingest a mock video asset
    dummy_video = media_dir / "hero_cut.mp4"
    dummy_video.write_bytes(b"MOCK_VIDEO_DATA")
    media_mgr.register_file(dummy_video)

    creative = CreativeEditingEngine(media_mgr)
    color = CinematicColorEngine()
    effects = AdvancedCreativeEngine(color)
    adapter = DaVinciResolveAdapter()

    blueprint = creative.generate_reel_blueprint(
        title="Cyberpunk Awakening",
        target_duration=10.0,
        format_type=PlatformFormat.VERTICAL_SHORT,
    )
    assert len(blueprint.video_clips) > 0

    treatment = effects.generate_treatment(blueprint=blueprint, look=CreativeLookType.DARK_CINEMATIC)

    manifest = adapter.translate_blueprint(blueprint=blueprint, treatment=treatment)
    assert isinstance(manifest, EditorProjectManifest)
    assert manifest.editor_type == EditorType.DAVINCI_RESOLVE

    edl = manifest.xml_payload
    assert "* ASC_SOP" in edl
    assert "* ASC_SAT" in edl

    exported_file = adapter.export_project(manifest, export_dir=tmp_path / "exports")
    assert exported_file.exists()
    assert exported_file.suffix == ".edl"
    assert "* ASC_SOP" in exported_file.read_text(encoding="utf-8")
