"""Typed schemas for hierarchical scene/shot decomposition, subjects, motion vectors, and visual intelligence."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Union
from pydantic import BaseModel, Field


class CameraShotType(str, Enum):
    CLOSE_UP = "CLOSE_UP"
    MEDIUM = "MEDIUM"
    WIDE = "WIDE"
    EXTREME_CLOSE_UP = "EXTREME_CLOSE_UP"
    EXTREME_WIDE = "EXTREME_WIDE"


ShotType = CameraShotType


class CameraAngle(str, Enum):
    EYE_LEVEL = "EYE_LEVEL"
    LOW_ANGLE = "LOW_ANGLE"
    HIGH_ANGLE = "HIGH_ANGLE"
    DUTCH_ANGLE = "DUTCH_ANGLE"
    OVER_THE_SHOULDER = "OVER_THE_SHOULDER"
    BIRDS_EYE = "BIRDS_EYE"


class MotionDirection(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UP = "UP"
    DOWN = "DOWN"
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"
    STATIC = "STATIC"


class CameraMovementType(str, Enum):
    STATIC = "STATIC"
    PAN_LEFT = "PAN_LEFT"
    PAN_RIGHT = "PAN_RIGHT"
    TILT_UP = "TILT_UP"
    TILT_DOWN = "TILT_DOWN"
    ZOOM = "ZOOM"
    ZOOM_IN = "ZOOM_IN"
    ZOOM_OUT = "ZOOM_OUT"
    TRACKING = "TRACKING"
    FAST_MOVEMENT = "FAST_MOVEMENT"
    WHIP_PAN = "WHIP_PAN"
    ROLL = "ROLL"
    SHAKE = "SHAKE"
    HANDHELD = "HANDHELD"
    ORBIT = "ORBIT"
    DOLLY = "DOLLY"


CameraMovement = CameraMovementType


class SubjectPosition(str, Enum):
    CENTER = "CENTER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    TOP_LEFT = "TOP_LEFT"
    TOP_RIGHT = "TOP_RIGHT"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"


class VisualLighting(BaseModel):
    lighting_type: str = "NATURAL"
    brightness: float = 1.0
    contrast: float = 1.0
    color_temperature: float = 0.0


LightingCondition = VisualLighting
LightingType = VisualLighting


class VisualQuality(BaseModel):
    quality_score: float = 0.90
    is_blurry: bool = False
    resolution: str = "1080p"


class BoundingBox(BaseModel):
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0


SubjectBoundingBox = BoundingBox


class DetectedSubject(BaseModel):
    subject_id: str = "subject_1"
    label: str = "person"
    confidence: float = 0.95
    bounding_box: BoundingBox = Field(default_factory=BoundingBox)
    position: SubjectPosition = SubjectPosition.CENTER
    has_face: bool = False
    is_primary: bool = True


class FaceDetection(BaseModel):
    face_id: str = "face_1"
    bounding_box: BoundingBox = Field(default_factory=BoundingBox)
    expression: str = "neutral"
    confidence: float = 0.90


class ActionDetection(BaseModel):
    action_type: str = "action"
    confidence: float = 0.85
    start_sec: float = 0.0
    end_sec: float = 2.0


class ImpactMoment(BaseModel):
    timestamp_sec: float = 0.0
    intensity: float = 0.8
    action_description: str = "impact hit"


class TransitionOpportunity(BaseModel):
    timestamp_sec: float = 0.0
    confidence: float = 0.85
    suggested_transition: str = "HARD_CUT"
    reason: str = "Pacing beat align"


class ShotDecomposition(BaseModel):
    shot_id: str
    start_sec: float
    end_sec: float
    shot_type: CameraShotType = CameraShotType.MEDIUM
    primary_action: str = "general"
    motion_direction: MotionDirection = MotionDirection.STATIC
    motion_magnitude: float = 0.5
    visual_energy: float = 0.5
    has_impact: bool = False
    impact_timestamp: float | None = None
    camera_angle: CameraAngle = CameraAngle.EYE_LEVEL
    camera_movement: CameraMovementType = CameraMovementType.STATIC
    lighting: Union[VisualLighting, str] = Field(default_factory=VisualLighting)
    quality: Union[VisualQuality, str] = Field(default_factory=VisualQuality)
    subjects: list[DetectedSubject] = Field(default_factory=list)
    faces: list[FaceDetection] = Field(default_factory=list)
    actions: list[ActionDetection] = Field(default_factory=list)
    impacts: list[ImpactMoment] = Field(default_factory=list)
    transition_opportunities: list[TransitionOpportunity] = Field(default_factory=list)


ShotAnalysis = ShotDecomposition


class SceneDecomposition(BaseModel):
    scene_id: str
    start_sec: float
    end_sec: float
    environment: str = "standard"
    mood: str = "neutral"
    shots: list[ShotDecomposition] = Field(default_factory=list)


SceneAnalysis = SceneDecomposition


class VideoIntelligenceReport(BaseModel):
    asset_id: str
    global_visual_energy: float = 0.65
    scenes: list[SceneDecomposition] = Field(default_factory=list)
    transition_opportunities: list[Any] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


VideoAnalysisReport = VideoIntelligenceReport
VisionAnalysisReport = VideoIntelligenceReport
VisualIntelligenceReport = VideoIntelligenceReport