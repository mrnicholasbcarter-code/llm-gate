from datetime import datetime, timezone
from typing import Any

from verdict.contracts import AvailabilitySnapshot, RuntimeCandidate
from verdict.dispatcher import DispatchPolicy, SwarmDispatcher

NOW = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)


def candidate(runtime_id: str, *, cost: float = 1, **kwargs: Any) -> RuntimeCandidate:
    return RuntimeCandidate(
        runtime_id=runtime_id,
        catalog_present=kwargs.pop("catalog_present", True),
        live_eligible=kwargs.pop("live_eligible", True),
        availability=kwargs.pop("availability", "ready"),
        signals={"cost_usd": {"value": cost}, **kwargs.pop("signals", {})},
        capabilities=list(kwargs.pop("capabilities", [])),
    )


def snapshot(
    *candidates: RuntimeCandidate, state: str = "ready", ttl_seconds: int = 60
) -> AvailabilitySnapshot:
    return AvailabilitySnapshot(
        observed_at=NOW.isoformat(),
        state=state,
        ttl_seconds=ttl_seconds,
        candidates=list(candidates),
    )


def test_no_eligible_candidates_records_all_exclusions() -> None:
    result = SwarmDispatcher().dispatch(
        snapshot(
            candidate("unknown", catalog_present=False),
            candidate("quota", availability="quota_exhausted"),
        ),
        now=NOW,
    )
    assert result.selected is None
    assert result.reason == "no eligible candidates"
    assert all(item.reasons for item in result.explanations)


def test_selects_cheapest_eligible_candidate_and_is_dry_run() -> None:
    result = SwarmDispatcher().dispatch(
        snapshot(candidate("expensive", cost=2), candidate("cheap", cost=0.1)), now=NOW
    )
    assert result.selected is not None
    assert result.selected.runtime_id == "cheap"
    assert result.estimated_cost == 0.1
    assert result.dry_run is True
    assert any(item.selected for item in result.explanations)


def test_verification_policy_escalates_once_and_records_depth() -> None:
    result = SwarmDispatcher(
        DispatchPolicy(verification_required=True, max_escalation_depth=1)
    ).dispatch(
        snapshot(
            candidate("cheap", cost=0.1),
            candidate("verified", cost=1, capabilities=["verification"]),
        ),
        now=NOW,
    )
    assert result.selected is not None
    assert result.selected.runtime_id == "verified"
    assert result.escalation_depth == 1
    assert next(item for item in result.explanations if item.selected).escalation_depth == 1


def test_outage_and_stale_snapshot_are_closed() -> None:
    outage = SwarmDispatcher().dispatch(snapshot(candidate("a"), state="outage"), now=NOW)
    stale = SwarmDispatcher().dispatch(
        snapshot(candidate("a"), ttl_seconds=1), now=NOW.replace(second=2)
    )
    assert outage.selected is None
    assert "outage" in outage.explanations[0].reasons[0]
    assert stale.selected is None
    assert "stale" in stale.explanations[0].reasons[0]


def test_budget_concurrency_and_timeout_are_hard_limits() -> None:
    policy = DispatchPolicy(max_budget=1, max_concurrency=2, timeout_seconds=1)
    result = SwarmDispatcher(policy).dispatch(
        snapshot(
            candidate("over-budget", cost=2),
            candidate("busy", cost=0.1, signals={"concurrency": 2}),
            candidate("slow", cost=0.1, signals={"latency_ms": 1001}),
        ),
        now=NOW,
    )
    assert result.selected is None
    reasons = {reason for item in result.explanations for reason in item.reasons}
    assert {
        "budget limit exceeded",
        "concurrency limit reached",
        "timeout limit exceeded",
    } <= reasons
