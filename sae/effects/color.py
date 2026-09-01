"""Cinematic color grading profiles and lookup mapping."""

from typing import Any
from sae.effects.models import ColorGradeProfile, CreativeLookType, FilmGrainConfig


class CinematicColorEngine:
    def __init__(self):
        self.profiles: dict[CreativeLookType, ColorGradeProfile] = {
            CreativeLookType.DARK_CINEMATIC: ColorGradeProfile(
                look_type=CreativeLookType.DARK_CINEMATIC,
                contrast=1.25,
                saturation=0.85,
                temperature=-5.0,
                tint=1.0,
                film_grain=FilmGrainConfig(enabled=True, amount=0.18)
            ),
            CreativeLookType.ANIME_CINEMATIC: ColorGradeProfile(
                look_type=CreativeLookType.ANIME_CINEMATIC,
                contrast=1.15,
                saturation=1.20,
                temperature=3.0,
                tint=0.0,
                film_grain=FilmGrainConfig(enabled=False, amount=0.05)
            ),
            CreativeLookType.HIGH_ENERGY_NEON: ColorGradeProfile(
                look_type=CreativeLookType.HIGH_ENERGY_NEON,
                contrast=1.30,
                saturation=1.40,
                temperature=8.0,
                tint=-2.0,
                film_grain=FilmGrainConfig(enabled=True, amount=0.10)
            ),
            CreativeLookType.HIGH_CONTRAST: ColorGradeProfile(
                look_type=CreativeLookType.HIGH_CONTRAST,
                contrast=1.40,
                saturation=1.0,
                temperature=0.0,
                tint=0.0,
                film_grain=FilmGrainConfig(enabled=True, amount=0.12)
            ),
            CreativeLookType.DOCUMENTARY_NATURAL: ColorGradeProfile(
                look_type=CreativeLookType.DOCUMENTARY_NATURAL,
                contrast=1.05,
                saturation=1.0,
                temperature=0.0,
                tint=0.0,
                film_grain=FilmGrainConfig(enabled=False, amount=0.0)
            ),
            CreativeLookType.MANHWA_DARK: ColorGradeProfile(
                look_type=CreativeLookType.MANHWA_DARK,
                contrast=1.35,
                saturation=0.80,
                temperature=-8.0,
                tint=2.0,
                film_grain=FilmGrainConfig(enabled=True, amount=0.20)
            ),
        }

    def get_look_profile(self, look: CreativeLookType | str = CreativeLookType.DARK_CINEMATIC) -> ColorGradeProfile:
        if isinstance(look, str):
            for k in self.profiles:
                if k.value == look or k.name == look:
                    return self.profiles[k]
            return self.profiles[CreativeLookType.DARK_CINEMATIC]
        return self.profiles.get(look, self.profiles[CreativeLookType.DARK_CINEMATIC])

    def get_profile(self, look: CreativeLookType | str = CreativeLookType.DARK_CINEMATIC) -> ColorGradeProfile:
        return self.get_look_profile(look)

    def generate_grade(self, look: CreativeLookType | str = CreativeLookType.DARK_CINEMATIC, **kwargs: Any) -> ColorGradeProfile:
        return self.get_look_profile(look)
