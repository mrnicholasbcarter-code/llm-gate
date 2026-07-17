"""Public llm-gate contracts, routing, planning, and availability interfaces."""

from llm_gate.availability import (
    AvailabilityCandidate,
    AvailabilityReport,
    AvailabilityState,
    CandidateRequirements,
    OmniRouteAvailabilityAdapter,
    OmniRouteTransport,
    RuntimeObservation,
    StaticOmniRouteTransport,
)
from llm_gate.contracts import (
    AvailabilitySnapshot,
    CapabilityRequirement,
    ContractValidationError,
    FallbackAttempt,
    LearningEvent,
    OutcomeEvent,
    RoutingDecisionContract,
    RuntimeCandidate,
    TaskSpec,
    VerificationPlan,
    WorkflowPlan,
)
from llm_gate.dispatcher import (
    AssignmentExplanation,
    Dispatcher,
    DispatchPolicy,
    DispatchResult,
    SwarmDispatcher,
)
from llm_gate.gate import Gate
from llm_gate.intelligence import IntelligenceService, ReadinessReport
from llm_gate.models import ModelInfo, ProviderConfig, RoutingDecision
from llm_gate.planner import (
    FailureClass,
    IntakePlanner,
    PlannerPolicy,
    PlanningResult,
    PlanningUnavailable,
    PlanRejected,
    PlanResult,
    StructuredPlanner,
    WorkflowKind,
    WorkflowSelector,
)

__all__ = [
    "AssignmentExplanation",
    "AvailabilityCandidate",
    "AvailabilityReport",
    "AvailabilitySnapshot",
    "AvailabilityState",
    "CandidateRequirements",
    "CapabilityRequirement",
    "ContractValidationError",
    "DispatchPolicy",
    "DispatchResult",
    "Dispatcher",
    "FailureClass",
    "FallbackAttempt",
    "Gate",
    "IntakePlanner",
    "IntelligenceService",
    "LearningEvent",
    "ModelInfo",
    "OmniRouteAvailabilityAdapter",
    "OmniRouteTransport",
    "OutcomeEvent",
    "PlanRejected",
    "PlanResult",
    "PlannerPolicy",
    "PlanningResult",
    "PlanningUnavailable",
    "ProviderConfig",
    "ReadinessReport",
    "RoutingDecision",
    "RoutingDecisionContract",
    "RuntimeCandidate",
    "RuntimeObservation",
    "StaticOmniRouteTransport",
    "StructuredPlanner",
    "SwarmDispatcher",
    "TaskSpec",
    "VerificationPlan",
    "WorkflowKind",
    "WorkflowPlan",
    "WorkflowSelector",
]

__version__ = "0.1.0"
