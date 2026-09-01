"""Adobe Premiere Pro Adapter translating SAE blueprints to FCPXML/Premiere-compatible project structures."""

import os
import shutil
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


class PremiereAdapter(BaseEditorAdapter):
    def detect(self) -> EditorCapabilities:
        # Check standard Windows paths for Adobe Premiere Pro
        prog_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        premiere_dir = Path(prog_files) / "Adobe"
        is_installed = False
        version = None

        if premiere_dir.exists():
            for p in premiere_dir.glob("Adobe Premiere Pro*"):
                is_installed = True
                version = p.name
                break

        return EditorCapabilities(
            editor_type=EditorType.PREMIERE_PRO,
            installed=is_installed,
            version=version or "Not Installed",
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
        a_mappings: list[ExportedClipMapping] = []
        markers: list[TimelineMarker] = []

        # 1. Translate Video Clips
        for c in blueprint.video_clips:
            v_mappings.append(
                ExportedClipMapping(
                    sae_clip_id=c.clip_id,
                    editor_item_id=f"pr_vid_{c.clip_id}",
                    asset_path=resolved_map.get(c.asset_id, f"assets/{c.asset_id}.mp4"),
                    track_index=c.track_index,
                    source_in_sec=c.source_in_sec,
                    source_out_sec=c.source_out_sec,
                    timeline_start_sec=c.timeline_start_sec,
                    timeline_end_sec=c.timeline_end_sec,
                    speed=c.speed
                )
            )
            # Add beat/cut markers
            markers.append(
                TimelineMarker(
                    marker_id=f"mark_{c.clip_id}",
                    timestamp_sec=c.timeline_start_sec,
                    name=f"Cut: {c.clip_id}",
                    comment=c.selection_reason,
                    color="CYAN"
                )
            )

        # 2. Translate Audio Tracks
        for a in blueprint.audio_clips:
            a_mappings.append(
                ExportedClipMapping(
                    sae_clip_id=a.audio_clip_id,
                    editor_item_id=f"pr_aud_{a.audio_clip_id}",
                    asset_path=resolved_map.get(a.asset_id, f"assets/{a.asset_id}.wav"),
                    track_index=a.track_index,
                    source_in_sec=a.source_in_sec,
                    source_out_sec=a.timeline_end_sec - a.timeline_start_sec,
                    timeline_start_sec=a.timeline_start_sec,
                    timeline_end_sec=a.timeline_end_sec,
                    speed=1.0
                )
            )

        # 3. Add Treatment Impact Markers
        if treatment:
            for eff in treatment.effects_stack:
                if eff.category.value == "MOTION":
                    markers.append(
                        TimelineMarker(
                            marker_id=f"mark_eff_{eff.effect_id}",
                            timestamp_sec=eff.start_sec,
                            name=f"Impact: {eff.name}",
                            comment=eff.reason,
                            color="RED"
                        )
                    )

        # 4. Generate XML payload
        xml_content = self._generate_fcpxml(blueprint, v_mappings, markers)

        return EditorProjectManifest(
            manifest_id=f"manifest_pr_{uuid.uuid4().hex[:8]}",
            editor_type=EditorType.PREMIERE_PRO,
            project_name=blueprint.title,
            sequence_name=f"{blueprint.title}_Sequence",
            width=blueprint.width,
            height=blueprint.height,
            fps=blueprint.fps,
            total_duration_sec=blueprint.target_duration_sec,
            video_clips=v_mappings,
            audio_clips=a_mappings,
            markers=markers,
            xml_payload=xml_content
        )

    def _generate_fcpxml(self, bp: EditingBlueprint, clips: list[ExportedClipMapping], markers: list[TimelineMarker]) -> str:
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!DOCTYPE xmeml>',
            '<xmeml version="4">',
            f'  <sequence id="{bp.blueprint_id}">',
            f'    <name>{bp.title}</name>',
            f'    <duration>{int(bp.target_duration_sec * bp.fps)}</duration>',
            '    <rate>',
            f'      <timebase>{int(bp.fps)}</timebase>',
            '    </rate>',
            '    <media>',
            '      <video>',
            '        <track>'
        ]

        for c in clips:
            start_frame = int(c.timeline_start_sec * bp.fps)
            end_frame = int(c.timeline_end_sec * bp.fps)
            lines.extend([
                '          <clipitem>',
                f'            <name>{c.sae_clip_id}</name>',
                f'            <start>{start_frame}</start>',
                f'            <end>{end_frame}</end>',
                f'            <in>{int(c.source_in_sec * bp.fps)}</in>',
                f'            <out>{int(c.source_out_sec * bp.fps)}</out>',
                '            <file>',
                f'              <pathurl>{c.asset_path}</pathurl>',
                '            </file>',
                '          </clipitem>'
            ])

        lines.extend([
            '        </track>',
            '      </video>',
            '    </media>',
            '  </sequence>',
            '</xmeml>'
        ])
        return "\n".join(lines)

    def export_project(self, manifest: EditorProjectManifest, export_dir: Path) -> Path:
        export_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{manifest.project_name.lower().replace(' ', '_')}_premiere.xml"
        out_path = export_dir / filename
        out_path.write_text(manifest.xml_payload or "", encoding="utf-8")
        return out_path