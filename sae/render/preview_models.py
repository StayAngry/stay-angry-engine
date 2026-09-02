"""Data models for real-time timeline frame previews and caching."""

from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel, Field


class PreviewFrame(BaseModel):
    """Metadata representing a single extracted preview frame."""
    timestamp_sec: float
    frame_index: int
    active_clip_id: str | None = None
    asset_id: str | None = None
    source_offset_sec: float = 0.0
    width: int = 1080
    height: int = 1920
    is_cut_point: bool = False
    color_grade_applied: bool = True
    cached_path: Path | None = None
    extracted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PreviewManifest(BaseModel):
    """Manifest summarizing cached preview frames for an EditingBlueprint."""
    blueprint_id: str
    target_duration_sec: float
    total_cached_frames: int
    cut_point_timestamps: list[float] = Field(default_factory=list)
    frames: list[PreviewFrame] = Field(default_factory=list)
