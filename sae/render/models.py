"""Typed models for rendering jobs, status tracking, and output verification."""

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field
from sae.creative.models import EditingBlueprint


class RenderStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RenderJob(BaseModel):
    job_id: str
    blueprint: EditingBlueprint
    output_path: Path
    status: RenderStatus = RenderStatus.PENDING
    progress_percent: float = 0.0
    error_message: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RenderResult(BaseModel):
    job_id: str
    status: RenderStatus
    output_path: Path
    rendered_frames: int
    verification_passed: bool = False
    error_message: str | None = None