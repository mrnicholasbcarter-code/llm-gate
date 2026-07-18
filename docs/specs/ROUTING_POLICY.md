# llm-gate Routing Policy
## Best-appropriate-model selection contract

### 1. Objective

Choose the highest expected-quality model that satisfies every hard requirement and is currently eligible. The selector is not a cheapest-model sorter. Cost may break ties or be used only when the user explicitly selects a cost-ceiling mode.

Every request passes through the mandatory `IntelligenceService`. Its deterministic component evaluates policy, capabilities, availability, and explainability. In the production profile, its managed Ruflo/RuVector component supplies a bounded adaptive signal. Adaptive intelligence can rank eligible candidates, but it can never override hard policy.

The decision must be deterministic for identical inputs, catalog state, policy version, and learned-policy snapshot.

### 2. Candidate states

Every discovered model is normalized into an explicit availability state:

- `ready`: catalog metadata is valid and the last health/headroom signal permits use.
- `degraded`: elevated latency or low remaining quota; rejected by default and usable
  only for non-protected work with an explicit `allow_degraded` opt-in.
- `unknown`: present in the catalog but not verified. Unknown is not treated as ready by default.
- `denied`: removed by policy, unsupported capability, privacy restriction, or failed hard gate.
- `unavailable`, `quota_exhausted`, `rate_limited`, `unauthorized`, `locked_out`,
  `circuit_open`, `timeout`, and `malformed`: stable hard-exclusion states with
  redacted explanations.

OmniRoute's `/v1/models` response is a synchronized catalog. It can contain models that are not currently usable. llm-gate MUST apply its own allowlist, denylist, metadata overrides, and optional bounded health probes. An OmniRoute API key's `allowed_models` restriction does not necessarily filter the catalog response, so local filtering is mandatory.

### 3. Requirement vector

The request classifier produces:

```text
TaskRequirements {
  task_class: security | auth | payments | live_execution | production_deploy |
              architecture | debugging | implementation | tests | docs | formatting | unknown
  minimum_quality_confidence: 0..1
  reasoning_level: none | low | medium | high | frontier
  coding_level: none | low | medium | high
  context_tokens_required: integer | unknown
  tools_required: boolean
  structured_output_required: boolean
  vision_required: boolean
  streaming_required: boolean
  latency_budget_ms: integer | unknown
  estimated_tokens: non-negative integer
  estimated_cost_usd: finite non-negative number
  budget_remaining_usd: finite non-negative number | unknown
  privacy_class: local_only | trusted_upstream | any
  protected: boolean
}
```

The classifier MUST combine explicit user policy, request shape, known tool fields, model/client hints, deterministic lexical signals, and the bounded IntelligenceService signal. A learned suggestion can increase confidence or rank candidates but cannot lower `protected`, required capability, or a configured quality floor.

### 4. Hard gates

Hard gates run before scoring:

1. Protected task classes require a frontier allowlist or an explicitly validated model policy. A generic name match is not sufficient to lower the floor.
2. A model without required tool calling, structured output, vision, context, or streaming capability is rejected.
3. A denied provider/model, privacy-incompatible provider, stale catalog row, or failed health policy is rejected.
4. A request with unknown risk and a protected keyword is escalated, never downgraded.
5. An upstream response already started streaming cannot be retried or silently switched.
6. User-specified `model` is treated as a preference only when `allow_client_model_override=false`; direct override requires an explicit policy flag.
7. Estimated request tokens must fit the candidate's normalized `token_headroom`
   (or `tokens_remaining` alias). Estimated cost must fit the smallest known
   request-policy or runtime budget.
8. Missing token or cost headroom degrades the candidate and requires an explicit
   non-protected opt-in. Protected work never admits degraded capacity evidence.
9. A request that exceeds known token or budget headroom is denied before ranking.

#### 4.1 Conservative capacity reservations

The deterministic planner emits an explicit `deterministic_effort_reservation_v1`
admission reservation:

| Effort | Reserved tokens | Reserved cost (USD) | Reserved latency (ms) |
| --- | ---: | ---: | ---: |
| low | 1,024 | 0.05 | 2,000 |
| medium | 8,192 | 1.00 | 15,000 |
| high | 32,768 | 5.00 | 60,000 |

These values are conservative routing reservations, not tokenizer output,
observed usage, pricing estimates, or billing records. They provide deterministic
floors until a versioned model-aware estimator is introduced. A structured or
learned planner may raise a reservation but cannot lower these floors. Invalid,
negative, non-finite, fractional token, or boolean estimates are rejected at the
planning or availability boundary.

Capacity reasons are stable and machine-readable: `token headroom unknown`,
`token headroom exceeded`, `budget headroom unknown`, and
`budget headroom exceeded`.

When both token-headroom aliases are present, they must agree or the observation
is malformed. When planned and runtime cost estimates are both present, the
larger estimate is checked against the smallest known budget.

### 5. Scoring

For each eligible candidate, calculate a score with normalized components:

```text
score =
  0.35 * quality_confidence
+ 0.20 * capability_fit
+ 0.15 * observed_reliability
+ 0.10 * context_fit
+ 0.08 * availability_headroom
+ 0.07 * latency_fit
+ 0.05 * policy_preference
- penalties
```

The weights are configuration, not a hidden constant. For protected tasks, quality and capability weights increase and cost contributes zero. For formatting/docs tasks, quality still has a floor; the router may prefer a fast model only after it remains above that floor.

Tie-breakers, in order:

1. Higher measured quality confidence.
2. Higher capability fit.
3. Higher observed reliability.
4. More remaining headroom.
5. Lower latency.
6. Lower cost only if all preceding values are within configured tolerance.
7. Stable model ID order.

The decision explanation MUST expose the score components and rejected candidates without exposing secrets or raw prompts.

### 6. Intelligence and learning contract

The IntelligenceService is mandatory. Its adaptive learning signal is advisory and bounded:

- Warm-up period: use deterministic policy until a model/task bucket has at least `N` validated outcomes.
- Every learned adjustment is clamped to `±learned_policy_max_adjustment`.
- A quality failure, safety escalation, test failure, malformed tool call, or user rejection decreases confidence for the exact model/task bucket.
- A transport success alone is not a quality success.
- Policy changes invalidate or version learned snapshots.
- The router records the chosen model, candidate set, policy version, features, and delayed outcome ID.
- A missing or unhealthy managed adaptive backend makes the production profile not-ready. Explicit degraded development mode continues with the deterministic safety floor and marks every decision accordingly.

### 7. Fallback contract

Fallback is a new candidate selection under the same requirements, not an unconditional downgrade.

- Retry only idempotent requests or requests explicitly marked retry-safe.
- Honor `Retry-After` and bounded retry budgets.
- For protected tasks, fallback candidates must satisfy the same hard floor.
- For non-protected tasks, fallback may move to the next highest-scoring eligible model, never directly to an arbitrary cheap model.
- Return an explicit `x-llm-gate-fallback` header and decision event.

### 8. Explainability schema

```json
{
  "request_id": "...",
  "policy_version": "...",
  "task_class": "implementation",
  "protected": false,
  "requirements": {"tools": true, "reasoning": "medium"},
  "candidates": [
    {"model": "...", "state": "ready", "score": 0.84, "rejected": false},
    {"model": "...", "state": "unknown", "rejected": true, "reason": "unverified"}
  ],
  "selected": "...",
  "learned_influence": {"enabled": true, "adjustment": 0.04},
  "fallbacks": ["..."],
  "latency_ms": 4.8
}
```

### 9. Testable policy examples

- A formatting request with tools required must not select a model lacking tool support, even if it is free.
- An auth migration request must not select an unknown or unverified model.
- A medium implementation request selects the highest-scoring ready model, not the lowest-cost model.
- If all eligible models are unknown, the router follows explicit `unknown_availability` policy and explains the result.
- A learned score cannot make a denied model eligible.
- A failed first request cannot trigger a retry after the first SSE byte.
