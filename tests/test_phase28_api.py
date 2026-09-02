"""Phase 28 test suite: REST API async jobs & download endpoints."""

from fastapi.testclient import TestClient
import pytest

from sae.api.server import app, jobs_db
from sae.api.models import JobStatus
from sae.creative.models import CreativeStyleType, PlatformFormat


@pytest.fixture(autouse=True)
def clean_jobs():
    jobs_db.clear()
    yield
    jobs_db.clear()


client = TestClient(app)


def test_api_direct_submission_and_lifecycle():
    payload = {
        "title": "Solo Leveling Web Reel",
        "duration": 4.0,
        "style": CreativeStyleType.DARK_MANHWA.value,
        "format_type": PlatformFormat.VERTICAL_SHORT.value,
        "transcript": ["ARISE", "SHADOWS"],
        "mock_render": True,
    }

    # 1. Dispatch job
    post_res = client.post("/api/v1/direct", json=payload)
    assert post_res.status_code == 202
    data = post_res.json()
    job_id = data["job_id"]
    assert data["status"] == "pending"

    # 2. Poll job status
    get_res = client.get(f"/api/v1/jobs/{job_id}")
    assert get_res.status_code == 200
    job_info = get_res.json()
    assert job_info["status"] == "completed"
    assert job_info["manifest"] is not None
    assert job_info["manifest"]["total_clips"] >= 1

    # 3. Download endpoint
    dl_res = client.get(f"/api/v1/jobs/{job_id}/download")
    assert dl_res.status_code == 200
    assert len(dl_res.content) > 0


def test_api_job_not_found():
    res = client.get("/api/v1/jobs/job_invalid_id")
    assert res.status_code == 404
