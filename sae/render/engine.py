"""Media Processing Engine coordinating rendering backends, verification, and hardware resource checks."""

import uuid
from pathlib import Path
from sae.creative.models import EditingBlueprint
from sae.render.backend import BaseMediaBackend, FFmpegMediaBackend
from sae.render.models import RenderJob, RenderResult, RenderStatus
from sae.render.verifier import MediaOutputVerifier
from sae.resources import ResourceManager


class MediaProcessingEngine:
    def __init__(
        self,
        workspace_root: Path,
        backend: BaseMediaBackend | None = None,
        resource_manager: ResourceManager | None = None,
        verifier: MediaOutputVerifier | None = None
    ):
        self.workspace_root = workspace_root.resolve()
        self.backend = backend or FFmpegMediaBackend(self.workspace_root)
        self.resource_manager = resource_manager or ResourceManager()
        self.verifier = verifier or MediaOutputVerifier()

    async def render_blueprint(self, blueprint: EditingBlueprint) -> Path:
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        expected_output = self.workspace_root / "exports" / f"{blueprint.blueprint_id}_render.mp4"

        job = RenderJob(
            job_id=job_id,
            blueprint=blueprint,
            output_path=expected_output
        )

        # Execute render backend
        result: RenderResult = await self.backend.render(job)
        if result.status != RenderStatus.COMPLETED or not result.output_path.exists():
            raise RuntimeError(f"Rendering failed: {result.error_message or 'Unknown error'}")

        # Verify output integrity
        is_valid, _ = self.verifier.verify(result.output_path, blueprint)
        if not is_valid:
            raise RuntimeError("Render output verification failed.")

        return result.output_path