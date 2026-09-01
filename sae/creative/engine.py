"""Creative Timeline Generation Engine translating media intelligence into editing blueprints."""

import uuid
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


class CreativeEditingEngine:
    def __init__(self, media_manager: MediaAssetManager):
        self.media_manager = media_manager

    def generate_reel_blueprint(
        self,
        title: str,
        target_duration: float = 15.0,
        style: CreativeStyleType = CreativeStyleType.CINEMATIC_ANIME,
        format_type: PlatformFormat = PlatformFormat.VERTICAL_SHORT
    ) -> EditingBlueprint:
        blueprint_id = f"bp_{uuid.uuid4().hex[:8]}"
        
        assets = self.media_manager.list_assets()
        video_assets = [a for a in assets if a.media_type.value == "VIDEO"] or assets
        asset_paths = [a.file_path for a in video_assets] if video_assets else [f"mock_asset_{i}" for i in range(1, 5)]

        # Cut interval tuned to ensure multi-shot dynamic pacing
        cut_duration = 2.0 if target_duration >= 8.0 else 1.5
        num_clips = max(2, int(target_duration // cut_duration))
        video_clips: list[TimelineClip] = []

        current_time = 0.0
        for i in range(num_clips):
            clip_id = f"clip_{i+1:02d}"
            assigned_asset = asset_paths[i % len(asset_paths)]
            
            motion = CameraMotionType.SLOW_ZOOM_IN if i % 2 == 0 else CameraMotionType.STATIC
            trans = TransitionType.HARD_CUT if i == 0 else (TransitionType.WHIP_PAN if i % 2 == 1 else TransitionType.CROSS_DISSOLVE)

            c_duration = cut_duration if (current_time + cut_duration) <= target_duration else (target_duration - current_time)
            
            video_clips.append(
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
                    selection_reason=f"Beat alignment cut {i+1} for {style.value} pacing."
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
                volume=0.9
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
            film_grain=0.15
        )

        return EditingBlueprint(
            blueprint_id=blueprint_id,
            title=title,
            style=style,
            format=format_type,
            width=1080,
            height=1920,
            fps=60.0,
            target_duration_sec=target_duration,
            pacing=PacingProfile.AGGRESSIVE if style == CreativeStyleType.DARK_MANHWA else PacingProfile.DYNAMIC,
            video_clips=video_clips,
            audio_clips=audio_clips,
            color_grade=grade,
            ai_creative_intent=f"High impact {style.value} edit tailored for vertical platforms."
        )