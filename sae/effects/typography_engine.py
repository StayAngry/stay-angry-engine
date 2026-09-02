"""Kinetic subtitle generation and ASS/SRT formatting engine."""

from pathlib import Path
from sae.audio.models import AudioAnalysisReport, BeatStrength
from sae.creative.models import EditingBlueprint
from sae.effects.typography_models import (
    SubtitleAnimationStyle,
    SubtitleSegment,
    TypographyConfig,
    WordTiming,
)
from sae.media.manager import MediaAssetManager


class KineticTypographyEngine:
    """Transforms transcripts and audio transients into animated ASS subtitle tracks."""

    def __init__(self, media_manager: MediaAssetManager, output_dir: Path | None = None):
        self.media_manager = media_manager
        self.output_dir = (output_dir or Path(".sae_cache/subtitles")).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def align_words_to_transients(
        self,
        words: list[WordTiming],
        audio_report: AudioAnalysisReport | None,
    ) -> list[WordTiming]:
        """Snaps word start times to the closest rhythmic downbeat if within reach."""
        if not audio_report or not audio_report.beats:
            return words

        downbeat_times = [
            b.timestamp_sec for b in audio_report.beats if b.strength == BeatStrength.DOWNBEAT
        ]

        for w in words:
            for d_time in downbeat_times:
                if abs(w.start_sec - d_time) <= 0.12:
                    w.start_sec = d_time
                    w.is_emphasized = True
                    break

        return words

    def generate_ass_script(
        self,
        segments: list[SubtitleSegment],
        config: TypographyConfig,
        blueprint: EditingBlueprint,
    ) -> str:
        """Constructs an Advanced SubStation Alpha (.ass) file script supporting kinetic pop animations."""
        header = f"""[Script Info]
Title: {blueprint.title} Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {blueprint.width}
PlayResY: {blueprint.height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{config.font_family},{config.font_size},{config.primary_color},{config.accent_color},{config.outline_color},&H60000000,-1,0,0,0,100,100,0,0,1,{config.outline_width},{config.shadow_depth},{config.alignment},40,40,{config.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        lines: list[str] = []
        for seg in segments:
            start_str = self._format_ass_time(seg.start_sec)
            end_str = self._format_ass_time(seg.end_sec)

            if config.animation_style == SubtitleAnimationStyle.POP_IN and seg.words:
                text_parts = []
                for w in seg.words:
                    word_text = w.word.upper() if config.all_caps else w.word
                    if w.is_emphasized:
                        text_parts.append(f"{{\\c{config.accent_color}\\fscx115\\fscy115}}{word_text}{{\\r}}")
                    else:
                        text_parts.append(word_text)
                dialogue_text = " ".join(text_parts)
            else:
                dialogue_text = seg.text.upper() if config.all_caps else seg.text

            lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{dialogue_text}")

        return header + "\n".join(lines) + "\n"

    def export_subtitles(
        self,
        segments: list[SubtitleSegment],
        blueprint: EditingBlueprint,
        config: TypographyConfig | None = None,
        audio_report: AudioAnalysisReport | None = None,
    ) -> Path:
        """Generates, beat-aligns, and persists the .ass subtitle track."""
        active_config = config or TypographyConfig()

        for seg in segments:
            seg.words = self.align_words_to_transients(seg.words, audio_report)

        script_content = self.generate_ass_script(segments, active_config, blueprint)
        out_path = self.output_dir / f"{blueprint.blueprint_id}_subtitles.ass"
        out_path.write_text(script_content, encoding="utf-8")
        return out_path

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        """Formats fractional seconds into ASS timestamp format (H:MM:SS.cs)."""
        hrs = int(seconds // 3600)
        rem = seconds % 3600
        mins = int(rem // 60)
        secs = rem % 60
        cs = int(round((secs - int(secs)) * 100))
        return f"{hrs:d}:{mins:02d}:{int(secs):02d}.{cs:02d}"
