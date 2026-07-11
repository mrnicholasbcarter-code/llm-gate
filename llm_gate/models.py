"""Core data models for llm-gate."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RoutingDecision:
    """Result of a routing decision.

    Returned by ``Gate.route()``. Contains the chosen model, the effective tier,
    and metadata about why this model was selected.
    """

    model: str
    """Fully-qualified model ID (e.g., 'anthropic/claude-sonnet-4')."""

    provider: str
    """Provider name from config."""

    tier: int
    """Effective criticality tier (0=critical, 3=low)."""

    reason: str
    """Human-readable routing explanation."""

    alternatives: list[str] = field(default_factory=list)
    """Other models considered but not chosen."""

    headroom_pct: float = -1.0
    """Remaining quota % for chosen model. -1 if unknown."""

    latency_ms: float = 0.0
    """Time to compute routing decision in milliseconds."""

    escalated: bool = False
    """Was criticality bumped by keyword scanner?"""

    escalation_reason: str | None = None
    """Which escalation pattern triggered the bump, if any."""

    logged: bool = False
    """Was this decision written to the JSONL log?"""


@dataclass
class ProviderConfig:
    """Configuration for a single LLM provider."""

    base_url: str
    """API base URL (e.g., 'https://api.groq.com/openai/v1')."""

    api_key: str | None = None
    """Direct API key. Prefer ``api_key_env`` for security."""

    api_key_env: str | None = None
    """Environment variable name containing the API key."""

    models_endpoint: str = "/models"
    """Path to the models listing endpoint."""

    headroom_endpoint: str | None = None
    """Optional path to a quota/usage endpoint."""

    priority: int = 0
    """Higher = preferred when multiple models tie at the same tier."""


@dataclass(frozen=True)
class ModelInfo:
    """Discovered model with auto-classified capability tier."""

    id: str
    """Model ID from /v1/models (e.g., 'claude-sonnet-4-20250514')."""

    provider: str
    """Provider name."""

    capability_tier: int
    """Auto-classified tier: 0 (strongest) to 3 (cheapest/fastest)."""

    context_window: int = -1
    """Max context tokens if available. -1 if unknown."""

    is_available: bool = True
    """Passed headroom check. False if quota exhausted."""


@dataclass(frozen=True)
class EscalationPattern:
    """A regex pattern that bumps task criticality upward."""

    pattern: str
    """Regex pattern to match against task text."""

    min_tier: int
    """Minimum tier if pattern matches (0=critical, 1=high)."""

    label: str
    """Human-readable label for logging."""
