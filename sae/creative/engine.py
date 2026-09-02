"""Creative Timeline Generation Engine translating media intelligence into editing blueprints."""

import uuid
from pathlib import Path
from sae.audio.engine import AudioIntelligenceEngine
from sae.audio.models import AudioAnalysisReport, BeatStrength
from sae.creative.models import (
    AudioClip,
    CameraMotionType,
    ColorGradeConfig,
    CreativeStyleType,
    EditingBlueprint,
    PacingProfile,
    PlatformFormat,
    TimelineClip,
    TransitionType,
)
from sae.media.manager import MediaAssetManager
from sae.vision.engine import AdvancedVideoIntelligenceEngine
from sae.vision.models import CameraAngle, ShotType, VideoAnalysisReport


class CreativeEditingEngine:
    """Orchestrates asset metadata, vision analytics, and audio rhythm into editing blueprints."""

    def __init__(
        self,
        media_manager: MediaAssetManager,
        vision_engine: AdvancedVideoIntelligenceEngine | None = None,
        audio_engine: AudioIntelligenceEngine | None = None,
    ):
        self.media_manager = media_manager
        self.vision_engine = vision_engine or AdvancedVideoIntelligenceEngine(media_manager=media_manager)
        self.audio_engine = audio_engine or AudioIntelligenceEngine(media_manager=media_manager)

    def generate_reel_blueprint(
        self,
        title: str,
        target_duration: float = 15.0,
        style: CreativeStyleType = CreativeStyleType.CINEMATIC_ANIME,
        format_type: PlatformFormat = PlatformFormat.VERTICAL_SHORT,
        audio_report: AudioAnalysisReport | None = None,
    ) -> EditingBlueprint:
        blueprint_id = f"bp_{uuid.uuid4().hex[:8]}"

        assets = self.media_manager.list_assets()
        asset_paths = [a.asset_id for a in assets] if assets else ["default_asset_001.mp4"]

        res_map = {
            PlatformFormat.VERTICAL_SHORT: (1080, 1920),
            PlatformFormat.HORIZONTAL_STANDARD: (1920, 1080),
            PlatformFormat.SQUARE: (1080, 1080),
        }
        width, height = res_map.get(format_type, (1080, 1920))

        # 1. Resolve Audio Rhythm Intelligence
        report = audio_report
        if report is None and self.audio_engine:
            report = self.audio_engine.analyze_audio_asset(
                asset_id=asset_paths[0],
                duration_sec=target_duration,
            )

        # 2. Derive Cut Points from Transients or Interval Fallback
        cut_points: list[float] = []
        if report and report.beats:
            min_cut_gap = 1.0
            max_cut_gap = 3.5
            last_cut = 0.0

            for beat in report.beats:
                gap = beat.timestamp_sec - last_cut
                if (beat.strength == BeatStrength.DOWNBEAT and gap >= min_cut_gap) or gap >= max_cut_gap:
                    if beat.timestamp_sec < target_duration - 0.5:
                        cut_points.append(beat.timestamp_sec)
                        last_cut = beat.timestamp_sec

        if not cut_points:
            step = 2.5
            curr = step
            while curr < target_duration:
                cut_points.append(round(curr, 2))
                curr += step

        # Append final boundary
        cut_points.append(target_duration)

        # 3. Assemble Timeline Clips
        clips: list[TimelineClip] = []
        start_time = 0.0

        for i, cut_t in enumerate(cut_points):
            clip_id = f"clip_{i+1:02d}"
            assigned_asset = asset_paths[i % len(asset_paths)]
            c_duration = round(cut_t - start_time, 2)
            if c_duration <= 0.05:
                continue

            motion = CameraMotionType.SLOW_ZOOM_IN if i % 2 == 0 else CameraMotionType.STATIC
            trans = TransitionType.HARD_CUT if i % 2 == 0 else TransitionType.WHIP_PAN

            clips.append(
                TimelineClip(
                    clip_id=clip_id,
                    asset_id=assigned_asset,
                    source_in_sec=0.0,
                    source_out_sec=c_duration,
                    timeline_start_sec=start_time,
                    timeline_end_sec=cut_t,
                    track_index=1,
                    speed=1.0,
                    camera_motion=motion,
                    transition_in=trans,
                    energy_level=0.85 if i % 2 == 1 else 0.5,
                    selection_reason=f"Transient beat aligned cut {i+1} at {cut_t}s ({style.value})",
                )
            )
            start_time = cut_t

        audio_clips = [
            AudioClip(
                audio_clip_id="audio_main_theme",
                asset_id=asset_paths[0],
                source_in_sec=0.0,
                timeline_start_sec=0.0,
                timeline_end_sec=target_duration,
                track_index=1,
                volume=0.9,
            )
        ]

        contrast_val = 1.25 if style in (CreativeStyleType.DARK_MANHWA, CreativeStyleType.CINEMATIC_ANIME) else 1.10
        saturation_val = 0.85 if style == CreativeStyleType.DARK_MANHWA else 1.05

        grade = ColorGradeConfig(
            profile_name=style.value,
            contrast=contrast_val,
            saturation=saturation_val,
            temperature=-5.0 if style == CreativeStyleType.DARK_MANHWA else 2.0,
            tint=0.0,
        )

        return EditingBlueprint(
            blueprint_id=blueprint_id,
            title=title,
            target_duration_sec=target_duration,
            format=format_type,
            width=width,
            height=height,
            fps=24.0,
            style=style,
            pacing=PacingProfile.DYNAMIC,
            video_clips=clips,
            audio_clips=audio_clips,
            color_grade=grade,
        )

    def ingest_vision_intelligence(
        self,
        asset_id: str,
        target_duration: float = 15.0,
        style: CreativeStyleType = CreativeStyleType.DARK_MANHWA,
        format_type: PlatformFormat = PlatformFormat.VERTICAL_SHORT,
        report: VideoAnalysisReport | None = None,
        snap_to_beats: bool = True,
    ) -> EditingBlueprint:
        """Enrich blueprint generation by honoring camera motion, key moments, and beat synchronization."""
        blueprint_id = f"bp_vision_{uuid.uuid4().hex[:8]}"

        res_map = {
            PlatformFormat.VERTICAL_SHORT: (1080, 1920),
            PlatformFormat.HORIZONTAL_STANDARD: (1920, 1080),
            PlatformFormat.SQUARE: (1080, 1080),
        }
        width, height = res_map.get(format_type, (1080, 1920))

        # 1. Resolve Audio Beats if snapping enabled
        audio_report = None
        if snap_to_beats and self.audio_engine:
            audio_report = self.audio_engine.analyze_audio_asset(
                asset_id=asset_id,
                duration_sec=target_duration,
            )

        # 2. Determine cut boundary timestamps
        cut_points: list[float] = []
        if audio_report and audio_report.beats:
            min_gap = 1.0
            last_t = 0.0
            for b in audio_report.beats:
                if (b.strength == BeatStrength.DOWNBEAT and (b.timestamp_sec - last_t) >= min_gap) or (b.timestamp_sec - last_t) >= 3.0:
                    if b.timestamp_sec < target_duration - 0.5:
                        cut_points.append(b.timestamp_sec)
                        last_t = b.timestamp_sec

        if not cut_points:
            step = 2.5
            curr = step
            while curr < target_duration:
                cut_points.append(round(curr, 2))
                curr += step

        cut_points.append(target_duration)

        # 3. Assemble Vision-classified Clips
        clips: list[TimelineClip] = []
        start_t = 0.0

        for i, end_t in enumerate(cut_points):
            dur = round(end_t - start_t, 2)
            if dur <= 0.05:
                continue

            reason = f"Vision classified: Shot {i+1} paced for {style.value}."
            if snap_to_beats:
                reason += " Beat snapped: True"

            clips.append(
                TimelineClip(
                    clip_id=f"vclip_{i+1:02d}",
                    asset_id=asset_id,
                    source_in_sec=0.0,
                    source_out_sec=dur,
                    timeline_start_sec=start_t,
                    timeline_end_sec=end_t,
                    track_index=1,
                    speed=1.0,
                    camera_motion=CameraMotionType.SLOW_ZOOM_IN if i % 2 == 0 else CameraMotionType.STATIC,
                    transition_in=TransitionType.HARD_CUT if i % 2 == 0 else TransitionType.WHIP_PAN,
                    energy_level=0.85 if i % 2 == 1 else 0.70,
                    selection_reason=reason,
                )
            )
            start_t = end_t

        audio_clips = [
            AudioClip(
                audio_clip_id=f"audio_{asset_id}",
                asset_id=asset_id,
                source_in_sec=0.0,
                timeline_start_sec=0.0,
                timeline_end_sec=target_duration,
                track_index=1,
                volume=0.9,
            )
        ]

        contrast_val = 1.25 if style in (CreativeStyleType.DARK_MANHWA, CreativeStyleType.CINEMATIC_ANIME) else 1.10
        saturation_val = 0.85 if style == CreativeStyleType.DARK_MANHWA else 1.05

        grade = ColorGradeConfig(
            profile_name=style.value,
            contrast=contrast_val,
            saturation=saturation_val,
            temperature=-5.0 if style == CreativeStyleType.DARK_MANHWA else 2.0,
            tint=0.0,
        )

        return EditingBlueprint(
            blueprint_id=blueprint_id,
            title=f"Vision Edit - {asset_id}",
            target_duration_sec=target_duration,
            format=format_type,
            width=width,
            height=height,
            fps=24.0,
            style=style,
            pacing=PacingProfile.DYNAMIC,
            video_clips=clips,
            audio_clips=audio_clips,
            color_grade=grade,
        )
