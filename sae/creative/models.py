"""Typed data structures and models for creative editing blueprints, timelines, and clips."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class PlatformFormat(str, Enum):
    VERTICAL_SHORT = "9:16"       # Reels, TikTok, Shorts (1080x1920)
    HORIZONTAL_STANDARD = "16:9"  # YouTube, TV (1920x1080 / 3840x2160)
    SQUARE = "1:1"                # Instagram Post (1080x1080)


class CreativeStyleType(str, Enum):
    CINEMATIC_ANIME = "CINEMATIC_ANIME"
    DARK_MANHWA = "DARK_MANHWA"
    HIGH_ENERGY_ACTION = "HIGH_ENERGY_ACTION"
    MINIMAL_DOCUMENTARY = "MINIMAL_DOCUMENTARY"
    FAST_PACED_EDIT = "FAST_PACED_EDIT"


class PacingProfile(str, Enum):
    AGGRESSIVE = "AGGRESSIVE"
    DYNAMIC = "DYNAMIC"
    STEADY = "STEADY"


class CameraMotionType(str, Enum):
    STATIC = "STATIC"
    SLOW_ZOOM_IN = "SLOW_ZOOM_IN"
    SLOW_ZOOM_OUT = "SLOW_ZOOM_OUT"
    WHIP_PAN_LEFT = "WHIP_PAN_LEFT"
    WHIP_PAN_RIGHT = "WHIP_PAN_RIGHT"
    CAMERA_SHAKE = "CAMERA_SHAKE"


CameraMotion = CameraMotionType


class TransitionType(str, Enum):
    HARD_CUT = "HARD_CUT"
    CROSS_DISSOLVE = "CROSS_DISSOLVE"
    WHIP_PAN = "WHIP_PAN"
    GLITCH = "GLITCH"
    FLASH_WHITE = "FLASH_WHITE"
    ZOOM_IN = "ZOOM_IN"


Transition = TransitionType


class ColorGradeConfig(BaseModel):
    profile_name: str = "CINEMATIC_ANIME"
    contrast: float = 1.15
    saturation: float = 1.05
    temperature: float = 0.0
    tint: float = 0.0
    film_grain: float = 0.10


class TimelineClip(BaseModel):
    clip_id: str
    asset_id: str
    source_in_sec: float = 0.0
    source_out_sec: float = 2.0
    timeline_start_sec: float = 0.0
    timeline_end_sec: float = 2.0
    track_index: int = 1
    speed: float = 1.0
    camera_motion: CameraMotionType = CameraMotionType.STATIC
    transition_in: TransitionType = TransitionType.HARD_CUT
    energy_level: float = 0.5
    selection_reason: str = ""


class AudioClip(BaseModel):
    audio_clip_id: str
    asset_id: str
    source_in_sec: float = 0.0
    timeline_start_sec: float = 0.0
    timeline_end_sec: float = 15.0
    track_index: int = 1
    volume: float = 1.0


TimelineAudioClip = AudioClip


class EditingBlueprint(BaseModel):
    blueprint_id: str
    title: str = "Reel Blueprint"
    style: CreativeStyleType = CreativeStyleType.CINEMATIC_ANIME
    format: PlatformFormat = PlatformFormat.VERTICAL_SHORT
    width: int = 1080
    height: int = 1920
    fps: float = 60.0
    target_duration_sec: float = 15.0
    pacing: PacingProfile = PacingProfile.DYNAMIC
    video_clips: list[TimelineClip] = Field(default_factory=list)
    audio_clips: list[AudioClip] = Field(default_factory=list)
    color_grade: ColorGradeConfig = Field(default_factory=ColorGradeConfig)
    ai_creative_intent: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())