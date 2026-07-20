"""Gate — composes eligibility + intelligence into routing decision."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from verdict.eligibility import EligibilityGate, EligibilityResult, EligibilityRecord
from verdict.intelligence import IntelligenceService, IntelligenceRanking
from verdict.models import ModelInfo, ProviderConfig, TaskSpec, RoutingDecision


@dataclass(frozen=True)
class GateResult:
    """Output of gate check."""
    selected_model: str
    reasoning: str
    eligibility: EligibilityResult
    intelligence: Optional[IntelligenceRanking] = None
    freshness: Optional[float] = None


class Gate:
    """Composes eligibility gate + intelligence ranking."""

    TIER_MAP = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    def __init__(
        self,
        primary_model: str,
        providers: dict[str, ProviderConfig],
        intelligence: Optional[IntelligenceService] = None,
    ) -> None:
        self.primary_model = primary_model
        self.providers = providers
        self.eligibility_gate = EligibilityGate()
        self.intelligence = intelligence

    async def route(
        self,
        task: str,
        criticality: str = "medium",
        context: dict[str, Any] | None = None,
        dev_mode: bool = True,
    ) -> GateResult:
        """Route task to most effective LLM model based on criticality."""
        # Build task spec
        task_spec = TaskSpec(
            prompt=task,
            criticality=criticality,
            context=context or {},
        )

        # Get all candidate models
        candidates = self._build_candidates()
        
        # Eligibility gate (hard filter)
        eligibility = self.eligibility_gate.evaluate(
            candidates=candidates,
            protected=criticality in ("high", "critical"),
            dev_mode=dev_mode,
        )

        # If no eligible, fall back to primary
        if not eligibility.eligible:
            return GateResult(
                selected_model=self.primary_model,
                reasoning=f"No eligible models after gate; falling back to primary {self.primary_model}",
                eligibility=eligibility,
            )

        # Intelligence ranking (advisory only)
        intelligence = None
        if self.intelligence:
            intelligence = await self.intelligence.rank(
                eligible=eligibility.eligible,
                task_spec=task_spec,
            )

        # Select best model
        if intelligence and intelligence.ranked:
            selected = intelligence.ranked[0].model_id
            reasoning = f"Ranked by intelligence: {intelligence.ranked[0].reasoning}"
        else:
            # Fallback: first eligible
            selected = eligibility.eligible[0].id
            reasoning = "First eligible model (no intelligence)"

        return GateResult(
            selected_model=selected,
            reasoning=reasoning,
            eligibility=eligibility,
            intelligence=intelligence,
        )

    def _build_candidates(self) -> list[ModelInfo]:
        """Build candidate models from configured providers."""
        candidates = []
        
        # Add primary model
        candidates.append(ModelInfo(
            id=self.primary_model,
            provider=self.primary_model.split("/")[0] if "/" in self.primary_model else "unknown",
            model=self.primary_model.split("/")[1] if "/" in self.primary_model else self.primary_model,
            capabilities=["tools", "reasoning"],
            max_tokens=128000,
            cost_per_1k=0.0,
        ))
        
        # Add provider models
        for provider_id, provider_config in self.providers.items():
            for model_id, model_config in provider_config.models.items():
                candidates.append(ModelInfo(
                    id=f"{provider_id}/{model_id}",
                    provider=provider_id,
                    model=model_id,
                    capabilities=model_config.get("capabilities", []),
                    max_tokens=model_config.get("max_tokens", 4096),
                    cost_per_1k=model_config.get("cost_per_1k", 0.0),
                ))
        
        return candidates
