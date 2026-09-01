"""Typed schemas for improvement proposals, risk assessments, benchmarks, and health diagnostics."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ProposalRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ProposalStatus(str, Enum):
    PROPOSED = "PROPOSED"
    SANDBOX_TESTING = "SANDBOX_TESTING"
    BENCHMARK_PASSED = "BENCHMARK_PASSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"


class EngineMode(str, Enum):
    PRODUCTION = "PRODUCTION"
    DEVELOPMENT = "DEVELOPMENT"
    RESEARCH = "RESEARCH"


class ImprovementProposal(BaseModel):
    proposal_id: str
    target_component: str
    description: str
    hypothesis: str
    risk: ProposalRisk = ProposalRisk.LOW
    status: ProposalStatus = ProposalStatus.PROPOSED
    baseline_score: float = 85.0
    candidate_score: float = 0.0
    patch_payload: dict[str, Any] = Field(default_factory=dict)
    rejection_reason: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BenchmarkResult(BaseModel):
    benchmark_id: str
    component_name: str
    execution_time_ms: float
    memory_mb: float
    task_success_rate: float
    regressions_detected: int = 0
    passed: bool = True


class DiagnosticCheck(BaseModel):
    subsystem: str
    status: str  # OK, WARN, FAIL
    details: str


class SystemHealthReport(BaseModel):
    overall_status: str
    engine_mode: EngineMode = EngineMode.PRODUCTION
    checks: list[DiagnosticCheck] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())