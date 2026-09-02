"""REST API request and response data models."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from sae.creative.models import CreativeStyleType, PlatformFormat
from sae.audio.loudness_models import LoudnessTargetStandard


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DirectJobRequest(BaseModel):
    title: str = Field(default="Autonomous Action Reel", description="Title of the synthesis reel")
    duration: float = Field(default=6.0, gt=0, le=60.0, description="Target duration in seconds")
    style: CreativeStyleType = Field(default=CreativeStyleType.DARK_MANHWA, description="Creative visual look preset")
    format_type: PlatformFormat = Field(default=PlatformFormat.VERTICAL_SHORT, description="Platform canvas layout")
    loudness_standard: LoudnessTargetStandard = Field(default=LoudnessTargetStandard.REELS_TIKTOK_SHORT)
    transcript: list[str] = Field(default_factory=lambda: ["AWAKEN", "SHADOW", "MONARCH"])
    mock_render: bool = Field(default=True, description="Fast mock backend mode for API integration")


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    manifest: dict[str, Any] | None = None
    error: str | None = None
