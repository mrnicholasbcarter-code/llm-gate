# Intelligence Adapter Protocol v1
## Normative design for llm-gate issue #7

**Status:** Implementation-blocking specification
**Version:** `intelligence-adapter/v1`
**Scope:** Ruflo/RuVector managed intelligence integration behind the public `IntelligenceService`

## 1. Design invariants

1. `IntelligenceService` is the only component allowed to return a model-selection decision.
2. Deterministic policy, capability, availability, privacy, and explanation logic runs before and after any adaptive call.
3. The managed adapter is advisory for ranking and mandatory for production readiness. It cannot authorize a denied candidate, lower a protected floor, override privacy, or turn an unknown candidate into ready.
4. The local deterministic backend is always available as the safety floor and cold-start path.
5. Production mode fails readiness closed when the managed adapter is unavailable. Development degraded mode is an explicit operator setting and is visible in readiness and every decision event.
6. The public package communicates with Ruflo and RuVector through documented CLI or plugin surfaces only. It never reads their private databases or tables.
7. Raw prompts, completions, credentials, environment values, and provider response bodies are never sent to the adapter by default.

## 2. Configuration contract

The implementation MUST validate configuration at startup:

```text
LLMGATE_INTELLIGENCE_MODE=production|development_degraded
LLMGATE_INTELLIGENCE_TIMEOUT_MS=250          # positive bounded integer
LLMGATE_INTELLIGENCE_ADAPTER=managed|local
LLMGATE_RUFLO_COMMAND=ruflo                 # executable name or absolute path
LLMGATE_RUVECTOR_COMMAND=ruvector            # executable name or absolute path
LLMGATE_POLICY_VERSION=policy-YYYY-MM-DD.N
LLMGATE_PRIVACY_MODE=redacted|local_only
LLMGATE_LEARNING_ENABLED=true|false
```

- The default mode is `production` for a release build and `development_degraded` only when explicitly selected by the operator.
- A production configuration with `LLMGATE_INTELLIGENCE_ADAPTER=local` is invalid.
- Unknown configuration keys, non-positive timeouts, unsafe executable paths, and malformed policy versions are startup errors.
- The adapter command is passed as an argument vector, never through a shell string.

## 3. Versioned request envelope

Every adapter invocation receives a redacted JSON request with this shape:

```json
{
  "protocol": "intelligence-adapter/v1",
  "operation": "route|readiness|record_outcome",
  "request_id": "uuid",
  "policy_version": "policy-2026-07-13.1",
  "task": {
    "class": "implementation",
    "fingerprint": "sha256:...",
    "message_count": 2,
    "estimated_input_tokens": 800,
    "requirements": {
      "reasoning": "high",
      "coding": "high",
      "tools": true,
      "structured_output": false,
      "vision": false,
      "streaming": true,
      "privacy": "trusted_upstream",
      "protected": false
    }
  },
  "candidates": [
    {
      "id": "agy/gpt-5.4-medium",
      "family": "gpt",
      "provider": "agy",
      "availability": "ready",
      "capabilities": ["coding", "tools", "streaming"],
      "quality_floor": 0.7
    }
  ],
  "policy": {
    "protected_floor": "frontier",
    "allow_client_model_override": false,
    "learned_policy_max_adjustment": 0.05
  },
  "privacy": {
    "raw_prompt_sent": false,
    "raw_completion_sent": false,
    "learning_opt_out": false
  }
}
```

The adapter MUST reject unknown protocol versions with a structured error. The envelope is safe to persist as test evidence after removing request IDs if desired.

## 4. Route response envelope

A successful `route` operation returns:

```json
{
  "protocol": "intelligence-adapter/v1",
  "operation": "route",
  "request_id": "uuid",
  "status": "ok",
  "managed_backend": "ruflo+ruvector",
  "adaptive_snapshot": "snapshot-id-or-null",
  "ranking": [
    {"model_id": "agy/gpt-5.4-medium", "adjustment": 0.02, "confidence": 0.61}
  ],
  "observations": ["warmup", "no_quality_outcome_for_bucket"],
  "expires_at": "2026-07-13T22:20:00Z"
}
```

The service MUST treat `ranking` as an advisory ordering signal only. It MUST intersect the result with deterministic eligible candidates, clamp adjustments, and recompute the final decision explanation locally.

A managed adapter cannot return a final `denied=false` or `protected=false` authority. Those fields do not exist in the protocol by design.

## 5. Readiness response envelope

A `readiness` operation returns:

```json
{
  "protocol": "intelligence-adapter/v1",
  "operation": "readiness",
  "status": "ready|not_ready|degraded",
  "managed_backend": "ruflo+ruvector",
  "checks": {
    "ruflo": "ready|not_ready|unknown",
    "ruvector": "ready|not_ready|unknown",
    "policy_bundle": "ready|not_ready|unknown"
  },
  "checked_at": "2026-07-13T22:20:00Z",
  "safe_reason": "managed adapter unavailable"
}
```

Production `/ready` requires `status=ready` and every required check `ready`. Development degraded mode may report `degraded`, never `ready`, while the local safety floor remains available.

## 6. Outcome response envelope

`record_outcome` is asynchronous and bounded. The immediate transport outcome and later validated quality outcome are distinct:

```json
{
  "protocol": "intelligence-adapter/v1",
  "operation": "record_outcome",
  "request_id": "uuid",
  "model_id": "agy/gpt-5.4-medium",
  "transport_outcome": "success|timeout|rate_limited|upstream_error|parse_error",
  "quality_outcome": "unknown|success|failure|user_rejected|tests_failed",
  "quality_score": null,
  "latency_ms": 842,
  "privacy": {"raw_prompt_sent": false, "raw_completion_sent": false}
}
```

A transport success with unknown quality MUST NOT be recorded as a quality success. An adapter failure is recorded locally and flips managed readiness to not-ready in production.

## 7. Ruflo and RuVector mapping

The adapter may invoke only documented surfaces already identified in `ENFORCEMENT_AND_LEARNING.md`:

- Ruflo route guidance uses stable family labels such as `haiku`, `sonnet`, `opus`, `gpt`, or `gemini`, not arbitrary OmniRoute IDs.
- The mapping from model ID to family is deterministic, versioned, and included in local telemetry.
- If a safe family mapping is unavailable, the Ruflo advisory call is skipped. Deterministic safety routing still runs.
- RuVector SONA operations are bounded, asynchronous learning or advisory retrieval operations. Training never runs inline on a user request.
- Command arguments are structured and redacted. Stderr is captured only as a generic categorized error, never returned to clients.

## 8. Failure and timeout matrix

| Failure | In-flight non-protected request | In-flight protected request | Readiness |
| --- | --- | --- | --- |
| Ruflo route timeout | deterministic floor, visible degraded event | reject unless explicit development degraded mode | production not-ready |
| RuVector ranking timeout | deterministic floor, visible degraded event | reject unless explicit development degraded mode | production not-ready |
| Outcome sink failure | local append-only record, do not crash request | same | production not-ready after bounded failure threshold |
| Malformed adapter JSON | deterministic floor, record protocol error | reject unless explicit development degraded mode | production not-ready |
| Adapter process missing | deterministic floor only in explicit development degraded mode | reject | not-ready |
| Candidate health unknown | exclude from protected selection | reject or select a verified alternative | unchanged |

No failure may cause an implicit downgrade of a protected request or an automatic retry after response bytes have started.

## 9. Required tests before Review

- Protocol request and response schema fixtures reject wrong versions and unknown required fields.
- Production readiness fails when either managed command is missing, times out, exits nonzero, or returns malformed JSON.
- Explicit development degraded mode is visible and protected requests reject by default.
- Adapter argv contains no raw prompt, completion, credential, or client Authorization header.
- A candidate returned by the adaptive ranking is still rejected when deterministic capability, privacy, availability, or protected gates reject it.
- Identical request, policy, catalog, and snapshot produce the same decision and explanation.
- Transport success plus unknown quality remains quality `unknown`.
- Adapter failure cannot crash the process or mutate local policy.
- No test or source path opens `ruvector.db`, Ruflo databases, OmniRoute SQLite, or historical 9router tables.

## 10. Review and release rule

Issue #7 cannot move to Review until this protocol is implemented or explicitly revised with a new version, the tests above pass, and the issue contains redacted command traces. A green unit-test suite without production readiness evidence is insufficient.
