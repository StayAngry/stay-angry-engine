"""Data models for audio transient, tempo, and beat analysis."""

from enum import Enum
from pydantic import BaseModel, Field


class BeatStrength(str, Enum):
    DOWNBEAT = "DOWNBEAT"
    STANDARD = "STANDARD"
    SUBTLE = "SUBTLE"


class AudioBeat(BaseModel):
    timestamp_sec: float
    strength: BeatStrength = BeatStrength.STANDARD
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    energy: float = Field(default=0.5, ge=0.0, le=1.0)


class AudioAnalysisReport(BaseModel):
    asset_id: str
    duration_sec: float
    estimated_bpm: float = 120.0
    beats: list[AudioBeat] = Field(default_factory=list)
    energy_envelope: list[float] = Field(default_factory=list)

    def find_nearest_beat(self, target_sec: float, tolerance_sec: float = 0.35) -> float:
        """Locate the closest beat within the given tolerance window, else return target."""
        if not self.beats:
            return target_sec
        best_beat = min(self.beats, key=lambda b: abs(b.timestamp_sec - target_sec))
        if abs(best_beat.timestamp_sec - target_sec) <= tolerance_sec:
            return round(best_beat.timestamp_sec, 3)
        return target_sec
