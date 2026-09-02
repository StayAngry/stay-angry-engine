"""DaVinci Resolve NLE export adapter (EDL / CMX 3600 interchange)."""

from datetime import datetime, timezone
from pathlib import Path
import uuid

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
    total_frames = int(round(seconds * fps))
    frames = total_frames % int(fps)
    total_seconds = total_frames // int(fps)
    secs = total_seconds % 60
    total_minutes = total_seconds // 60
    mins = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours:02d}:{mins:02d}:{secs:02d}:{frames:02d}"


class DaVinciResolveAdapter(BaseEditorAdapter):
    """Adapter that compiles EditingBlueprints into DaVinci Resolve CMX 3600 EDLs with CDL color and markers."""

    def detect(self) -> EditorCapabilities:
        return EditorCapabilities(
            editor_type=EditorType.DAVINCI_RESOLVE,
            installed=True,
            version="18.6",
            supports_multitrack=True,
            supports_native_color=True,
            supports_keyframes=True,
            supports_markers=True,
        )

    def translate_blueprint(
        self,
        blueprint: EditingBlueprint,
        treatment: CreativeTreatmentBlueprint | None = None,
        asset_map: dict[str, str] | None = None,
    ) -> EditorProjectManifest:
        fps = getattr(blueprint, "fps", 24.0) or 24.0
        clips = getattr(blueprint, "video_clips", getattr(blueprint, "clips", getattr(blueprint, "timeline", [])))
        v_mappings: list[ExportedClipMapping] = []

        for idx, clip in enumerate(clips):
            clip_id = getattr(clip, "clip_id", f"clip_{idx:02d}")
            src_path = (asset_map or {}).get(clip_id, f"assets/{clip_id}.mp4")
            v_mappings.append(
                ExportedClipMapping(
                    sae_clip_id=clip_id,
                    editor_item_id=f"v_{idx}",
                    track_index=1,
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
                        marker_id=f"marker_{uuid.uuid4().hex[:6]}",
                        timestamp_sec=beat,
                        name="Beat Drop",
                        color="Cyan",
                        comment="Generated beat sync marker",
                    )
                )

        # Determine ASC-CDL parameters
        cg = getattr(treatment, "color_grade", None) or getattr(blueprint, "color_grade", None)
        slope = "1.0000 1.0000 1.0000"
        offset = "0.0000 0.0000 0.0000"
        power = "1.0000 1.0000 1.0000"
        saturation = "1.0000"

        if cg is not None:
            c_slope = getattr(cg, "slope", None)
            c_offset = getattr(cg, "offset", None)
            c_power = getattr(cg, "power", None)
            c_sat = getattr(cg, "saturation", None)
            if c_slope:
                slope = f"{c_slope[0]:.4f} {c_slope[1]:.4f} {c_slope[2]:.4f}" if isinstance(c_slope, (list, tuple)) else f"{float(c_slope):.4f} {float(c_slope):.4f} {float(c_slope):.4f}"
            if c_offset:
                offset = f"{c_offset[0]:.4f} {c_offset[1]:.4f} {c_offset[2]:.4f}" if isinstance(c_offset, (list, tuple)) else f"{float(c_offset):.4f} {float(c_offset):.4f} {float(c_offset):.4f}"
            if c_power:
                power = f"{c_power[0]:.4f} {c_power[1]:.4f} {c_power[2]:.4f}" if isinstance(c_power, (list, tuple)) else f"{float(c_power):.4f} {float(c_power):.4f} {float(c_power):.4f}"
            if c_sat is not None:
                saturation = f"{float(c_sat):.4f}"

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
            edl_lines.append(f"* ASC_SOP ({slope}) ({offset}) ({power})")
            edl_lines.append(f"* ASC_SAT {saturation}")

            clip_markers = [m for m in markers if c.timeline_start_sec <= getattr(m, "timestamp_sec", getattr(m, "time_sec", 0.0)) < c.timeline_end_sec]
            for m in clip_markers:
                m_time = getattr(m, "timestamp_sec", getattr(m, "time_sec", 0.0))
                m_tc = sec_to_timecode(m_time, fps)
                edl_lines.append(f"* MARKER {m.color.upper()} {m_tc} 1 {m.name} : {m.comment}")

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
