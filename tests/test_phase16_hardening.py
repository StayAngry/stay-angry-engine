"""Comprehensive Phase 16 test suite validating self-improvement boundaries, benchmarks, and production diagnostics."""

import pytest
from pathlib import Path
from sae.database import DatabaseManager
from sae.events import EventBus
from sae.hardening.benchmarks import BenchmarkEngine
from sae.hardening.engine import SelfImprovementEngine
from sae.hardening.models import EngineMode, ProposalRisk, ProposalStatus
from sae.media.manager import MediaAssetManager
from sae.models.registry import LocalModelRegistry


@pytest.fixture
def hardening_env(tmp_path: Path):
    db = DatabaseManager(tmp_path / "test_sae_hardening.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, tmp_path / "cache")
    model_reg = LocalModelRegistry()
    bm_engine = BenchmarkEngine()
    
    engine = SelfImprovementEngine(
        db_manager=db,
        model_registry=model_reg,
        media_manager=media_mgr,
        benchmark_engine=bm_engine,
        mode=EngineMode.PRODUCTION
    )
    return engine


def test_doctor_diagnostics_returns_healthy_system(hardening_env):
    engine = hardening_env
    report = engine.run_diagnostics()

    assert report.overall_status == "HEALTHY"
    assert len(report.checks) >= 3
    assert any(c.subsystem == "SQLite DB Core" and c.status == "OK" for c in checks_list(report))


def test_self_improvement_proposals_require_sandbox_and_benchmark(hardening_env):
    engine = hardening_env
    
    # Propose low-risk cache optimization
    prop = engine.propose_improvement(
        target_component="MediaCache",
        description="Optimize memory buffer",
        hypothesis="Reduces duplicate frame lookups",
        patch_payload={"buffer_size_mb": 512},
        risk=ProposalRisk.LOW
    )
    assert prop.status == ProposalStatus.PROPOSED

    # Evaluate proposal in benchmark harness
    evaluated = engine.test_and_evaluate_proposal(prop.proposal_id)
    assert evaluated.status == ProposalStatus.BENCHMARK_PASSED
    assert evaluated.candidate_score > evaluated.baseline_score

    # Deploy approved proposal
    success = engine.approve_and_deploy(prop.proposal_id)
    assert success is True
    assert evaluated.status == ProposalStatus.APPROVED

    # Test rollback capability
    rolled_back = engine.rollback(prop.proposal_id)
    assert rolled_back is True
    assert evaluated.status == ProposalStatus.ROLLED_BACK


def test_rejection_of_regressive_patch(hardening_env):
    engine = hardening_env
    
    # Propose patch with deliberate defect
    prop = engine.propose_improvement(
        target_component="TimelineScheduler",
        description="Experimental Fast Scheduler",
        hypothesis="May cause timing regressions",
        patch_payload={"introduce_fault": True},
        risk=ProposalRisk.HIGH
    )

    evaluated = engine.test_and_evaluate_proposal(prop.proposal_id)
    assert evaluated.status == ProposalStatus.REJECTED
    assert "Regression detected" in (evaluated.rejection_reason or "")


def checks_list(report):
    return report.checks