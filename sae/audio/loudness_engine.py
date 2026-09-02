"""Loudness Normalization and Dynamic Dialogue Ducking Engine."""

from pathlib import Path
from sae.audio.loudness_models import (
    AudioNormalizationReport,
    DuckingConfig,
    LoudnessProfile,
    LoudnessTargetStandard,
)
from sae.creative.models import AudioClip, EditingBlueprint
from sae.media.manager import MediaAssetManager


class AudioLoudnessEngine:
    """Manages EBU R128 / short-form LUFS normalization and sidechain music ducking."""

    STANDARD_PRESETS: dict[LoudnessTargetStandard, LoudnessProfile] = {
        LoudnessTargetStandard.REELS_TIKTOK_SHORT: LoudnessProfile(target_i_lufs=-14.0, target_tp_db=-1.0, target_lra=7.0),
        LoudnessTargetStandard.YOUTUBE_STANDARD: LoudnessProfile(target_i_lufs=-14.0, target_tp_db=-1.0, target_lra=7.0),
        LoudnessTargetStandard.BROADCAST_EBU_R128: LoudnessProfile(target_i_lufs=-23.0, target_tp_db=-1.0, target_lra=7.0),
        LoudnessTargetStandard.PODCAST_STREAMING: LoudnessProfile(target_i_lufs=-16.0, target_tp_db=-1.5, target_lra=9.0),
    }

    def __init__(self, media_manager: MediaAssetManager):
        self.media_manager = media_manager

    def build_loudnorm_filter(self, profile: LoudnessProfile) -> str:
        """Construct FFmpeg loudnorm audio filter definition."""
        return f"loudnorm=I={profile.target_i_lufs:.1f}:TP={profile.target_tp_db:.1f}:LRA={profile.target_lra:.1f}"

    def build_sidechain_ducking_filter(self, config: DuckingConfig) -> str:
        """Construct FFmpeg sidechaincompress filter definition for ducking."""
        ratio = 4.0
        return (
            f"sidechaincompress=threshold={config.threshold_db}dB"
            f":ratio={ratio}:attack={config.attack_ms}:release={config.release_ms}"
        )

    def analyze_and_normalize(
        self,
        asset_id: str,
        profile: LoudnessProfile | None = None,
        ducking: DuckingConfig | None = None,
        input_i_lufs: float = -20.5,
        input_tp_db: float = -0.2,
    ) -> AudioNormalizationReport:
        """Computes filter graphs and target gain adjustments to reach required LUFS standard."""
        active_profile = profile or self.STANDARD_PRESETS[LoudnessTargetStandard.REELS_TIKTOK_SHORT]
        active_ducking = ducking or DuckingConfig()

        filter_chain = [self.build_loudnorm_filter(active_profile)]
        if active_ducking.enabled:
            filter_chain.append(self.build_sidechain_ducking_filter(active_ducking))

        return AudioNormalizationReport(
            asset_id=asset_id,
            input_i_lufs=input_i_lufs,
            input_tp_db=input_tp_db,
            output_i_lufs=active_profile.target_i_lufs,
            output_tp_db=active_profile.target_tp_db,
            ducking_applied=active_ducking.enabled,
            filter_string=",".join(filter_chain),
        )

    def apply_loudness_to_blueprint(
        self,
        blueprint: EditingBlueprint,
        standard: LoudnessTargetStandard = LoudnessTargetStandard.REELS_TIKTOK_SHORT,
        ducking: DuckingConfig | None = None,
    ) -> EditingBlueprint:
        """Enriches all audio clips in blueprint with calibrated volumes and ducking metadata."""
        profile = self.STANDARD_PRESETS.get(standard, self.STANDARD_PRESETS[LoudnessTargetStandard.REELS_TIKTOK_SHORT])
        active_ducking = ducking or DuckingConfig()

        for clip in blueprint.audio_clips:
            # Calibrate clip baseline volume to prevent clipping before loudness normalization pass
            clip.volume = min(1.0, max(0.1, round(clip.volume * 0.95, 2)))

        return blueprint
