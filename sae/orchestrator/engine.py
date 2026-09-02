"""Director Pipeline: Capstone end-to-end orchestrator for autonomous media production."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import uuid

from sae.audio.engine import AudioIntelligenceEngine
from sae.audio.loudness_engine import AudioLoudnessEngine
from sae.audio.loudness_models import DuckingConfig, LoudnessTargetStandard
from sae.creative.engine import CreativeEditingEngine
from sae.creative.models import CreativeStyleType, EditingBlueprint, PlatformFormat
from sae.effects.engine import AdvancedCreativeEngine
from sae.effects.models import CreativeLookType
from sae.effects.typography_engine import KineticTypographyEngine
from sae.effects.typography_models import SubtitleSegment, TypographyConfig, WordTiming
from sae.media.manager import MediaAssetManager
from sae.render.engine import MediaProcessingEngine
from sae.vision.engine import AdvancedVideoIntelligenceEngine


@dataclass
class ProductionManifest:
    pipeline_id: str
    blueprint: EditingBlueprint
    rendered_video_path: Path
    subtitle_track_path: Path | None
    loudness_calibrated: bool
    total_clips: int


class DirectorPipeline:
    """Master orchestrator executing complete end-to-end video synthesis."""

    def __init__(
        self,
        media_manager: MediaAssetManager,
        creative_engine: CreativeEditingEngine,
        vision_engine: AdvancedVideoIntelligenceEngine,
        audio_engine: AudioIntelligenceEngine,
        loudness_engine: AudioLoudnessEngine,
        effects_engine: AdvancedCreativeEngine,
        typography_engine: KineticTypographyEngine,
        render_engine: MediaProcessingEngine,
    ):
        self.media_manager = media_manager
        self.creative_engine = creative_engine
        self.vision_engine = vision_engine
        self.audio_engine = audio_engine
        self.loudness_engine = loudness_engine
        self.effects_engine = effects_engine
        self.typography_engine = typography_engine
        self.render_engine = render_engine

    async def produce_reel(
        self,
        title: str,
        target_duration: float = 6.0,
        style: CreativeStyleType = CreativeStyleType.DARK_MANHWA,
        format_type: PlatformFormat = PlatformFormat.VERTICAL_SHORT,
        loudness_standard: LoudnessTargetStandard = LoudnessTargetStandard.REELS_TIKTOK_SHORT,
        sample_transcript: list[str] | None = None,
    ) -> ProductionManifest:
        pipeline_id = f"dir_{uuid.uuid4().hex[:8]}"

        # 1. Generate Creative Blueprint
        blueprint = self.creative_engine.generate_reel_blueprint(
            title=title,
            target_duration=target_duration,
            style=style,
            format_type=format_type,
        )

        # 2. Audio Loudness & Dynamics Calibration
        blueprint = self.loudness_engine.apply_loudness_to_blueprint(
            blueprint=blueprint,
            standard=loudness_standard,
            ducking=DuckingConfig(enabled=True),
        )

        # 3. Vision & Beat-Aligned Typography
        sub_path: Path | None = None
        if sample_transcript:
            words = [
                WordTiming(
                    word=w,
                    start_sec=i * 0.5,
                    end_sec=(i + 1) * 0.5,
                )
                for i, w in enumerate(sample_transcript)
            ]
            segments = [
                SubtitleSegment(
                    segment_id=f"seg_{pipeline_id}",
                    start_sec=0.0,
                    end_sec=min(target_duration, len(words) * 0.5),
                    text=" ".join(sample_transcript),
                    words=words,
                )
            ]
            sub_path = self.typography_engine.export_subtitles(
                segments=segments,
                blueprint=blueprint,
                config=TypographyConfig(),
            )
            # Attach generated subtitles directly to blueprint
            setattr(blueprint, "subtitle_path", sub_path)

        # 4. Color Grading and Visual Treatment
        look_type = (
            CreativeLookType.MANHWA_DARK
            if "MANHWA" in style.value
            else CreativeLookType.ANIME_CINEMATIC
        )
        self.effects_engine.generate_treatment(
            blueprint=blueprint,
            vision_report=None,
            look=look_type,
        )

        # 5. Media Processing and Render Dispatch
        rendered_file = await self.render_engine.render_blueprint(blueprint)

        return ProductionManifest(
            pipeline_id=pipeline_id,
            blueprint=blueprint,
            rendered_video_path=rendered_file,
            subtitle_track_path=sub_path,
            loudness_calibrated=True,
            total_clips=len(blueprint.video_clips),
        )
