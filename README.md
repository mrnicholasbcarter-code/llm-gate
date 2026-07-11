<p align="center">
  <img src="https://raw.githubusercontent.com/mrnicholasbcarter-code/llm-gate/main/docs/logo.svg" width="120" alt="llm-gate logo" />
</p>

<h1 align="center">llm-gate</h1>

<p align="center">
  <strong>Route LLM tasks by criticality. Never send prod code to a cheap model.<br/>Never burn $20/hr on formatting.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/llm-gate/"><img src="https://img.shields.io/pypi/v/llm-gate?color=blue" alt="PyPI" /></a>
  <a href="https://github.com/mrnicholasbcarter-code/llm-gate/actions"><img src="https://img.shields.io/github/actions/workflow/status/mrnicholasbcarter-code/llm-gate/ci.yml?label=tests" alt="Tests" /></a>
  <a href="https://github.com/mrnicholasbcarter-code/llm-gate/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License" /></a>
  <a href="https://pepy.tech/project/llm-gate"><img src="https://img.shields.io/pepy/dt/llm-gate?color=orange" alt="Downloads" /></a>
</p>

---

## The Problem

You're paying for Claude Opus / GPT-4o / Grok-3 to reformat JSON, summarize logs, and lint docstrings.

Meanwhile, your production database migrations, security reviews, and payment integrations are getting the same model as your throwaway scripts.

**Most LLM costs come from sending the wrong task to the wrong model.**

## The Solution

```python
from llm_gate import Gate

gate = Gate()  # auto-discovers models from any OpenAI-compatible endpoint

result = gate.route(
    task="Refactor this auth module to use JWT refresh tokens",
    criticality="high",  # or: "critical", "medium", "low"
)

print(result.model)     # → "claude-sonnet-4-20250514"
print(result.provider)  # → "anthropic"
print(result.reason)    # → "high criticality + auth/security keywords → tier 2"
```

```python
# Critical path — NEVER offloads to a cheap model
result = gate.route(
    task="Review this payment processing function for edge cases",
    criticality="critical",
)
# result.model → your most capable model, always

# Bulk work — sends to the cheapest model with capacity
result = gate.route(
    task="Add type hints to these 50 utility functions",
    criticality="low",
)
# result.model → "gemini-2.5-flash" (free tier, plenty of capacity)
```

## Features

- **4 criticality tiers** — `critical` / `high` / `medium` / `low`. Critical tasks never leave your best model.
- **Auto-discovery** — Queries any OpenAI-compatible `/v1/models` endpoint. No hardcoded model lists.
- **Capability classification** — Automatically tiers models by ID pattern (`opus`/`gpt-4o` → high, `flash`/`mini` → low).
- **Quota-aware** — Checks provider rate limits and remaining capacity before routing.
- **Keyword escalation** — Detects `auth`, `payment`, `security`, `migration`, `prod` in tasks and bumps criticality.
- **Decision logging** — Every routing decision logged as structured JSONL for cost analysis and ML training.
- **Fail-open** — If no offload model is available, falls back to your primary model. Never blocks.
- **Provider-agnostic** — Works with OpenAI, Anthropic, Google, Groq, Together, Fireworks, Cerebras, Mistral, local Ollama, or any OpenAI-compatible proxy.
- **Zero dependencies** — Pure Python. No heavy frameworks. Installs in < 1 second.

## Install

```bash
pip install llm-gate
```

## Quick Start

### 1. Minimal (auto-discover from one endpoint)

```python
from llm_gate import Gate

gate = Gate(
    providers={"openrouter": {"base_url": "https://openrouter.ai/api/v1"}},
    primary_model="anthropic/claude-sonnet-4",
)

decision = gate.route("Add error handling to this database connector", criticality="high")
# → Routes to best available model that meets "high" tier
```

### 2. Multi-provider with config file

```yaml
# llm-gate.yaml
primary_model: "anthropic/claude-sonnet-4"

providers:
  anthropic:
    base_url: "https://api.anthropic.com/v1"
    api_key_env: "ANTHROPIC_API_KEY"
  groq:
    base_url: "https://api.groq.com/openai/v1"
    api_key_env: "GROQ_API_KEY"
  ollama:
    base_url: "http://localhost:11434/v1"

tiers:
  critical:
    keywords: ["payment", "auth", "security", "migration", "production", "deploy"]
    never_offload: true
  high:
    prefer_models: ["claude-sonnet", "gpt-4o", "grok-3"]
  medium:
    prefer_models: ["claude-haiku", "gpt-4o-mini", "llama-3.3-70b"]
  low:
    prefer_models: ["gemini-flash", "llama-3.1-8b", "qwen-2.5-coder"]

escalation_patterns:
  - pattern: "(payment|billing|charge|refund|stripe)"
    min_tier: "critical"
  - pattern: "(auth|login|token|session|password|jwt)"
    min_tier: "high"
  - pattern: "(migration|schema|alter table|deploy)"
    min_tier: "high"
```

```python
from llm_gate import Gate

gate = Gate.from_yaml("llm-gate.yaml")
decision = gate.route("Format these log lines as CSV", criticality="low")
```

### 3. As a CLI

```bash
# Route a task and print the decision
llm-gate route "Review this SQL injection fix" --criticality high

# Show discovered models and their tiers
llm-gate models

# Analyze routing history
llm-gate stats --last 7d
```

## How Routing Works

```
Task arrives → Keyword scan → Criticality floor applied
                                     ↓
                            Tier determined (T0-T3)
                                     ↓
                   ┌─────────────────┴─────────────────┐
                   │                                     │
              T0: CRITICAL                        T1-T3: OFFLOADABLE
              Never offload.                      Find best model at tier.
              Use primary model.                  Check quota headroom.
                   │                              Prefer cheapest adequate.
                   │                                     │
                   │                              ┌──────┴──────┐
                   │                              │             │
                   │                          Available?   Exhausted?
                   │                              │             │
                   │                         Use offload   Fail open →
                   │                           model      primary model
                   ↓                              ↓             ↓
                Return                         Return       Return
               Decision                       Decision     Decision
```

## Decision Logging

Every routing decision is appended to a JSONL log:

```json
{
  "ts": "2026-07-11T18:30:00Z",
  "task_hash": "a1b2c3d4",
  "task_preview": "Review this SQL injection...",
  "input_criticality": "high",
  "effective_criticality": "high",
  "escalation_reason": null,
  "model_chosen": "anthropic/claude-sonnet-4",
  "tier": 2,
  "provider": "anthropic",
  "alternatives_considered": ["groq/llama-3.3-70b", "google/gemini-flash"],
  "quota_headroom_pct": 72.5,
  "latency_ms": 12,
  "reason": "high tier, best available model with headroom"
}
```

Use this data to:
- **Analyze spend** — See which tiers consume which models
- **Train a contextual router** — Feed embeddings + quality scores to learn task-model fit
- **Debug routing** — Understand why a specific task went to a specific model

## Benchmarks

| Scenario | Without llm-gate | With llm-gate | Savings |
|----------|-----------------|---------------|---------|
| 100 mixed dev tasks | $47.20 (all Claude Opus) | $12.80 (routed) | **73%** |
| CI/CD pipeline (lint + review + deploy) | $8.50/run | $3.10/run | **64%** |
| Bulk refactoring (200 files) | $156.00 | $28.40 | **82%** |

*Benchmarks from real usage on a 57,000-line Python codebase. Your results will vary by task mix and provider pricing.*

## API Reference

### `Gate`

```python
Gate(
    providers: dict[str, ProviderConfig] = None,  # provider name → config
    primary_model: str = None,                     # model that handles critical tasks
    config_path: str = None,                       # path to YAML config
    log_path: str = "llm-gate-decisions.jsonl",    # routing decision log
    discovery_ttl: int = 60,                       # seconds to cache /v1/models
)
```

### `Gate.route()`

```python
gate.route(
    task: str,                          # task description or prompt
    criticality: str = "medium",        # "critical" | "high" | "medium" | "low"
    context: dict = None,               # optional metadata (file path, language, etc.)
) -> RoutingDecision
```

### `RoutingDecision`

```python
@dataclass
class RoutingDecision:
    model: str              # chosen model ID
    provider: str           # provider name
    tier: int               # 0 (critical) to 3 (low)
    reason: str             # human-readable explanation
    alternatives: list      # other models considered
    headroom_pct: float     # remaining quota percentage
    latency_ms: float       # routing decision time
    escalated: bool         # was criticality bumped by keywords?
    logged: bool            # was decision written to log?
```

## Comparison

| Feature | llm-gate | LiteLLM | Martian | OpenRouter |
|---------|----------|---------|---------|------------|
| Criticality-based routing | ✅ | ❌ | ✅ | ❌ |
| Auto model discovery | ✅ | ❌ | ❌ | ❌ |
| Keyword escalation | ✅ | ❌ | ❌ | ❌ |
| Quota-aware routing | ✅ | ❌ | ✅ | Partial |
| Decision logging for ML | ✅ | ❌ | ❌ | ❌ |
| Self-hosted | ✅ | ✅ | ❌ (SaaS) | ❌ (SaaS) |
| Zero dependencies | ✅ | ❌ | N/A | N/A |
| Free | ✅ | ✅ | ❌ | ❌ |

## Philosophy

1. **Critical code never touches a cheap model.** Payment logic, auth flows, database migrations, and production deployments always go to your best model. No exceptions.

2. **Cheap work never touches an expensive model.** Formatting, linting, type hints, log summarization, and boilerplate generation go to the fastest, cheapest model with capacity.

3. **Fail open, never block.** If every offload model is rate-limited or down, the task goes to your primary model. Work never stops.

4. **No magic, no ML required.** The default router is a simple tier + keyword matcher. It works out of the box. The decision log lets you build an ML router later if you want to.

5. **Zero vendor lock-in.** Works with any OpenAI-compatible endpoint. Swap providers by editing one YAML file.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT. See [LICENSE](LICENSE).
