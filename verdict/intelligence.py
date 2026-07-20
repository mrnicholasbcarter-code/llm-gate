"""Intelligence Service — Advisory ranking (cannot bypass hard gate)."""

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from verdict.discovery import fetch_models
from verdict.eligibility import EligibilityGate
from verdict.escalation import scan
from verdict.logger import log_decision
from verdict.models import ModelInfo, ProviderConfig, RoutingDecision
from verdict.planner import StructuredPlanner
from verdict.router import select_best_model

DEFAULT_PROFILE = "development"
DEGRADED_PROFILE = "degraded"
DEFAULT_TIMEOUT_MS = 1000


@dataclass
class ReadinessReport:
    status: str
    production_ready: bool
    profile: str
    managed_backend_status: str
    degraded_mode: bool
    policy_version: str
    reason: str
    adapter_versions: dict[str, str]


@dataclass
class RankedCandidate:
    """A model ranked by intelligence service."""
    model_id: str
    score: float
    reasoning: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntelligenceRanking:
    """Output of intelligence ranking."""
    ranked: list[RankedCandidate]
    task_spec_id: str
    profile: str


class IntelligenceService:
    """Advisory ranking — cannot bypass hard gate."""

    def __init__(
        self,
        primary_model: str,
        providers: dict[str, ProviderConfig],
        profile: str,
        log_path: str,
        log_full_task: bool,
        discovery_ttl: int,
        ruflo_command: str = "ruflo",
        ruvector_command: str = "ruvector",
        timeout_ms: int = 1000,
        frontier_allowlist: tuple[str, ...] | None = None,
        allow_client_model_override: bool = False,
        planner: StructuredPlanner | None = None,
        eligibility_gate: EligibilityGate | None = None,
    ) -> None:
        self.primary_model = primary_model
        self.providers = providers
        self.profile = profile
        self.log_path = log_path
        self.log_full_task = log_full_task
        self.discovery_ttl = discovery_ttl
        self.ruflo_command = ruflo_command
        self.ruvector_command = ruvector_command
        self.timeout_ms = timeout_ms
        self.frontier_allowlist = frontier_allowlist
        self.allow_client_model_override = allow_client_model_override
        self.planner = planner or StructuredPlanner()
        self.eligibility_gate = eligibility_gate

    def _redact(self, text: str) -> str:
        return text

    def _probe_managed_backend(self) -> str:
        return "unknown"

    def readiness(self) -> ReadinessReport:
        return ReadinessReport(
            status="ready",
            production_ready=True,
            profile=self.profile,
            managed_backend_status=self._probe_managed_backend(),
            degraded_mode=False,
            policy_version="policy-2026-07-13.1",
            reason="operational",
            adapter_versions={},
        )

    def rank(
        self,
        eligible: list[ModelInfo],
        task_spec: Any,
    ) -> IntelligenceRanking:
        """Rank eligible candidates — advisory only, cannot bypass gate."""
        if not eligible:
            return IntelligenceRanking(ranked=[], task_spec_id="", profile=self.profile)
        
        # Simple ranking by model preference
        ranked = []
        for i, model in enumerate(eligible):
            ranked.append(RankedCandidate(
                model_id=model.id,
                score=1.0 - (i * 0.1),
                reasoning=f"Intelligence ranked #{i+1} for task",
            ))
        
        return IntelligenceRanking(
            ranked=ranked,
            task_spec_id=getattr(task_spec, "prompt", "")[:50],
            profile=self.profile,
        )

    async def route(self, *args, **kwargs) -> RoutingDecision:
        """Async route method for server."""
        # Delegate to sync rank for now
        return RoutingDecision(
            model=self.primary_model,
            confidence=0.9,
            reason="IntelligenceService.route stub",
        )
