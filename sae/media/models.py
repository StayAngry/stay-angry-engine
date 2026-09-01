"""Typed schemas for media assets, technical metadata, scene cuts, beats, and creative tags."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class MediaType(str, Enum):
    VIDEO = "VIDEO"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    FONT = "FONT"
    UNKNOWN = "UNKNOWN"


class MediaStyle(str, Enum):
    ANIME = "ANIME"
    MANHWA_STYLE = "MANHWA_STYLE"
    ANIMATION = "ANIMATION"
    LIVE_ACTION = "LIVE_ACTION"
    ILLUSTRATION = "ILLUSTRATION"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class SceneCut(BaseModel):
    scene_id: str
    start_sec: float
    end_sec: float
    keyframe_preview_path: str | None = None
    motion_intensity: str = "MEDIUM"  # LOW, MEDIUM, HIGH


class BeatMarker(BaseModel):
    timestamp_sec: float
    energy: float = 1.0


class AudioAnalysis(BaseModel):
    duration_sec: float
    sample_rate: int
    channels: int
    tempo_bpm: float = 120.0
    beats: list[BeatMarker] = Field(default_factory=list)
    waveform_peaks: list[float] = Field(default_factory=list)


class CreativeAttributes(BaseModel):
    energy: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    mood: str = "NEUTRAL"
    style: MediaStyle = MediaStyle.UNKNOWN
    confidence: float = 1.0
    user_override: bool = False


class MediaAsset(BaseModel):
    asset_id: str
    file_path: str
    filename: str
    media_type: MediaType
    file_size_bytes: int
    content_hash: str
    width: int | None = None
    height: int | None = None
    duration_sec: float | None = None
    fps: float | None = None
    tags: list[str] = Field(default_factory=list)
    user_rating: int | None = None
    scenes: list[SceneCut] = Field(default_factory=list)
    audio_data: AudioAnalysis | None = None
    creative: CreativeAttributes = Field(default_factory=CreativeAttributes)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())