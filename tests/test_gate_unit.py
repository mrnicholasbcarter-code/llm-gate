"""Unit tests for Gate routing logic."""

from __future__ import annotations

from verdict.gate import Gate


class FakeIntelligence:
    """Stub intelligence that records calls."""

    def __init__(self):
        self.calls = []

    async def rank(self, eligible, task_spec):
        from verdict.intelligence import IntelligenceRanking, RankedCandidate

        self.calls.append((task_spec.prompt, task_spec.criticality, task_spec.context))
        return IntelligenceRanking(
            ranked=[RankedCandidate(model_id="test/model", score=0.9, reasoning="test")],
            task_spec_id=task_spec.prompt[:50],
            profile="test",
        )


def test_critical_is_09():
    assert Gate.COMPLEXITY_MAP["critical"] == 0.9


def test_high_is_07():
    assert Gate.COMPLEXITY_MAP["high"] == 0.7


def test_low_is_02():
    assert Gate.COMPLEXITY_MAP["low"] == 0.2
