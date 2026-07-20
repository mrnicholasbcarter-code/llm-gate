"""Single-source-of-truth eligibility gate pre-ranking filtering."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from verdict.availability import AvailabilityReport, AvailabilityState
from verdict.models import ModelInfo


class EligibilityVerdict(str, Enum):
    """Why candidate kept/excluded by gate."""
    ELIGIBLE = "eligible"
    NOT_LIVE_ELIGIBLE = "not_live_eligible"
    RUNTIME_TRUTH_ABSENT = "runtime_truth_absent"
    NOT_REQUESTED_TIER = "not_requested_tier"


# States that admit a candidate into the pre-ranking eligible set
_ADMITTED_STATES = frozenset([
    AvailabilityState.ELIGIBLE,
    AvailabilityState.READY,
    AvailabilityState.DEGRADED,
])


@dataclass(frozen=True)
class EligibilityRecord:
    """Per-candidate gate outcome, preserved for explain endpoint."""
    model_id: str
    provider: str
    admitted: bool
    verdict: str
    state: str
    source: str
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "admitted": self.admitted,
            "verdict": self.verdict,
            "state": self.state,
            "source": self.source,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class EligibilityResult:
    """Aggregated gate result."""
    eligible: list[ModelInfo]
    records: list[EligibilityRecord]

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": [m.id for m in self.eligible],
            "exclusions": [r.to_dict() for r in self.records if not r.admitted],
        }


def _mock_availability_source(model_id: str) -> AvailabilityReport:
    """Mock availability source for CLI when no OmniRoute configured."""
    from verdict.availability import AvailabilityCandidate
    return AvailabilityReport(
        candidates=(),
        eligible=(),
        source="mock",
        freshness_seconds=0,
        errors=(),
    )


class EligibilityGate:
    """Filter candidates by live eligibility before any ranking.

    Single authority consulted by router, dispatcher, explain endpoint.
    Downstream ranker MUST NOT reintroduce excluded candidate (issue #57).
    """

    def __init__(
        self,
        availability_source: Callable[[str], AvailabilityReport] | None = None,
        protected_fail_closed: bool = True,
        allow_unverified_in_dev: bool = True,
        clock: Any | None = None,
    ) -> None:
        # If no source provided, use mock (CLI mode without OmniRoute)
        self.availability_source = availability_source or _mock_availability_source
        self.protected_fail_closed = protected_fail_closed
        self.allow_unverified_in_dev = allow_unverified_in_dev

    def evaluate(
        self,
        candidates: list[ModelInfo],
        protected: bool = False,
        dev_mode: bool = False,
        now: Any | None = None,
    ) -> EligibilityResult:
        """Filter candidates pre-ranking into eligible set."""
        records: list[EligibilityRecord] = []
        eligible: list[ModelInfo] = []

        for model in candidates:
            report = self.availability_source(model.id)
            
            # Find candidate in report
            candidate = next((c for c in report.candidates if c.model_id == model.id), None)
            
            if candidate is None:
                # Model not in availability report
                if protected and self.protected_fail_closed:
                    verdict = EligibilityVerdict.RUNTIME_TRUTH_ABSENT
                    admitted = False
                    reason = "not in availability report (protected mode)"
                elif dev_mode and self.allow_unverified_in_dev:
                    verdict = EligibilityVerdict.ELIGIBLE
                    admitted = True
                    reason = "dev mode: unverified admission"
                else:
                    verdict = EligibilityVerdict.NOT_LIVE_ELIGIBLE
                    admitted = False
                    reason = "not in availability report"
                state = "unknown"
                source = "mock"
            else:
                state = candidate.state.value
                source = report.source
                if candidate.state in _ADMITTED_STATES:
                    verdict = EligibilityVerdict.ELIGIBLE
                    admitted = True
                    reason = None
                else:
                    verdict = EligibilityVerdict.NOT_LIVE_ELIGIBLE
                    admitted = False
                    reason = candidate.state.value

            record = EligibilityRecord(
                model_id=model.id,
                provider=model.provider,
                admitted=admitted,
                verdict=verdict.value,
                state=state,
                source=source,
                reason=reason,
            )
            records.append(record)
            if admitted:
                eligible.append(model)

        return EligibilityResult(eligible=eligible, records=records)
