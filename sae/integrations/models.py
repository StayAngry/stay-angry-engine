"""Typed schemas for editor capabilities, timeline interchange, track markers, and export verification."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class EditorType(str, Enum):
    PREMIERE_PRO = "PREMIERE_PRO"
    DAVINCI_RESOLVE = "DAVINCI_RESOLVE"
    GENERIC_XML = "GENERIC_XML"


class EditorCapabilities(BaseModel):
    editor_type: EditorType
    installed: bool = False
    version: str | None = None
    supports_multitrack: bool = True
    supports_native_color: bool = True
    supports_keyframes: bool = True
    supports_markers: bool = True


class TimelineMarker(BaseModel):
    marker_id: str
    timestamp_sec: float
    name: str
    comment: str = ""
    color: str = "CYAN"  # CYAN, RED, GREEN, YELLOW


class ExportedClipMapping(BaseModel):
    sae_clip_id: str
    editor_item_id: str
    asset_path: str
    track_index: int
    source_in_sec: float
    source_out_sec: float
    timeline_start_sec: float
    timeline_end_sec: float
    speed: float = 1.0


class EditorProjectManifest(BaseModel):
    manifest_id: str
    editor_type: EditorType
    project_name: str
    sequence_name: str
    width: int
    height: int
    fps: float
    total_duration_sec: float
    video_clips: list[ExportedClipMapping] = Field(default_factory=list)
    audio_clips: list[ExportedClipMapping] = Field(default_factory=list)
    markers: list[TimelineMarker] = Field(default_factory=list)
    xml_payload: str | None = None
    rendered_fallback_clips: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())