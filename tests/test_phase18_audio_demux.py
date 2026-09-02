"""Test suite validating video audio extraction and transient analysis dispatch."""

from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from sae.audio.engine import AudioIntelligenceEngine
from sae.render.backend import FFmpegMediaBackend
from tests.test_phase16_audio_wav_detection import create_synthetic_wav


@pytest.mark.asyncio
async def test_video_audio_extraction_dispatch(tmp_path: Path):
    dummy_video = tmp_path / "cinematic_cut.mp4"
    dummy_video.write_bytes(b"dummy_mp4_bytes")

    target_wav = tmp_path / "extracted.wav"
    create_synthetic_wav(target_wav, duration_sec=1.5)

    backend = FFmpegMediaBackend(tmp_path)
    backend.extract_audio_stream = AsyncMock(return_value=target_wav)

    engine = AudioIntelligenceEngine(backend=backend)
    report = await engine.analyze_audio_asset_async(str(dummy_video))

    backend.extract_audio_stream.assert_awaited_once_with(dummy_video)
    assert report.asset_id == "extracted.wav"
    assert len(report.beats) > 0
