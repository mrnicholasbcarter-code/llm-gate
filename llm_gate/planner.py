"""Structured task intake and bounded workflow planning."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from llm_gate.contracts import TaskSpec, VerificationPlan, WorkflowPlan


class PlanningUnavailableError(RuntimeError):
    """Raised when the optional planning provider cannot be reached."""


class PlanRejectedError(ValueError):
    """Raised when a plan violates deterministic planner policy."""


class WorkflowKind(str, Enum):
    SINGLE = "single_model"
    RESEARCH_IMPLEMENT = "research_then_implementation"
    IMPLEMENT_REVIEW = "implementation_then_review"
    IMPLEMENT_TEST = "implementation_then_test"
    PARALLEL = "parallel_specialists"
    SEQUENTIAL = "sequential_specialist_pipeline"
    APPROVAL = "human_approval_workflow"
    HUMAN_APPROVAL = "human_approval_workflow"


class FailureClass(str, Enum):
    PROVIDER_FAILURE = "provider_failure"
    QUOTA_EXHAUSTION = "quota_exhaustion"
    TOOL_FAILURE = "tool_failure"
    PERMISSION_DENIAL = "permission_denial"
    TEST_FAILURE = "test_failure"
    PLAN_FAILURE = "plan_failure"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PlannerPolicy:
    max_cost_usd: float | None = 20.0
    max_replans: int = 1
    protected_keywords: tuple[str, ...] = (
        "production",
        "deploy",
        "delete",
        "credential",
        "secret",
        "security",
    )


@dataclass(frozen=True)
class PlanResult:
    task_spec: TaskSpec
    workflow_plan: WorkflowPlan
    metadata: dict[str, Any]


PlannerCallable = Callable[[dict[str, Any]], dict[str, Any]]

# Compatibility names used by the public planner API and fixtures.
PlanningUnavailable = PlanningUnavailableError
PlanRejected = PlanRejectedError
PlanningResult = PlanResult


class StructuredPlanner:
    """Produce validated task/workflow contracts without selecting a model."""

    def __init__(
        self,
        planner: PlannerCallable | None = None,
        *,
        policy: PlannerPolicy | None = None,
    ) -> None:
        self.planner = planner
        self.policy = policy or PlannerPolicy()

    def plan(
        self,
        objective: str,
        *,
        criticality: str = "unknown",
        budget: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> PlanResult:
        if not objective.strip():
            raise PlanRejected("objective is required")
        request: dict[str, Any] = {
            "objective": objective,
            "criticality": criticality,
            "budget": budget or {},
            "context": context or {},
        }
        try:
            proposed = self.planner(request) if self.planner else None
            if proposed is None:
                result = self._deterministic(request)
                mode = "deterministic"
            else:
                result = self._sanitize_proposal(request, proposed)
                mode = "structured"
        except PlanningUnavailable:
            result = self._deterministic(request)
            mode = "deterministic-fallback"
        self._enforce_budget(result.task_spec, budget)
        return replace(result, metadata={**result.metadata, "planner_mode": mode})

    def replan(self, result: PlanResult, failure: str, *, attempt: int) -> PlanResult:
        if attempt < 1 or attempt > self.policy.max_replans:
            raise PlanRejected("replan limit exceeded")
        failure_class = self.classify_failure(failure)
        workflow = result.workflow_plan
        metadata = {
            **workflow.metadata,
            "replan_reason": failure_class.value,
            "replan_attempt": attempt,
            "alternate_route_required": failure_class
            in {FailureClass.PROVIDER_FAILURE, FailureClass.QUOTA_EXHAUSTION},
            "human_escalation": failure_class is FailureClass.PERMISSION_DENIAL,
            "cancellation_allowed": failure_class
            in {FailureClass.PERMISSION_DENIAL, FailureClass.PLAN_FAILURE},
            "rollback_required": result.task_spec.destructive_operation,
        }
        return replace(
            result,
            workflow_plan=replace(workflow, metadata=metadata),
            metadata={**result.metadata, "replan_reason": failure_class.value},
        )

    @staticmethod
    def classify_failure(message: str) -> FailureClass:
        value = message.lower()
        if any(token in value for token in ("429", "quota", "rate limit", "headroom")):
            return FailureClass.QUOTA_EXHAUSTION
        if any(token in value for token in ("permission", "forbidden", "unauthorized")):
            return FailureClass.PERMISSION_DENIAL
        if any(token in value for token in ("pytest", "test failed", "verification failed")):
            return FailureClass.TEST_FAILURE
        if any(token in value for token in ("tool", "command failed")):
            return FailureClass.TOOL_FAILURE
        if any(token in value for token in ("timeout", "provider", "upstream", "connection")):
            return FailureClass.PROVIDER_FAILURE
        if any(token in value for token in ("plan", "assumption")):
            return FailureClass.PLAN_FAILURE
        return FailureClass.UNKNOWN

    def _deterministic(self, request: dict[str, Any]) -> PlanResult:
        objective = str(request["objective"])
        lower = objective.lower()
        criticality = str(request["criticality"])
        protected = criticality in {"critical", "high"} or any(
            keyword in lower for keyword in self.policy.protected_keywords
        )
        steps: list[dict[str, Any]]
        if any(word in lower for word in ("parallel", "independent specialists")):
            kind = WorkflowKind.PARALLEL
            steps = [{"action": "specialist", "parallel": True}, {"action": "synthesis"}]
            effort = "high"
        elif any(word in lower for word in ("pipeline", "sequential", "decompose")):
            kind = WorkflowKind.SEQUENTIAL
            steps = [{"action": "specialist"}, {"action": "synthesis"}]
            effort = "high"
        elif any(word in lower for word in ("research", "investigate")) and any(
            word in lower for word in ("implement", "build", "write", "code")
        ):
            kind = WorkflowKind.RESEARCH_IMPLEMENT
            steps = [
                {"action": "research", "verification": "sources"},
                {"action": "implement", "verification": "tests"},
            ]
            effort = "high"
        elif any(word in lower for word in ("review", "audit")):
            kind = WorkflowKind.IMPLEMENT_REVIEW
            steps = [{"action": "review"}, {"action": "verify"}]
            effort = "medium"
        elif any(word in lower for word in ("test", "fix", "implement", "build")):
            kind = WorkflowKind.IMPLEMENT_TEST
            steps = [{"action": "implement"}, {"action": "verify"}]
            effort = "medium"
        else:
            kind = WorkflowKind.SINGLE
            steps = [{"action": "answer"}]
            effort = "low"
        if protected:
            steps.insert(0, {"action": "human_approval", "required": True})
        verification = VerificationPlan(
            checks=["tests" if kind != WorkflowKind.SINGLE else "response_schema"],
            on_failure="replan_or_deny",
        )
        task = TaskSpec(
            objective=objective,
            task_type=kind.value,
            effort=effort,
            reasoning="high" if protected or effort == "high" else "medium",
            criticality=criticality,
            required_capabilities=(
                ["tool-calling"]
                if any(word in lower for word in ("implement", "build", "code", "api", "test"))
                else []
            ),
            tools=(
                ["tool-calling"]
                if any(word in lower for word in ("implement", "build", "code", "api", "test"))
                else []
            ),
            budget={
                **dict(request.get("budget") or {}),
                "estimated_usd": {"low": 0.05, "medium": 1.0, "high": 5.0}[effort],
                "estimated_latency_ms": {"low": 2_000, "medium": 15_000, "high": 60_000}[effort],
            },
            context=request.get("context") if isinstance(request.get("context"), dict) else None,
            production_impact=any(word in lower for word in ("production", "deploy")),
            destructive_operation=any(word in lower for word in ("delete", "destroy", "drop")),
            degraded_mode_policy="deny" if protected else "allow_with_penalty",
            verification=verification.to_dict(),
        )
        workflow = WorkflowPlan(
            steps=steps,
            verification=verification,
            fallback_allowed=False,
            metadata={"workflow": kind.value, "model": None, "policy_floor": "protected" if protected else "standard"},
        )
        return PlanResult(task, workflow, {"workflow": kind.value, "model": None})

    def _sanitize_proposal(self, request: dict[str, Any], proposed: dict[str, Any]) -> PlanResult:
        fallback = self._deterministic(request)
        task_payload = proposed.get("task_spec")
        workflow_payload = proposed.get("workflow_plan")
        task = TaskSpec.from_dict(task_payload) if isinstance(task_payload, dict) else fallback.task_spec
        workflow = WorkflowPlan.from_dict(workflow_payload) if isinstance(workflow_payload, dict) else fallback.workflow_plan
        protected = fallback.task_spec.degraded_mode_policy == "deny"
        task = replace(
            task,
            objective=fallback.task_spec.objective,
            criticality=fallback.task_spec.criticality,
            production_impact=fallback.task_spec.production_impact or task.production_impact,
            destructive_operation=fallback.task_spec.destructive_operation or task.destructive_operation,
            degraded_mode_policy="deny" if protected else task.degraded_mode_policy,
            effort=(
                fallback.task_spec.effort
                if {"low": 0, "medium": 1, "high": 2}.get(task.effort, 0)
                < {"low": 0, "medium": 1, "high": 2}.get(fallback.task_spec.effort, 0)
                else task.effort
            ),
            required_capabilities=list(
                dict.fromkeys(
                    [*fallback.task_spec.required_capabilities, *task.required_capabilities]
                )
            ),
        )
        if protected:
            workflow = replace(
                workflow,
                fallback_allowed=False,
                metadata={**workflow.metadata, "model": None, "policy_floor": "protected"},
                steps=[{"action": "human_approval", "required": True}, *workflow.steps],
            )
        else:
            workflow = replace(workflow, metadata={**workflow.metadata, "model": None})
        return PlanResult(task, workflow, {"workflow": workflow.metadata.get("workflow"), "model": None})

    def _enforce_budget(self, task: TaskSpec, budget: dict[str, Any] | None) -> None:
        limit = self.policy.max_cost_usd
        requested = (budget or {}).get("max_usd")
        estimated = float(task.budget.get("estimated_usd", task.budget.get("max_usd", 0)))
        if requested is not None and estimated > float(requested):
            raise PlanRejected("plan exceeds requested budget")
        if limit is not None and estimated > limit:
            raise PlanRejected("budget exceeds planner policy")


# Compatibility names used by integrations that prefer explicit boundaries.
IntakePlanner = StructuredPlanner
WorkflowSelector = StructuredPlanner
