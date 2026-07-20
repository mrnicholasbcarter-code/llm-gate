"""Core data models for Verdict."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class RoutingDecision:
    """Result of a routing decision.
    
    Contains the chosen model, the effective tier, and metadata.
    Returned by `Gate.route()`.
    """
    selected_model: str
    """Chosen model ID (e.g., 'anthropic/claude-3-opus-20240229')."""
    effective_tier: int
    """Effective criticality tier (0=critical, 3=low)."""
    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata (reasoning, freshness, etc.)."""


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for a single LLM provider."""
    models: dict[str, ModelConfig] = field(default_factory=dict)
    """Model-specific configs for this provider."""


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for a specific model within a provider."""
    capabilities: list[str] = field(default_factory=list)
    """Capabilities this model supports (tools, vision, reasoning, etc.)."""
    pricing: dict[str, float] = field(default_factory=dict)
    """Pricing per 1k tokens (input, output, etc.)."""


class ModelInfo(BaseModel):
    """Model information from catalog."""
    id: str = Field(..., description="Model ID (provider/model)")
    provider: str = Field(..., description="Provider name")
    model: str = Field(..., description="Model name")
    capability_tier: int = Field(default=1, description="Capability tier")
    capabilities: list[str] = Field(default_factory=list)
    pricing: dict[str, float] = Field(default_factory=dict)
    # Additional fields from normalize_catalog
    is_available: bool = Field(default=False, description="Whether model is available")
    availability_state: str = Field(default="unknown", description="Availability state")
    source: str = Field(default="catalog", description="Source of model info")
    context_window: int = Field(default=-1, description="Context window size")


class TaskSpec(BaseModel):
    """Normalized task specification for routing."""
    prompt: str = Field(..., description="Task prompt")
    criticality: str = Field(default="medium", description="Criticality level")
    context: dict[str, Any] = Field(default_factory=dict)
    requirements: list[str] = Field(default_factory=list)
    budget_per_1k: float | None = None
    privacy_level: str = Field(default="standard")


class RoutingDecisionContract(BaseModel):
    """Versioned routing decision contract."""
    version: str = "1.0"
    task_spec: TaskSpec
    decision: RoutingDecision
    eligibility: dict[str, Any] = Field(default_factory=dict)
    intelligence: dict[str, Any] = Field(default_factory=dict)
