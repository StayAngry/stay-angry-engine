"""Comprehensive Phase 11 test suite validating backend abstraction, rendering pipeline, and output verification."""

import pytest
from pathlib import Path
from sae.creative.models import EditingBlueprint, PlatformFormat
from sae.render.backend import MockMediaBackend
from sae.render.engine import MediaProcessingEngine
from sae.render.verifier import RenderVerificationError, RenderVerifier
from sae.resources import ResourceManager


@pytest.fixture
def render_env(tmp_path: Path):
    backend = MockMediaBackend()
    res_mgr = ResourceManager()
    engine = MediaProcessingEngine(tmp_path, backend=backend, resource_manager=res_mgr)
    return engine, backend, tmp_path


@pytest.mark.asyncio
async def test_render_blueprint_produces_verified_file(render_env):
    engine, backend, root = render_env
    bp = EditingBlueprint(
        blueprint_id="test_render_bp",
        title="Anime Fight Final Edit",
        format=PlatformFormat.VERTICAL_SHORT,
        width=1080,
        height=1920,
        fps=60.0,
        target_duration_sec=12.0
    )

    out_file = await engine.render_blueprint(bp)
    assert out_file.exists()
    assert out_file.stat().st_size > 0
    assert "SAE Render Manifest" in out_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_verifier_catches_resolution_mismatch(render_env):
    _, backend, root = render_env
    verifier = RenderVerifier(backend)
    
    dummy_out = root / "mismatch_output.mp4"
    dummy_out.write_text("sample video payload", encoding="utf-8")

    # Target blueprint expects landscape (1920x1080) but MockBackend probes vertical (1080x1920)
    bp = EditingBlueprint(
        blueprint_id="bp_mismatch",
        title="Landscape Target",
        width=1920,
        height=1080,
        target_duration_sec=10.0
    )

    with pytest.raises(RenderVerificationError, match="Resolution mismatch"):
        await verifier.verify_output(dummy_out, bp)