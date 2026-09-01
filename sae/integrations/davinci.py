"""DaVinci Resolve Adapter generating CMX 3600 standard EDL and Resolve interchange manifests."""

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


def sec_to_timecode(seconds: float, fps: float = 24.0) -> str:
    """Convert floating seconds to standard SMPTE timecode HH:MM:SS:FF."""
    total_frames = int(round(seconds * fps))
    ff = total_frames % int(fps)
    total_seconds = total_frames // int(fps)
    ss = total_seconds % 60
    total_minutes = total_seconds // 60
    mm = total_minutes % 60
    hh = total_minutes // 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


class DaVinciResolveAdapter(BaseEditorAdapter):
    """Adapter for DaVinci Resolve exporting standard CMX 3600 EDLs and markers."""

    def detect(self) -> EditorCapabilities:
        return EditorCapabilities(
            editor_type=EditorType.DAVINCI_RESOLVE,
            is_installed=True,
            supported_formats=["edl", "drp", "xml"],
            supports_speed_ramps=True,
            supports_color_luts=True,
            supports_markers=True,
        )

    def translate_blueprint(
        self,
        blueprint: EditingBlueprint,
        treatment: CreativeTreatmentBlueprint | None = None,
        asset_map: dict[str, str] | None = None,
    ) -> EditorProjectManifest:
        fps = getattr(blueprint, "fps", 24.0) or 24.0
        clips = getattr(blueprint, "clips", getattr(blueprint, "timeline", []))
        v_mappings: list[ExportedClipMapping] = []

        for idx, clip in enumerate(clips):
            clip_id = getattr(clip, "clip_id", f"clip_{idx}")
            src_path = (asset_map or {}).get(clip_id, f"assets/{clip_id}.mp4")
            v_mappings.append(
                ExportedClipMapping(
                    clip_index=idx,
                    sae_clip_id=clip_id,
                    asset_path=src_path,
                    source_in_sec=getattr(clip, "source_in_sec", 0.0),
                    source_out_sec=getattr(clip, "source_out_sec", 3.0),
                    timeline_start_sec=getattr(clip, "timeline_start_sec", 0.0),
                    timeline_end_sec=getattr(clip, "timeline_end_sec", 3.0),
                    speed=getattr(clip, "speed", 1.0),
                )
            )

        markers: list[TimelineMarker] = []
        pacing = getattr(treatment, "pacing", None) if treatment else None
        if pacing:
            for beat in getattr(pacing, "beat_grid_sec", []):
                markers.append(
                    TimelineMarker(
                        time_sec=beat,
                        name="Beat Drop",
                        color="Cyan",
                        comment="Generated beat sync marker",
                    )
                )

        edl_lines = [
            f"TITLE: {blueprint.title}",
            "FCM: NON-DROP FRAME",
            "",
        ]

        for i, c in enumerate(v_mappings, 1):
            src_in = sec_to_timecode(c.source_in_sec, fps)
            src_out = sec_to_timecode(c.source_out_sec, fps)
            rec_in = sec_to_timecode(c.timeline_start_sec, fps)
            rec_out = sec_to_timecode(c.timeline_end_sec, fps)

            edl_lines.append(f"{i:03d}  AX       V     C        {src_in} {src_out} {rec_in} {rec_out}")
            edl_lines.append(f"* FROM CLIP NAME: {c.sae_clip_id}")
            edl_lines.append(f"* SOURCE FILE: {c.asset_path}")
            edl_lines.append("")

        return EditorProjectManifest(
            manifest_id=f"manifest_dv_{uuid.uuid4().hex[:8]}",
            editor_type=EditorType.DAVINCI_RESOLVE,
            project_name=blueprint.title,
            sequence_name=f"{blueprint.title}_Resolve",
            width=blueprint.width,
            height=blueprint.height,
            fps=fps,
            total_duration_sec=blueprint.target_duration_sec,
            video_clips=v_mappings,
            audio_clips=[],
            markers=markers,
            xml_payload="\n".join(edl_lines),
        )

    def export_project(self, manifest: EditorProjectManifest, export_dir: Path) -> Path:
        export_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{manifest.project_name.lower().replace(' ', '_')}_davinci.edl"
        out_path = export_dir / filename
        out_path.write_text(manifest.xml_payload or "", encoding="utf-8")
        return out_path


# Compatibility aliases
DaVinciAdapter = DaVinciResolveAdapter
DavinciAdapter = DaVinciResolveAdapter
