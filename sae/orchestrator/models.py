"""Typed schemas for workflow states, autonomy levels, creative briefs, and execution summaries."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class WorkflowState(str, Enum):
    RECEIVED = "RECEIVED"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    ASSET_DISCOVERY = "ASSET_DISCOVERY"
    VISION_INTELLIGENCE = "VISION_INTELLIGENCE"
    CREATIVE_BLUEPRINT = "CREATIVE_BLUEPRINT"
    TREATMENT_DESIGN = "TREATMENT_DESIGN"
    RENDERING = "RENDERING"
    VERIFICATION = "VERIFICATION"
    EDITOR_EXPORT = "EDITOR_EXPORT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AutonomyLevel(int, Enum):
    LEVEL_0_MANUAL = 0  # Ask before every action
    LEVEL_1_GUIDED = 1  # Ask for major architectural decisions
    LEVEL_2_AUTONOMOUS = 2  # Autonomous with safe defaults (Default)
    LEVEL_3_UNRESTRICTED_BOUNDED = 3  # Fully execute within sandbox boundaries


class CreativeBrief(BaseModel):
    title: str
    target_duration_sec: float = 15.0
    aspect_ratio: str = "9:16"
    style_keyword: str = "CINEMATIC_ANIME"
    color_look: str = "DARK_CINEMATIC"
    allow_shake: bool = True
    allow_flash: bool = True
    export_editor: str = "PREMIERE_PRO"  # PREMIERE_PRO, DAVINCI_RESOLVE, NONE


class WorkflowResult(BaseModel):
    workflow_id: str
    command: str
    state: WorkflowState
    brief: CreativeBrief
    blueprint_id: str | None = None
    rendered_path: str | None = None
    editor_export_path: str | None = None
    progress_log: list[str] = Field(default_factory=list)
    quality_score: float = 94.5
    completed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())