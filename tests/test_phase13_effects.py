"""Comprehensive Phase 13 test suite validating creative effects, cinematic color grading, and override rules."""

import pytest
from pathlib import Path
from sae.creative.engine import CreativeEditingEngine
from sae.database import DatabaseManager
from sae.effects.color import CinematicColorEngine
from sae.effects.engine import AdvancedCreativeEngine
from sae.effects.models import CreativeLookType, EffectCategory
from sae.events import EventBus
from sae.media.manager import MediaAssetManager
from sae.vision.engine import AdvancedVideoIntelligenceEngine


@pytest.fixture
def effects_env(tmp_path: Path):
    db = DatabaseManager(tmp_path / "test_sae_effects.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "cache")
    creative_engine = CreativeEditingEngine(media_mgr)
    vision_engine = AdvancedVideoIntelligenceEngine(media_mgr)
    color_engine = CinematicColorEngine()
    effects_engine = AdvancedCreativeEngine(color_engine)
    return effects_engine, creative_engine, vision_engine


def test_cinematic_color_look_generation(effects_env):
    effects_engine, _, _ = effects_env
    grade = effects_engine.color_engine.generate_grade(look=CreativeLookType.DARK_CINEMATIC)

    assert grade.look_type == CreativeLookType.DARK_CINEMATIC
    assert grade.contrast > 1.0
    assert grade.temperature < 0.0  # Cool cinematic bias
    assert grade.film_grain.enabled is True
    assert grade.film_grain.seed == 42


def test_treatment_generation_with_impact_effects_and_restraint(effects_env):
    effects_engine, creative_engine, vision_engine = effects_env
    
    bp = creative_engine.generate_reel_blueprint("Manhwa Action Sequence", target_duration=12.0)
    report = vision_engine.analyze_asset("mock_asset_action")
    treatment = effects_engine.generate_treatment(bp, vision_report=report, look=CreativeLookType.MANHWA_DARK)

    assert treatment.target_blueprint_id == bp.blueprint_id
    assert len(treatment.effects_stack) >= 2
    assert any(e.name == "ImpactCameraShake" for e in treatment.effects_stack)
    assert len(treatment.motion_keyframes) >= 2
    assert len(treatment.explanations) > 0


def test_user_override_restraint_rule(effects_env):
    effects_engine, creative_engine, vision_engine = effects_env

    bp = creative_engine.generate_reel_blueprint("Dialogue Scene", target_duration=10.0)
    report = vision_engine.analyze_asset("mock_dialogue")
    
    # User strictly requests no camera shake
    treatment = effects_engine.generate_treatment(
        bp,
        vision_report=report,
        user_overrides={"allow_shake": False}
    )

    assert not any(e.name == "ImpactCameraShake" for e in treatment.effects_stack)