"""Base Editor Adapter contract defining capability detection and timeline translation."""

from abc import ABC, abstractmethod
from pathlib import Path
from sae.creative.models import EditingBlueprint
from sae.effects.models import CreativeTreatmentBlueprint
from sae.integrations.models import EditorCapabilities, EditorProjectManifest


class BaseEditorAdapter(ABC):
    @abstractmethod
    def detect(self) -> EditorCapabilities:
        """Detect installation, versions, and capabilities on current system."""
        pass

    @abstractmethod
    def translate_blueprint(
        self,
        blueprint: EditingBlueprint,
        treatment: CreativeTreatmentBlueprint | None = None,
        asset_map: dict[str, str] | None = None
    ) -> EditorProjectManifest:
        """Translate SAE blueprints into structured editor manifest and interchange data."""
        pass

    @abstractmethod
    def export_project(
        self,
        manifest: EditorProjectManifest,
        export_dir: Path
    ) -> Path:
        """Write project interchange file (XML / EDL / JSON) to disk."""
        pass