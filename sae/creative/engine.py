"""Creative Timeline Generation Engine translating media intelligence into editing blueprints."""

import uuid
from pathlib import Path
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
    """Orchestrates asset metadata and multimodal vision intelligence into timeline blueprints."""

    def __init__(
        self,
        media_manager: MediaAssetManager,
        vision_engine: AdvancedVideoIntelligenceEngine | None = None,
    ):
        self.media_manager = media_manager
        self.vision_engine = vision_engine or AdvancedVideoIntelligenceEngine(media_manager=media_manager)

    def generate_reel_blueprint(
        self,
        title: str,
        target_duration: float = 15.0,
        style: CreativeStyleType = CreativeStyleType.CINEMATIC_ANIME,
        format_type: PlatformFormat = PlatformFormat.VERTICAL_SHORT,
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

        clips: list[TimelineClip] = []
        c_duration = 2.5
        num_clips = max(1, int(target_duration // c_duration))
        current_time = 0.0

        for i in range(num_clips):
            clip_id = f"clip_{i+1:02d}"
            assigned_asset = asset_paths[i % len(asset_paths)]
            motion = CameraMotionType.SLOW_ZOOM_IN if i % 2 == 0 else CameraMotionType.STATIC
            trans = TransitionType.HARD_CUT if i % 2 == 0 else TransitionType.WHIP_PAN

            clips.append(
                TimelineClip(
                    clip_id=clip_id,
                    asset_id=assigned_asset,
                    source_in_sec=0.0,
                    source_out_sec=c_duration,
                    timeline_start_sec=current_time,
                    timeline_end_sec=current_time + c_duration,
                    track_index=1,
                    speed=1.0,
                    camera_motion=motion,
                    transition_in=trans,
                    energy_level=0.85 if i % 2 == 1 else 0.5,
                    selection_reason=f"Beat alignment cut {i+1} for {style.value} pacing.",
                )
            )
            current_time += c_duration
            if current_time >= target_duration:
                break

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
    ) -> EditingBlueprint:
        """Construct an autonomous blueprint driven directly by multimodal vision analytics."""
        analysis = report or self.vision_engine.analyze_asset(asset_id)
        blueprint_id = f"bp_vision_{uuid.uuid4().hex[:8]}"

        res_map = {
            PlatformFormat.VERTICAL_SHORT: (1080, 1920),
            PlatformFormat.HORIZONTAL_STANDARD: (1920, 1080),
            PlatformFormat.SQUARE: (1080, 1080),
        }
        width, height = res_map.get(format_type, (1080, 1920))

        timeline_clips: list[TimelineClip] = []
        current_time = 0.0

        all_shots = [shot for scene in analysis.scenes for shot in scene.shots]
        sorted_shots = sorted(all_shots, key=lambda s: s.visual_energy, reverse=True)

        for idx, shot in enumerate(sorted_shots):
            shot_duration = shot.end_sec - shot.start_sec
            if current_time + shot_duration > target_duration:
                shot_duration = max(0.5, target_duration - current_time)

            motion = CameraMotionType.SLOW_ZOOM_IN if shot.shot_type == ShotType.CLOSE_UP else CameraMotionType.STATIC
            transition = TransitionType.WHIP_PAN if shot.visual_energy > 0.75 else TransitionType.HARD_CUT

            clip = TimelineClip(
                clip_id=f"vision_clip_{idx+1:02d}_{shot.shot_id}",
                asset_id=asset_id,
                source_in_sec=shot.start_sec,
                source_out_sec=shot.start_sec + shot_duration,
                timeline_start_sec=current_time,
                timeline_end_sec=current_time + shot_duration,
                track_index=1,
                speed=1.0,
                camera_motion=motion,
                transition_in=transition,
                energy_level=shot.visual_energy,
                selection_reason=f"Vision classified: {shot.shot_type.value} shot with {shot.camera_angle.value} angle",
            )
            timeline_clips.append(clip)
            current_time += shot_duration

            if current_time >= target_duration:
                break

        audio_clips = [
            AudioClip(
                audio_clip_id=f"audio_{asset_id}",
                asset_id=asset_id,
                source_in_sec=0.0,
                timeline_start_sec=0.0,
                timeline_end_sec=target_duration,
                track_index=1,
                volume=1.0,
            )
        ]

        color_grade = ColorGradeConfig(
            profile_name="dark_manhwa_vision",
            contrast=1.30,
            saturation=0.80,
            temperature=-6.0,
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
            pacing=PacingProfile.AGGRESSIVE,
            video_clips=timeline_clips,
            audio_clips=audio_clips,
            color_grade=color_grade,
        )
