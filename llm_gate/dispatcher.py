"""Bounded, availability-aware swarm assignment.

This module is deliberately a planning contract: it never invokes a provider.  A
caller may use the returned assignment with a separately verified executor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from llm_gate.contracts import AvailabilitySnapshot, RuntimeCandidate


class SubagentExecutor(Protocol):
    """Optional execution seam; live provider integrations are out of scope."""

    def execute(self, candidate: RuntimeCandidate, timeout_seconds: float) -> Any: ...


@dataclass(frozen=True)
class DispatchPolicy:
    """Hard bounds and the narrow conditions under which escalation is legal."""

    required_capabilities: frozenset[str] = frozenset()
    verification_required: bool = False
    verification_capability: str = "verification"
    allow_escalation: bool = True
    max_escalation_depth: int = 1
    max_budget: float | None = None
    max_concurrency: int = 1
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class AssignmentExplanation:
    runtime_id: str
    selected: bool
    cost: float | None
    escalation_depth: int
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "selected": self.selected,
            "cost": self.cost,
            "escalation_depth": self.escalation_depth,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class DispatchResult:
    selected: RuntimeCandidate | None
    explanations: tuple[AssignmentExplanation, ...]
    eligible: tuple[RuntimeCandidate, ...] = ()
    dry_run: bool = True
    reason: str = ""
    estimated_cost: float = 0.0
    escalation_depth: int = 0

    @property
    def assignment(self) -> RuntimeCandidate | None:
        return self.selected

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": self.selected.to_dict() if self.selected else None,
            "explanations": [item.to_dict() for item in self.explanations],
            "eligible": [item.to_dict() for item in self.eligible],
            "dry_run": self.dry_run,
            "reason": self.reason,
            "estimated_cost": self.estimated_cost,
            "escalation_depth": self.escalation_depth,
        }


def _as_candidate(value: RuntimeCandidate | dict[str, Any]) -> RuntimeCandidate:
    return value if isinstance(value, RuntimeCandidate) else RuntimeCandidate.from_dict(value)


def _as_snapshot(value: AvailabilitySnapshot | dict[str, Any]) -> AvailabilitySnapshot:
    if isinstance(value, AvailabilitySnapshot):
        return value
    candidates = [_as_candidate(item) for item in value.get("candidates", [])]
    return AvailabilitySnapshot.from_dict({**value, "candidates": candidates})


def _timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _signal(candidate: RuntimeCandidate, *names: str) -> Any:
    lowered = {name.lower() for name in names}
    for key, value in candidate.signals.items():
        if key.lower() in lowered:
            return value
        if isinstance(value, dict) and any(k.lower() in lowered for k in value):
            return value
    return None


def _number(candidate: RuntimeCandidate, *names: str) -> float | None:
    value = _signal(candidate, *names)
    if isinstance(value, dict):
        matching = {n.lower() for n in names}
        value = next((v for k, v in value.items() if k.lower() in matching), value)
        if isinstance(value, dict):
            value = value.get("value", value.get("amount"))
    try:
        return None if value is None or isinstance(value, bool) else float(value)
    except (TypeError, ValueError):
        return None


def _cost(candidate: RuntimeCandidate) -> float | None:
    return _number(candidate, "cost", "cost_usd", "estimated_cost", "usd")


def _capabilities(candidate: RuntimeCandidate) -> frozenset[str]:
    return frozenset(item.lower() for item in candidate.capabilities)


class SwarmDispatcher:
    """Select the least-cost candidate using only a caller-supplied snapshot."""

    def __init__(self, policy: DispatchPolicy | None = None, *, clock: Any = None) -> None:
        self.policy = policy or DispatchPolicy()
        self.clock = clock

    def dispatch(
        self,
        snapshot: AvailabilitySnapshot | dict[str, Any],
        *,
        policy: DispatchPolicy | None = None,
        dry_run: bool = True,
        now: datetime | None = None,
    ) -> DispatchResult:
        active = policy or self.policy
        snap = _as_snapshot(snapshot)
        current = now or (self.clock() if self.clock else datetime.now(timezone.utc))
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        candidates = tuple(_as_candidate(item) for item in snap.candidates)
        explanations: list[AssignmentExplanation] = []
        global_reason = self._snapshot_reason(snap, current)
        eligible: list[RuntimeCandidate] = []
        for candidate in candidates:
            reasons = list(global_reason or ())
            reasons.extend(self._reject_reasons(candidate, active))
            if not reasons:
                eligible.append(candidate)
            explanations.append(
                AssignmentExplanation(
                    candidate.runtime_id, False, _cost(candidate), 0, tuple(reasons)
                )
            )
        if not eligible:
            return DispatchResult(None, tuple(explanations), (), dry_run, "no eligible candidates")

        verification = active.verification_required
        verified = [
            c for c in eligible if active.verification_capability.lower() in _capabilities(c)
        ]
        depth = 0
        pool = eligible
        if verification and verified:
            pool = verified
            if len(verified) < len(eligible):
                if not active.allow_escalation or active.max_escalation_depth < 1:
                    return DispatchResult(
                        None,
                        tuple(explanations),
                        tuple(eligible),
                        dry_run,
                        "verification escalation denied",
                    )
                depth = 1
        elif verification and not verified:
            if not active.allow_escalation or active.max_escalation_depth < 1:
                return DispatchResult(
                    None,
                    tuple(explanations),
                    tuple(eligible),
                    dry_run,
                    "verification escalation denied",
                )
            depth = 1
            required = active.required_capabilities | {active.verification_capability.lower()}
            pool = [c for c in eligible if required <= _capabilities(c)]
            if not pool:
                return DispatchResult(
                    None,
                    tuple(explanations),
                    tuple(eligible),
                    dry_run,
                    "no verification-capable candidate",
                )
        chosen = min(
            pool, key=lambda c: (_cost(c) if _cost(c) is not None else float("inf"), c.runtime_id)
        )
        chosen_cost = _cost(chosen) or 0.0
        for index, item in enumerate(explanations):
            if item.runtime_id == chosen.runtime_id:
                explanations[index] = AssignmentExplanation(
                    item.runtime_id, True, item.cost, depth, ("least cost eligible",)
                )
        return DispatchResult(
            chosen, tuple(explanations), tuple(pool), dry_run, "selected", chosen_cost, depth
        )

    def _snapshot_reason(self, snapshot: AvailabilitySnapshot, now: datetime) -> tuple[str, ...]:
        if snapshot.state.lower() in {"outage", "down", "unavailable", "timeout"}:
            return (f"snapshot outage: {snapshot.state}",)
        observed = _timestamp(snapshot.observed_at)
        expires = _timestamp(snapshot.expires_at)
        if observed is None or (expires and now > expires):
            return ("stale availability snapshot",)
        if (now - observed).total_seconds() > snapshot.ttl_seconds:
            return ("stale availability snapshot",)
        return ()

    def _reject_reasons(self, candidate: RuntimeCandidate, policy: DispatchPolicy) -> list[str]:
        reasons: list[str] = []
        availability = candidate.availability.lower()
        if not candidate.catalog_present:
            reasons.append("unknown candidate: absent from catalog")
        if not candidate.live_eligible:
            reasons.append("not live eligible")
        if availability in {"unknown", "stale", "outage", "down", "unhealthy", "denied", "timeout"}:
            reasons.append(f"unavailable: {availability}")
        if availability in {"quota_exhausted", "rate_limited", "locked_out", "circuit_open"}:
            reasons.append(f"unavailable: {availability}")
        quota = _number(
            candidate, "quota", "quota_remaining", "quota_remaining_pct", "headroom_pct"
        )
        if quota is not None and quota <= 0:
            reasons.append("quota exhausted")
        health = _signal(candidate, "health", "status")
        if isinstance(health, str) and health.lower() in {"unhealthy", "down", "offline"}:
            reasons.append(f"unhealthy: {health.lower()}")
        missing = policy.required_capabilities - _capabilities(candidate)
        if missing:
            reasons.append(f"missing capability: {sorted(missing)[0]}")
        cost = _cost(candidate)
        if policy.max_budget is not None and (cost is None or cost > policy.max_budget):
            reasons.append("budget limit exceeded")
        concurrency = _number(candidate, "concurrency", "in_flight")
        if concurrency is not None and concurrency >= policy.max_concurrency:
            reasons.append("concurrency limit reached")
        latency = _number(candidate, "latency_ms", "timeout_ms")
        if latency is not None and latency > policy.timeout_seconds * 1000:
            reasons.append("timeout limit exceeded")
        return reasons


Dispatcher = SwarmDispatcher
