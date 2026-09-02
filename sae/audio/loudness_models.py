"""Data models for LUFS normalization and dynamic ducking profiles."""

from enum import Enum
from pydantic import BaseModel, Field


class LoudnessTargetStandard(str, Enum):
    """Industry-standard integrated loudness targets."""
    REELS_TIKTOK_SHORT = "REELS_TIKTOK_SHORT"  # -14 LUFS, -1.0 dBTP
    YOUTUBE_STANDARD = "YOUTUBE_STANDARD"      # -14 LUFS, -1.0 dBTP
    BROADCAST_EBU_R128 = "BROADCAST_EBU_R128"  # -23 LUFS, -1.0 dBTP
    PODCAST_STREAMING = "PODCAST_STREAMING"    # -16 LUFS, -1.5 dBTP


class LoudnessProfile(BaseModel):
    """Target loudness and peak thresholds for normalization."""
    target_i_lufs: float = -14.0
    target_tp_db: float = -1.0
    target_lra: float = 7.0
    standard: LoudnessTargetStandard = LoudnessTargetStandard.REELS_TIKTOK_SHORT


class DuckingConfig(BaseModel):
    """Parameters controlling background music ducking when speech is detected."""
    attenuation_db: float = -12.0
    attack_ms: float = 20.0
    release_ms: float = 250.0
    threshold_db: float = -24.0
    enabled: bool = True


class AudioNormalizationReport(BaseModel):
    """Audit metrics produced by two-pass or simulated loudnorm processing."""
    asset_id: str
    input_i_lufs: float
    input_tp_db: float
    output_i_lufs: float
    output_tp_db: float
    ducking_applied: bool = False
    filter_string: str = ""
