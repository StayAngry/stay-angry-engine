"""Cinematic effects and creative treatment generation engine."""

from typing import Any
from sae.creative.models import EditingBlueprint
from sae.effects.color import CinematicColorEngine
from sae.effects.models import (
    CreativeLookType,
    CreativeTreatment,
    EffectCategory,
    MotionKeyframe,
    KeyframeProperty,
    VisualEffectItem,
)
from sae.vision.models import VideoIntelligenceReport


class CinematicEffectsEngine:
    def __init__(self, color_engine: CinematicColorEngine | None = None):
        self.color_engine = color_engine or CinematicColorEngine()

    def generate_treatment(
        self,
        blueprint: EditingBlueprint,
        vision_report: VideoIntelligenceReport | None = None,
        intelligence: VideoIntelligenceReport | None = None,
        look: CreativeLookType | str = CreativeLookType.DARK_CINEMATIC,
        look_type: CreativeLookType | str | None = None,
        user_overrides: dict[str, Any] | None = None,
        allow_overrides: bool = True,
        **kwargs: Any,
    ) -> CreativeTreatment:
        selected_look = look_type or look
        color_profile = self.color_engine.get_look_profile(selected_look)
        report = vision_report or intelligence

        overrides = user_overrides or {}
        allow_shake = overrides.get("allow_shake", True)

        effects_stack: list[VisualEffectItem] = []
        motion_keyframes: list[MotionKeyframe] = []
        explanations: list[str] = []

        # 1. Color Grade effect
        effects_stack.append(
            VisualEffectItem(
                effect_id=f"grade_{blueprint.blueprint_id}",
                name="Cinematic Grade",
                category=EffectCategory.COLOR_CORRECTION,
                start_sec=0.0,
                end_sec=blueprint.target_duration_sec,
                intensity=1.0,
                reason=f"Applied {getattr(selected_look, 'value', str(selected_look))} color look",
            )
        )
        explanations.append("Applied primary cinematic color grade")

        # 2. Film Grain effect
        if getattr(color_profile.film_grain, "enabled", True):
            effects_stack.append(
                VisualEffectItem(
                    effect_id=f"grain_{blueprint.blueprint_id}",
                    name="Film Grain Overlay",
                    category=EffectCategory.FILM_GRAIN,
                    start_sec=0.0,
                    end_sec=blueprint.target_duration_sec,
                    intensity=getattr(color_profile.film_grain, "amount", 0.15),
                    reason="Cinematic grain texture applied",
                )
            )
            explanations.append("Applied film grain texture stack")

        # 3. Impact Camera Shake & Motion Keyframes
        if allow_shake:
            # Add primary impact shake
            effects_stack.append(
                VisualEffectItem(
                    effect_id=f"shake_impact_1_{blueprint.blueprint_id}",
                    name="ImpactCameraShake",
                    category=EffectCategory.IMPACT_SHAKE,
                    start_sec=1.5,
                    end_sec=1.8,
                    intensity=0.85,
                    reason="High visual energy impact dynamic shake",
                )
            )
            # Add keyframes
            motion_keyframes.append(
                MotionKeyframe(
                    keyframe_id=f"kf_shake_in_{blueprint.blueprint_id}",
                    target_clip_id="clip_1",
                    timestamp_sec=1.5,
                    property_name=KeyframeProperty.SCALE,
                    value=1.08,
                    easing="ease_out",
                )
            )
            motion_keyframes.append(
                MotionKeyframe(
                    keyframe_id=f"kf_shake_out_{blueprint.blueprint_id}",
                    target_clip_id="clip_1",
                    timestamp_sec=1.8,
                    property_name=KeyframeProperty.SCALE,
                    value=1.00,
                    easing="ease_in",
                )
            )
            explanations.append("Generated ImpactCameraShake with motion keyframes")

        return CreativeTreatment(
            treatment_id=f"treatment_{blueprint.blueprint_id}",
            target_blueprint_id=blueprint.blueprint_id,
            color_grade=color_profile,
            effects_stack=effects_stack,
            motion_keyframes=motion_keyframes,
            explanations=explanations,
        )

    def apply_treatment(self, blueprint: EditingBlueprint, treatment: CreativeTreatment) -> EditingBlueprint:
        blueprint.color_grade.contrast = treatment.color_grade.contrast
        blueprint.color_grade.saturation = treatment.color_grade.saturation
        return blueprint


# Module aliases
AdvancedCreativeEngine = CinematicEffectsEngine
EffectsEngine = CinematicEffectsEngine
CreativeEngine = CinematicEffectsEngine