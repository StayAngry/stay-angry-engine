"""Data models for kinetic subtitles, typography styling, and word-level animations."""

from enum import Enum
from pydantic import BaseModel, Field


class SubtitleAnimationStyle(str, Enum):
    """Animation behaviors for short-form video captions."""
    POP_IN = "POP_IN"              # Quick scale up on active word
    KARAOKE_HIGHLIGHT = "KARAOKE"  # Text color fills as words trigger
    BOUNCE_ACCENT = "BOUNCE"       # Vertical nudge on transient/beat
    CLEAN_STATIC = "STATIC"        # Standard legible block subtitles


class WordTiming(BaseModel):
    """Timestamped word for granular kinetic animations."""
    word: str
    start_sec: float
    end_sec: float
    confidence: float = 1.0
    is_emphasized: bool = False


class SubtitleSegment(BaseModel):
    """A sentence or phrase containing word-level timing breakdown."""
    segment_id: str
    start_sec: float
    end_sec: float
    text: str
    words: list[WordTiming] = Field(default_factory=list)
    energy_score: float = 0.5


class TypographyConfig(BaseModel):
    """Visual design parameters for caption overlays."""
    font_family: str = "Montserrat-Black"
    font_size: int = 48
    primary_color: str = "&H00FFFFFF"      # Pure white in ASS hex
    accent_color: str = "&H0000FFFF"       # Bright yellow accent
    outline_color: str = "&H00000000"      # Black border
    outline_width: float = 3.0
    shadow_depth: float = 2.0
    animation_style: SubtitleAnimationStyle = SubtitleAnimationStyle.POP_IN
    all_caps: bool = True
    alignment: int = 2                     # Bottom-center in ASS notation
    margin_v: int = 180                    # Clear of UI elements on 1080x1920 reels
