# ADR 004: Episode Storage Adapter

**Status:** Accepted
**Date:** 2026-07-22

## Context

Privacy-safe execution episodes (TaskWorkflowOutcomeEpisode) need to be
stored and retrieved in a way that is provider-agnostic, testable without
external credentials, and never blocks deterministic routing safety.

## Decision

We defined an abstract `EpisodeStore` interface and two implementations:

1. **InMemoryEpisodeStore** — OrderedDict-backed fake for tests.
2. **RuVectorEpisodeStore** — Production stub, degraded by default.

### Key design rules

- Every result includes `RetrievalResult` metadata: episode_id, score,
  freshness, provenance, namespace, and embedding_version.
- `StorageDegradedError` never blocks deterministic routing. Callers catch
  it and continue.
- Duplicate detection is per embedding_version scope.
- Metadata filtering is surfaced as structured query parameters.
- Redaction is structural (`redact_contract_secrets`) before persistence.

## Consequences

- Adapter absence is explicit and cannot block routing safety.
- Tenant/project and embedding-version isolation is enforced.
- Retrieval results are redacted and provenance-linked.
- Duplicate, stale, malformed, and unauthorized records are handled safely.
- All tests run without external RuVector credentials.
