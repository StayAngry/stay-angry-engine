"""Adobe Premiere Pro FCPXML timeline integration adapter."""

import os
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
            supports_markers=True,
        )

    def translate_blueprint(
        self,
        blueprint: EditingBlueprint,
        treatment: CreativeTreatmentBlueprint | None = None,
        asset_map: dict[str, Path] | None = None,
    ) -> EditorProjectManifest:
        resolved_map = asset_map or {}
        v_mappings: list[ExportedClipMapping] = []
        a_mappings: list[ExportedClipMapping] = []
        markers: list[TimelineMarker] = []

        # 1. Translate Video Tracks
        for c in blueprint.video_clips:
            resolved_p = resolved_map.get(c.asset_id, Path(f"assets/{c.asset_id}"))
            v_mappings.append(
                ExportedClipMapping(
                    sae_clip_id=c.clip_id,
                    editor_item_id=f"pr_vid_{c.clip_id}",
                    asset_path=str(resolved_p.as_posix()),
                    track_index=c.track_index,
                    source_in_sec=c.source_in_sec,
                    source_out_sec=c.source_out_sec,
                    timeline_start_sec=c.timeline_start_sec,
                    timeline_end_sec=c.timeline_end_sec,
                    speed=c.speed,
                )
            )
            # Add beat/cut markers
            markers.append(
                TimelineMarker(
                    marker_id=f"mark_{c.clip_id}",
                    timestamp_sec=c.timeline_start_sec,
                    name=f"Cut: {c.clip_id}",
                    comment=c.selection_reason,
                    color="CYAN",
                )
            )

        # 2. Translate Audio Tracks
        for a in blueprint.audio_clips:
            resolved_a = resolved_map.get(a.asset_id, Path(f"assets/{a.asset_id}.wav"))
            a_mappings.append(
                ExportedClipMapping(
                    sae_clip_id=a.audio_clip_id,
                    editor_item_id=f"pr_aud_{a.audio_clip_id}",
                    asset_path=str(resolved_a.as_posix()),
                    track_index=a.track_index,
                    source_in_sec=a.source_in_sec,
                    source_out_sec=a.timeline_end_sec - a.timeline_start_sec,
                    timeline_start_sec=a.timeline_start_sec,
                    timeline_end_sec=a.timeline_end_sec,
                    speed=1.0,
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
                            color="MAGENTA",
                        )
                    )

        xml_payload = self._generate_fcpxml(blueprint, v_mappings, a_mappings, markers, treatment)

        return EditorProjectManifest(
            manifest_id=f"manifest_pr_{blueprint.blueprint_id[3:]}",
            editor_type=EditorType.PREMIERE_PRO,
            blueprint_id=blueprint.blueprint_id,
            project_name=blueprint.title,
            sequence_name=blueprint.title,
            width=blueprint.width,
            height=blueprint.height,
            fps=blueprint.fps,
            total_duration_sec=blueprint.target_duration_sec,
            video_clips=v_mappings,
            audio_clips=a_mappings,
            markers=markers,
            xml_payload=xml_payload,
        )

    def _generate_fcpxml(
        self,
        bp: EditingBlueprint,
        v_clips: list[ExportedClipMapping],
        a_clips: list[ExportedClipMapping],
        markers: list[TimelineMarker],
        treatment: CreativeTreatmentBlueprint | None = None,
    ) -> str:
        fps_int = int(bp.fps)
        total_duration_frames = int(bp.target_duration_sec * bp.fps)

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!DOCTYPE xmeml>',
            '<xmeml version="4">',
            f'  <sequence id="{bp.blueprint_id}">',
            f'    <name>{bp.title}</name>',
            f'    <duration>{total_duration_frames}</duration>',
            '    <rate>',
            f'      <timebase>{fps_int}</timebase>',
            '      <ntsc>FALSE</ntsc>',
            '    </rate>',
            '    <media>',
            '      <video>',
            '        <format>',
            '          <samplecharacteristics>',
            f'            <width>{bp.width}</width>',
            f'            <height>{bp.height}</height>',
            '          </samplecharacteristics>',
            '        </format>',
            '        <track>',
        ]

        # Video Clips
        for c in v_clips:
            start_frame = int(c.timeline_start_sec * bp.fps)
            end_frame = int(c.timeline_end_sec * bp.fps)
            in_frame = int(c.source_in_sec * bp.fps)
            out_frame = int(c.source_out_sec * bp.fps)
            lines.extend([
                '          <clipitem>',
                f'            <name>{c.sae_clip_id}</name>',
                f'            <start>{start_frame}</start>',
                f'            <end>{end_frame}</end>',
                f'            <in>{in_frame}</in>',
                f'            <out>{out_frame}</out>',
                '            <file>',
                f'              <pathurl>{c.asset_path}</pathurl>',
                '            </file>',
            ])

            # Color LUT filter if provided in blueprint
            if bp.color_grade:
                lines.extend([
                    '            <filter>',
                    '              <effect>',
                    f'                <name>ColorGrade_{bp.color_grade.profile_name}</name>',
                    '                <parameter>',
                    '                  <name>Contrast</name>',
                    f'                  <value>{bp.color_grade.contrast}</value>',
                    '                </parameter>',
                    '                <parameter>',
                    '                  <name>Saturation</name>',
                    f'                  <value>{bp.color_grade.saturation}</value>',
                    '                </parameter>',
                    '              </effect>',
                    '            </filter>',
                ])
            lines.append('          </clipitem>')

        lines.extend([
            '        </track>',
            '      </video>',
            '      <audio>',
            '        <track>',
        ])

        # Audio Clips
        for a in a_clips:
            a_start = int(a.timeline_start_sec * bp.fps)
            a_end = int(a.timeline_end_sec * bp.fps)
            a_in = int(a.source_in_sec * bp.fps)
            a_out = int(a.source_out_sec * bp.fps)
            lines.extend([
                '          <clipitem>',
                f'            <name>{a.sae_clip_id}</name>',
                f'            <start>{a_start}</start>',
                f'            <end>{a_end}</end>',
                f'            <in>{a_in}</in>',
                f'            <out>{a_out}</out>',
                '            <file>',
                f'              <pathurl>{a.asset_path}</pathurl>',
                '            </file>',
                '          </clipitem>',
            ])

        lines.extend([
            '        </track>',
            '      </audio>',
            '    </media>',
        ])

        # Sequence Timeline Markers
        for m in markers:
            m_frame = int(m.timestamp_sec * bp.fps)
            lines.extend([
                '    <marker>',
                f'      <name>{m.name}</name>',
                f'      <comment>{m.comment}</comment>',
                f'      <in>{m_frame}</in>',
                f'      <out>{m_frame}</out>',
                f'      <color>{m.color}</color>',
                '    </marker>',
            ])

        lines.extend([
            '  </sequence>',
            '</xmeml>',
        ])

        return "\n".join(lines)

    def export_project(self, manifest: EditorProjectManifest, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"{manifest.manifest_id}.xml"
        file_path.write_text(manifest.xml_payload or "", encoding="utf-8")
        return file_path
