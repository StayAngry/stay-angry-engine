"""Low-level media processing and FFmpeg dispatch backend."""

import asyncio
import os
import shutil
from pathlib import Path


class FFmpegMediaBackend:
    """Executes FFmpeg system commands for media transformation and demuxing."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_binary = shutil.which("ffmpeg") or "ffmpeg"

    async def extract_audio_stream(
        self,
        video_path: Path,
        output_wav_path: Path | None = None,
        sample_rate: int = 44100,
    ) -> Path:
        """Demux and convert video audio stream into uncompressed 16-bit mono PCM WAV."""
        if not video_path.exists():
            raise FileNotFoundError(f"Source video file not found: {video_path}")

        target_wav = output_wav_path or (self.workspace_root / f"{video_path.stem}_audio.wav")
        target_wav.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg_binary,
            "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(sample_rate),
            "-ac", "1",
            str(target_wav),
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg audio extraction failed: {stderr.decode(errors='ignore')}")

        return target_wav
