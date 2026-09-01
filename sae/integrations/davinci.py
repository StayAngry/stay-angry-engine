"""DaVinci Resolve Adapter translating SAE blueprints to DaVinci-compatible XML/EDL interchange formats."""

import os
import uuid
from pathlib import Path
from sae.creative.models import EditingBlueprint
from sae.effects.models import CreativeTreatmentBlueprint
from sae.integrations.base import BaseEditorAdapter
from sae.integrations.models import (
    EditorCapabilities,
    EditorProjectManifest,
    EditorType,
    ExportedClipMapping,
    TimelineMarker,
)


class DaVinciAdapter(BaseEditorAdapter):
    def detect(self) -> EditorCapabilities:
        prog_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        resolve_path = Path(prog_files) / "Blackmagic Design" / "DaVinci Resolve"
        is_installed = resolve_path.exists()

        return EditorCapabilities(
            editor_type=EditorType.DAVINCI_RESOLVE,
            installed=is_installed,
            version="DaVinci Resolve Studio / Free" if is_installed else "Not Installed",
            supports_multitrack=True,
            supports_native_color=True,
            supports_keyframes=True,
            supports_markers=True
        )

    def translate_blueprint(
        self,
        blueprint: EditingBlueprint,
        treatment: CreativeTreatmentBlueprint | None = None,
        asset_map: dict[str, str] | None = None
    ) -> EditorProjectManifest:
        resolved_map = asset_map or {}
        v_mappings: list[ExportedClipMapping] = []
        markers: list[TimelineMarker] = []

        for c in blueprint.video_clips:
            v_mappings.append(
                ExportedClipMapping(
                    sae_clip_id=c.clip_id,
                    editor_item_id=f"dv_clip_{c.clip_id}",
                    asset_path=resolved_map.get(c.asset_id, f"assets/{c.asset_id}.mp4"),
                    track_index=c.track_index,
                    source_in_sec=c.source_in_sec,
                    source_out_sec=c.source_out_sec,
                    timeline_start_sec=c.timeline_start_sec,
                    timeline_end_sec=c.timeline_end_sec,
                    speed=c.speed
                )
            )

        # Generate simple EDL/XML interchange structure
        edl_lines = [
            f"TITLE: {blueprint.title}",
            "FCM: NON-DROP FRAME"
        ]
        for i, c in enumerate(v_mappings, 1):
            edl_lines.append(f"{i:03d}  AX       V     C        00:00:00:00 00:00:03:00 00:00:00:00 00:00:03:00")
            edl_lines.append(f"* FROM CLIP NAME: {c.sae_clip_id}")

        return EditorProjectManifest(
            manifest_id=f"manifest_dv_{uuid.uuid4().hex[:8]}",
            editor_type=EditorType.DAVINCI_RESOLVE,
            project_name=blueprint.title,
            sequence_name=f"{blueprint.title}_Resolve",
            width=blueprint.width,
            height=blueprint.height,
            fps=blueprint.fps,
            total_duration_sec=blueprint.target_duration_sec,
            video_clips=v_mappings,
            audio_clips=[],
            markers=markers,
            xml_payload="\n".join(edl_lines)
        )

    def export_project(self, manifest: EditorProjectManifest, export_dir: Path) -> Path:
        export_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{manifest.project_name.lower().replace(' ', '_')}_davinci.edl"
        out_path = export_dir / filename
        out_path.write_text(manifest.xml_payload or "", encoding="utf-8")
        return out_path