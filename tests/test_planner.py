from __future__ import annotations

import pytest

from llm_gate.contracts import TaskSpec, WorkflowPlan
from llm_gate.planner import (
    FailureClass,
    PlannerPolicy,
    PlanningUnavailable,
    PlanRejected,
    StructuredPlanner,
    WorkflowKind,
)


def test_planner_returns_valid_typed_task_and_workflow() -> None:
    result = StructuredPlanner().plan("Research the API and implement it with tests")

    assert isinstance(result.task_spec, TaskSpec)
    assert isinstance(result.workflow_plan, WorkflowPlan)
    assert result.task_spec.effort == "high"
    assert result.workflow_plan.metadata["workflow"] == WorkflowKind.RESEARCH_IMPLEMENT.value
    assert result.workflow_plan.verification.checks


def test_unavailable_planner_uses_deterministic_fallback() -> None:
    def unavailable(_: dict[str, object]) -> dict[str, object]:
        raise PlanningUnavailable("planner offline")

    planner = StructuredPlanner(unavailable)
    first = planner.plan("Format a JSON document", criticality="low")
    second = planner.plan("Format a JSON document", criticality="low")

    assert first == second
    assert first.metadata["planner_mode"] == "deterministic-fallback"
    assert first.task_spec.to_dict()["criticality"] == "low"


def test_criticality_alone_does_not_select_a_model() -> None:
    low = StructuredPlanner().plan("Summarize a document", criticality="low")
    critical = StructuredPlanner().plan("Summarize a document", criticality="critical")

    assert low.task_spec.required_capabilities == critical.task_spec.required_capabilities
    assert low.task_spec.task_type == critical.task_spec.task_type
    assert low.workflow_plan.metadata["model"] is None
    assert critical.workflow_plan.metadata["model"] is None


def test_capability_requirements_uses_current_task_contract_fields() -> None:
    task = TaskSpec(
        objective="Implement a tested API client",
        task_type="implementation_then_test",
        effort="high",
        reasoning="high",
        tools=["shell", "editor"],
        required_capabilities=["tool-calling"],
        verification={"checks": ["pytest -q"]},
        production_impact=True,
    )

    requirements = StructuredPlanner.capability_requirements(task)

    assert requirements == {
        "reasoning": "high",
        "tools": ["editor", "shell"],
        "required_capabilities": ["tool-calling"],
        "effort": "high",
        "verification": {"checks": ["pytest -q"]},
        "production_impact": True,
    }


def test_planner_output_cannot_weaken_policy() -> None:
    def malicious(_: dict[str, object]) -> dict[str, object]:
        return {
            "task_spec": {
                "objective": "deploy production",
                "task_type": "deployment",
                "criticality": "low",
                "production_impact": False,
                "degraded_mode_policy": "allow",
                "budget": {"max_usd": 0.01},
            },
            "workflow_plan": {
                "steps": [{"action": "execute", "model": "cheap/unverified"}],
                "fallback_allowed": True,
                "metadata": {"policy_floor": "none", "model": "cheap/unverified"},
            },
        }

    result = StructuredPlanner(malicious).plan("deploy production", criticality="critical")

    assert result.task_spec.production_impact is True
    assert result.task_spec.criticality == "critical"
    assert result.task_spec.degraded_mode_policy == "deny"
    assert result.workflow_plan.fallback_allowed is False
    assert result.workflow_plan.metadata["model"] is None
    assert result.workflow_plan.metadata["policy_floor"] == "protected"
    assert "human_approval" in [step["action"] for step in result.workflow_plan.steps]


def test_over_budget_plan_is_rejected() -> None:
    planner = StructuredPlanner(policy=PlannerPolicy(max_cost_usd=1.0))
    with pytest.raises(PlanRejected, match="budget"):
        planner.plan("Implement a large distributed system", budget={"max_usd": 0.01})


def test_failure_classification_and_bounded_replanning() -> None:
    planner = StructuredPlanner(policy=PlannerPolicy(max_replans=1))
    assert planner.classify_failure("429 quota exceeded") is FailureClass.QUOTA_EXHAUSTION
    assert planner.classify_failure("permission denied by tool") is FailureClass.PERMISSION_DENIAL
    assert planner.classify_failure("pytest failed") is FailureClass.TEST_FAILURE

    result = planner.replan(
        planner.plan("Implement a feature"),
        "provider timeout",
        attempt=1,
    )
    assert result.workflow_plan.metadata["replan_reason"] == FailureClass.PROVIDER_FAILURE.value
    with pytest.raises(PlanRejected, match="replan"):
        planner.replan(result, "provider timeout", attempt=2)
