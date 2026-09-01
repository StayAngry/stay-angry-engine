"""Typed schemas for cinematic color grades, visual effects stacks, keyframes, and treatments."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class CreativeLookType(str, Enum):
    DARK_CINEMATIC = "DARK_CINEMATIC"
    ANIME_CINEMATIC = "ANIME_CINEMATIC"
    HIGH_ENERGY_NEON = "HIGH_ENERGY_NEON"
    DOCUMENTARY_NATURAL = "DOCUMENTARY_NATURAL"
    MANHWA_DARK = "MANHWA_DARK"
    HIGH_CONTRAST = "HIGH_CONTRAST"
    WARM_VINTAGE = "WARM_VINTAGE"
    COOL_SCI_FI = "COOL_SCI_FI"


ColorLook = CreativeLookType


class EffectCategory(str, Enum):
    COLOR_CORRECTION = "COLOR_CORRECTION"
    IMPACT_SHAKE = "IMPACT_SHAKE"
    LIGHTING_FLASH = "LIGHTING_FLASH"
    MOTION_ZOOM = "MOTION_ZOOM"
    FILM_GRAIN = "FILM_GRAIN"


class KeyframeProperty(str, Enum):
    SCALE = "SCALE"
    POSITION_X = "POSITION_X"
    POSITION_Y = "POSITION_Y"
    OPACITY = "OPACITY"
    ROTATION = "ROTATION"


class FilmGrainConfig(BaseModel):
    enabled: bool = True
    amount: float = 0.15
    seed: int = 42


FilmGrainSettings = FilmGrainConfig


class ColorGradeProfile(BaseModel):
    look_type: CreativeLookType = CreativeLookType.DARK_CINEMATIC
    contrast: float = 1.15
    saturation: float = 1.05
    temperature: float = 0.0
    tint: float = 0.0
    film_grain: FilmGrainConfig = Field(default_factory=FilmGrainConfig)


DetailedColorGrade = ColorGradeProfile


class VisualEffectItem(BaseModel):
    effect_id: str
    name: str
    category: EffectCategory
    start_sec: float
    end_sec: float
    intensity: float = 1.0
    reason: str = ""


class MotionKeyframe(BaseModel):
    keyframe_id: str
    target_clip_id: str
    timestamp_sec: float
    property_name: KeyframeProperty
    value: float
    easing: str = "ease_in_out"


class CreativeTreatment(BaseModel):
    treatment_id: str
    target_blueprint_id: str
    color_grade: ColorGradeProfile
    effects_stack: list[VisualEffectItem] = Field(default_factory=list)
    motion_keyframes: list[MotionKeyframe] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


VisualTreatment = CreativeTreatment
TreatmentBlueprint = CreativeTreatment
CreativeTreatmentBlueprint = CreativeTreatment
