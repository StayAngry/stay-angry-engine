import dataclasses
"""FastAPI application exposing autonomous director orchestration endpoints."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from sae.api.models import DirectJobRequest, JobResponse, JobStatus
from sae.audio.engine import AudioIntelligenceEngine
from sae.audio.loudness_engine import AudioLoudnessEngine
from sae.creative.engine import CreativeEditingEngine
from sae.database import DatabaseManager
from sae.effects.color import CinematicColorEngine
from sae.effects.engine import AdvancedCreativeEngine
from sae.effects.typography_engine import KineticTypographyEngine
from sae.events import EventBus
from sae.media.manager import MediaAssetManager
from sae.orchestrator.engine import DirectorPipeline
from sae.render.backend import FFmpegMediaBackend, MockMediaBackend
from sae.render.engine import MediaProcessingEngine
from sae.vision.engine import AdvancedVideoIntelligenceEngine


app = FastAPI(
    title="Stay-Angry Engine Director API",
    version="1.0.0",
    description="Autonomous AI Video Synthesis & NLE Interchange API",
)

# In-memory job repository for async execution tracking
jobs_db: dict[str, JobResponse] = {}


def build_director(work_dir: Path, mock_render: bool = True) -> DirectorPipeline:
    work_dir.mkdir(parents=True, exist_ok=True)
    db = DatabaseManager(work_dir / "api_sae.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, work_dir / "media")
    audio = AudioIntelligenceEngine(media_mgr)
    creative = CreativeEditingEngine(media_mgr, audio_engine=audio)
    color = CinematicColorEngine()
    effects = AdvancedCreativeEngine(color)
    vision = AdvancedVideoIntelligenceEngine(media_mgr)
    loudness = AudioLoudnessEngine(media_mgr)
    typography = KineticTypographyEngine(media_mgr, output_dir=work_dir / "subtitles")

    backend = MockMediaBackend(output_dir=work_dir / "rendered") if mock_render else FFmpegMediaBackend(output_dir=work_dir / "rendered")
    render = MediaProcessingEngine(workspace_root=work_dir, backend=backend)

    return DirectorPipeline(
        media_manager=media_mgr,
        creative_engine=creative,
        vision_engine=vision,
        audio_engine=audio,
        loudness_engine=loudness,
        effects_engine=effects,
        typography_engine=typography,
        render_engine=render,
    )


async def process_direct_job(job_id: str, request: DirectJobRequest) -> None:
    job = jobs_db[job_id]
    job.status = JobStatus.PROCESSING
    work_dir = Path(".sae_cache") / "api_jobs" / job_id
    try:
        director = build_director(work_dir, mock_render=request.mock_render)
        manifest = await director.produce_reel(
            title=request.title,
            target_duration=request.duration,
            style=request.style,
            format_type=request.format_type,
            loudness_standard=request.loudness_standard,
            sample_transcript=request.transcript,
        )
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        if dataclasses.is_dataclass(manifest):
            raw_dict = dataclasses.asdict(manifest)
            # Serialize any nested Path or complex objects
            if isinstance(raw_dict.get("rendered_video_path"), Path):
                raw_dict["rendered_video_path"] = str(raw_dict["rendered_video_path"])
            if isinstance(raw_dict.get("subtitle_track_path"), Path):
                raw_dict["subtitle_track_path"] = str(raw_dict["subtitle_track_path"])
            job.manifest = raw_dict
        elif hasattr(manifest, "model_dump"):
            job.manifest = manifest.model_dump(mode="json")
        elif hasattr(manifest, "dict"):
            job.manifest = manifest.dict()
        else:
            job.manifest = dict(manifest)
    except Exception as e:
        job.status = JobStatus.FAILED
        job.completed_at = datetime.now(timezone.utc)
        job.error = str(e)


@app.post("/api/v1/direct", response_model=JobResponse, status_code=202)
async def create_direct_job(request: DirectJobRequest, background_tasks: BackgroundTasks):
    job_id = f"job_{uuid.uuid4().hex[:10]}"
    job = JobResponse(job_id=job_id, status=JobStatus.PENDING)
    jobs_db[job_id] = job
    background_tasks.add_task(process_direct_job, job_id, request)
    return job


@app.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job ID not found")
    return jobs_db[job_id]


@app.get("/api/v1/jobs/{job_id}/download")
async def download_rendered_media(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job ID not found")
    job = jobs_db[job_id]
    if job.status != JobStatus.COMPLETED or not job.manifest:
        raise HTTPException(status_code=400, detail=f"Job not completed. Current status: {job.status}")

    video_path_str = job.manifest.get("rendered_video_path")
    if not video_path_str:
        raise HTTPException(status_code=404, detail="No rendered video output registered in manifest")

    video_path = Path(video_path_str)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Rendered video file not found on disk")

    return FileResponse(video_path, media_type="video/mp4", filename=video_path.name)
