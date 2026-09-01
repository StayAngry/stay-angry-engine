"""Controlled Self-Improvement Engine and Production Diagnostics (SAE Doctor)."""

import uuid
from pathlib import Path
from typing import Any
from sae.database import DatabaseManager
from sae.hardening.benchmarks import BenchmarkEngine
from sae.hardening.models import (
    DiagnosticCheck,
    EngineMode,
    ImprovementProposal,
    ProposalRisk,
    ProposalStatus,
    SystemHealthReport,
)
from sae.media.manager import MediaAssetManager
from sae.models.registry import LocalModelRegistry


class SelfImprovementEngine:
    def __init__(
        self,
        db_manager: DatabaseManager,
        model_registry: LocalModelRegistry,
        media_manager: MediaAssetManager,
        benchmark_engine: BenchmarkEngine | None = None,
        mode: EngineMode = EngineMode.PRODUCTION
    ):
        self.db_manager = db_manager
        self.model_registry = model_registry
        self.media_manager = media_manager
        self.benchmark_engine = benchmark_engine or BenchmarkEngine()
        self.mode = mode
        self._proposals: dict[str, ImprovementProposal] = {}
        self._active_baseline_version = "1.0.0"

    def run_diagnostics(self) -> SystemHealthReport:
        checks: list[DiagnosticCheck] = []

        # 1. Database Check
        try:
            with self.db_manager._get_connection() as conn:
                conn.execute("SELECT 1")
            checks.append(DiagnosticCheck(subsystem="SQLite DB Core", status="OK", details="Connected and responsive."))
        except Exception as e:
            checks.append(DiagnosticCheck(subsystem="SQLite DB Core", status="FAIL", details=str(e)))

        # 2. Local Models Check
        models = self.model_registry.list_models()
        checks.append(
            DiagnosticCheck(
                subsystem="Local Model Registry",
                status="OK" if models else "WARN",
                details=f"{len(models)} local models registered."
            )
        )

        # 3. Media Subsystem Check
        assets = self.media_manager.list_assets()
        checks.append(
            DiagnosticCheck(
                subsystem="Media Asset Manager",
                status="OK",
                details=f"{len(assets)} registered assets indexed."
            )
        )

        overall = "HEALTHY" if all(c.status != "FAIL" for c in checks) else "DEGRADED"

        return SystemHealthReport(
            overall_status=overall,
            engine_mode=self.mode,
            checks=checks
        )

    def propose_improvement(
        self,
        target_component: str,
        description: str,
        hypothesis: str,
        patch_payload: dict[str, Any],
        risk: ProposalRisk = ProposalRisk.LOW
    ) -> ImprovementProposal:
        prop_id = f"prop_{uuid.uuid4().hex[:6]}"
        proposal = ImprovementProposal(
            proposal_id=prop_id,
            target_component=target_component,
            description=description,
            hypothesis=hypothesis,
            risk=risk,
            status=ProposalStatus.PROPOSED,
            patch_payload=patch_payload
        )
        self._proposals[prop_id] = proposal
        return proposal

    def test_and_evaluate_proposal(self, proposal_id: str) -> ImprovementProposal:
        prop = self._proposals.get(proposal_id)
        if not prop:
            raise ValueError(f"Proposal {proposal_id} not found.")

        prop.status = ProposalStatus.SANDBOX_TESTING
        
        # Run benchmark in sandbox harness
        bm = self.benchmark_engine.run_component_benchmark(
            component_name=prop.target_component,
            candidate_config=prop.patch_payload
        )

        if not bm.passed or bm.regressions_detected > 0:
            prop.status = ProposalStatus.REJECTED
            prop.rejection_reason = f"Regression detected ({bm.regressions_detected} failures)."
            prop.candidate_score = 40.0
        else:
            prop.candidate_score = 92.0
            prop.status = ProposalStatus.BENCHMARK_PASSED

        return prop

    def approve_and_deploy(self, proposal_id: str) -> bool:
        prop = self._proposals.get(proposal_id)
        if not prop or prop.status != ProposalStatus.BENCHMARK_PASSED:
            return False

        # Production Guard: High-risk proposals in production mode require manual sign-off
        if self.mode == EngineMode.PRODUCTION and prop.risk == ProposalRisk.HIGH:
            return False

        prop.status = ProposalStatus.APPROVED
        return True

    def rollback(self, proposal_id: str) -> bool:
        prop = self._proposals.get(proposal_id)
        if prop and prop.status == ProposalStatus.APPROVED:
            prop.status = ProposalStatus.ROLLED_BACK
            return True
        return False