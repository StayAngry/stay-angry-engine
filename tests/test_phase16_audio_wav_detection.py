"""Test suite validating native WAV transient detection and energy peak extraction."""

import math
import struct
import wave
from pathlib import Path
import pytest
from sae.audio.engine import AudioIntelligenceEngine
from sae.audio.models import BeatStrength


def create_synthetic_wav(file_path: Path, duration_sec: float = 2.0, sample_rate: int = 44100):
    """Generate a PCM WAV file with silent troughs and energetic burst pulses."""
    n_frames = int(duration_sec * sample_rate)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        frames = bytearray()
        for i in range(n_frames):
            t = i / sample_rate
            # Pulses at 0.5s and 1.5s
            if 0.48 <= t <= 0.55 or 1.48 <= t <= 1.55:
                val = int(24000 * math.sin(2 * math.pi * 440 * t))
            else:
                val = int(100 * math.sin(2 * math.pi * 220 * t))
            frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)


def test_native_wav_transient_detection(tmp_path: Path):
    wav_path = tmp_path / "test_kick.wav"
    create_synthetic_wav(wav_path, duration_sec=2.0)

    engine = AudioIntelligenceEngine()
    report = engine.analyze_audio_asset(str(wav_path))

    assert report.asset_id == "test_kick.wav"
    assert report.duration_sec == pytest.approx(2.0, abs=0.1)
    assert len(report.beats) >= 2

    first_beat = report.beats[0].timestamp_sec
    assert 0.40 <= first_beat <= 0.60
