# llm-gate Release Acceptance Matrix
## No public release until every blocking gate passes

### A. Core correctness

- [ ] `python -m pytest` passes in a clean environment with all declared dev dependencies.
- [ ] `ruff check`, `ruff format --check`, and strict mypy pass.
- [ ] Configuration loading validates URLs, ports, auth, model policy, and unknown keys.
- [ ] Routing is deterministic for fixed catalog/policy/input fixtures.
- [ ] Best-appropriate scoring is covered by unit tests, including quality floors and tie-breakers.
- [ ] Learned suggestions cannot bypass hard gates.

### A1. Mandatory intelligence

- [ ] Every routed request passes through the versioned `IntelligenceService` contract.
- [ ] The deterministic policy and capability safety floor runs even during cold start or adaptive-backend failure.
- [ ] The production profile requires healthy Ruflo/RuVector managed intelligence before `/ready` reports ready.
- [ ] Development-only degraded mode is explicit, visible in readiness and decision events, and cannot be advertised as production-ready.
- [ ] Adaptive-backend failure does not crash in-flight requests, but flips readiness and rejects protected work unless explicit degraded development mode is active.
- [ ] Privacy opt-out removes new prompt-derived learning data without disabling deterministic safety intelligence.
- [ ] Ruflo/RuVector adapter calls use documented CLI/API surfaces, bounded timeouts, redacted events, and no private database reads.
- [ ] Adaptive suggestions are advisory only and are proven unable to bypass denial, privacy, capability, or protected-task gates.

### B. Transparent proxy

- [ ] `GET /health` and `GET /ready` have stable JSON schemas.
- [ ] `GET /v1/models` returns a filtered, normalized catalog and does not claim catalog rows are live.
- [ ] `POST /v1/chat/completions` forwards a minimal request mutation and preserves all unknown fields.
- [ ] Non-streaming response status, headers, body, usage, tool calls, and errors round-trip.
- [ ] Streaming response passes arbitrary SSE chunk boundaries without corruption.
- [ ] Tool calls with parallel calls and partial deltas round-trip.
- [ ] Request size and timeout limits are enforced.
- [ ] Upstream auth is never taken from an arbitrary client field.
- [ ] Client-selected models cannot bypass policy unless explicitly enabled.

### C. Fallback and availability

- [ ] OmniRoute catalog rows can be marked `unknown`, `ready`, `degraded`, or `denied`.
- [ ] Local allow/deny rules work even when upstream catalog listing is broad.
- [ ] Health/headroom adapters are bounded and failure-isolated.
- [ ] Non-idempotent or already-streaming requests are never silently retried.
- [ ] Protected requests never fall back below their hard capability floor.
- [ ] Every fallback is represented in the response headers and event log.

### D. Safety and privacy

- [ ] Local authentication is tested.
- [ ] Upstream URL validation prevents SSRF and arbitrary per-request destinations.
- [ ] Secrets are redacted from logs and learning events.
- [ ] Raw prompt logging is disabled by default.
- [ ] Debug endpoints are loopback/auth protected.
- [ ] Guidance/Ruflo/RuVector integration failures cannot weaken policy safety. In production they make readiness fail, while the deterministic floor remains available for explicit degraded development mode.
- [ ] Dependency and static security scans pass.

### E. Compatibility

- [ ] Raw `httpx` client smoke test.
- [ ] OpenAI Python client smoke test pointed at llm-gate.
- [ ] One CLI-agent configuration example verified against a mock upstream.
- [ ] OmniRoute integration verified against the configured local endpoint.
- [ ] Anthropic/Responses adapters are either passing contract tests or explicitly excluded from the release.

### F. Distribution and operations

- [ ] `python -m build` and `twine check dist/*` pass.
- [ ] Wheel contains no credentials, caches, logs, test artifacts, or local paths.
- [ ] Docker image builds from a minimal context if Docker is advertised.
- [ ] `llm-gate --help`, `llm-gate serve --help`, `llm-gate check`, and `llm-gate route` work after install.
- [ ] Version, changelog, migration notes, and documented limitations agree.
- [ ] A release candidate can be installed into a fresh virtual environment and smoke-tested without the source checkout.

### G. Public claims gate

Before promotion, the release owner must attach evidence for each checked box. The README MUST NOT claim 20K-star readiness, universal compatibility, real-time quota accuracy, or autonomous quality learning without corresponding passing evidence.
