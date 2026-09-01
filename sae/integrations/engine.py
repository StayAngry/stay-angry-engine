"""Central Editor Integration Engine coordinating adapters, dry-runs, and project exports."""

from pathlib import Path
from sae.creative.models import EditingBlueprint
from sae.effects.models import CreativeTreatmentBlueprint
from sae.integrations.base import BaseEditorAdapter
from sae.integrations.davinci import DaVinciAdapter
from sae.integrations.models import EditorCapabilities, EditorProjectManifest, EditorType
from sae.integrations.premiere import PremiereAdapter
from sae.media.manager import MediaAssetManager


class EditorIntegrationEngine:
    def __init__(self, media_manager: MediaAssetManager, export_root: Path):
        self.media_manager = media_manager
        self.export_root = export_root.resolve()
        self.export_root.mkdir(parents=True, exist_ok=True)
        self.adapters: dict[EditorType, BaseEditorAdapter] = {
            EditorType.PREMIERE_PRO: PremiereAdapter(),
            EditorType.DAVINCI_RESOLVE: DaVinciAdapter()
        }

    def detect_all(self) -> dict[EditorType, EditorCapabilities]:
        return {etype: adapter.detect() for etype, adapter in self.adapters.items()}

    def export_to_editor(
        self,
        blueprint: EditingBlueprint,
        treatment: CreativeTreatmentBlueprint | None = None,
        editor_type: EditorType = EditorType.PREMIERE_PRO,
        dry_run: bool = False
    ) -> tuple[EditorProjectManifest, Path | None]:
        adapter = self.adapters.get(editor_type)
        if not adapter:
            raise ValueError(f"Unsupported editor target: {editor_type}")

        # Resolve asset filesystem paths
        asset_map = {a.asset_id: a.file_path for a in self.media_manager.list_assets()}
        manifest = adapter.translate_blueprint(blueprint, treatment=treatment, asset_map=asset_map)

        if dry_run:
            return manifest, None

        out_path = adapter.export_project(manifest, self.export_root)
        return manifest, out_path