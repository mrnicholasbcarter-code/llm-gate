# ADR 003: Privacy-Safe Episode Schema

**Status:** Accepted
**Date:** 2026-07-22

## Context
Execution episode data (Tasks, Workflows, Outcomes, and Composite Episodes) must be reliably persisted without violating privacy and retention policies. This structure needs to strictly encode bounds so downstream datastores know when/where and what data they can safely process. 

## Decision
We implemented a provider-agnostic episode schema design tracking strict execution evidence boundaries:
1. **Namespace & Provenance:** Included on all episodes explicitly (`tenant`, `project`, `source`).
2. **Retention & Consent:** Policies track expiration dates and explicit deletion requests.
3. **Embeddings:** Explicit controls prevent semantic embedding algorithms from creating hashes on raw strings except in strictly labeled test-only environments (`embedding_mode`, `testing_only`). 
4. **Temporal Context:** Episodes can supersede previous IDs, mapping temporal version changes via `supersedes`, `valid_from`, and `valid_until`.
5. **Redaction First:** Strong `Contract` based implementation removes defined secrets and prompts from the payload before it has the opportunity to persist to disk.

## Consequences
- Every new episode defaults to restrictive values and correctly routes data to downstream collections with built-in consent constraints.
- Any hash-based embeddings automatically fail validation without explicit test-only parameters.
- Prompts, outputs, API keys, and internal text blocks never reach collections raw. They are uniformly checked by validation layers in both Typescript and Python APIs.
