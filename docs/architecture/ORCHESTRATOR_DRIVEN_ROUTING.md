# Orchestrator-Driven Routing — Architecture & Vision

> **Status:** Canonical design spec for `llm-gate` and the surrounding portfolio.
> **Audience:** Contributors, future agent runs, and any model pointed at this repo.
> **Principle:** *Nothing hardcoded. Everything derived live from what is available.*

This document is the single source of truth for **why** the framework exists and **how** the
pieces fit together. It supersedes the older "regex tier engine" mental model. If you are a
model agent working in this repo, read this first — it explains the intent behind every routing
decision so you do not reinvent or contradict it.

---

## 1. The Problem (why this exists)

A frontier model (the one you pay $100–200/month for — Claude Opus, GPT-5.x, Gemini 3.x Pro)
burns **~95% of its token budget on file-parsing, boilerplate, and basic work** instead of the
hard reasoning it was bought for. That is waste.

The entire point of this framework: **reserve frontier models for appropriate (hard) tasks; push
everything-else to right-sized workers**, and make the whole system **accountable and self-improving**.

- "Appropriate," **not "cheap."** Right-sized per *actual task*:
  - Super basic → free OpenRouter models are fine.
  - Mid-level reasoning → Gemini 3.1 Pro / GPT-5.4 / GPT-5.5 are decent.
  - Money-level / trading decisions → max frontier.
- Models genuinely vary in power **and specialty** — some are better at some things. The selector
  reviews live metadata (capabilities, ratings, pricing) and picks per slice. It never uses a fixed rank.

---

## 2. The Core Principle: Zero Hardcoding

| Don't hardcode | Derive from |
|---|---|
| Model allowlist | OmniRoute `/v1/models` live catalog (all configured providers, one endpoint) |
| Capability tiers (T0–T3) | Per-model metadata: `capabilities`, `rating`, `context_length`, `pricing` |
| Worker selection | Orchestrator review + neural (SONA) learning from outcomes |
| Provider routing | OmniRoute dynamic/auto routing (`auto`, `auto/coding`, `auto/cheap`, smart) |
| Passing/failing a model | Live probe + runtime state (ready/degraded/denied/quota_exhausted/…) |

> The `classifier.py` static regex tier table is **deprecated** for the non-protected path.
> It is a maintenance trap: a new capable model lands in the wrong tier until someone edits the file.
> (See `docs/specs/ADR-149` precedent — tiers are a *ceiling*; operate on concrete ModelIds.)

---

## 3. Component Map (everything we already have)

```
┌──────────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR  (frontier model you pay for: LLMGATE_PRIMARY)           │
│  does the EXPENSIVE pass ONCE:                                         │
│  research → review catalog → pick per-slice model → spec → dispatch →  │
│  verify → feed outcome to learning loop                               │
└───────────┬──────────────────────────────────────────┬───────────────┘
            │ consults                                    │ dispatches slices to
            ▼                                             ▼
┌───────────────────────────┐              ┌──────────────────────────────────┐
│  llm-gate  (THIN GATE)     │              │  WORKERS (right-sized models)     │
│  • EligibilityGate         │              │  • free / mid / frontier per task │
│  • ProbeRunner (live truth)│              │  • ruflo swarm / agent-coordination│
│  • Catalog mirror (/v1/models)            │  • OpenRouter @openrouter/agent    │
│  • Fail-closed enforcement │              │    (AgentSDK: callModel + tools)   │
│  • Explain (#73)           │              └──────────────┬───────────────────┘
└───────────┬───────────────┘                              │ reports effectiveness
            │ live catalog + availability                  ▼
            ▼                              ┌──────────────────────────────────┐
┌───────────────────────────┐              │  LEARNING LOOP (SONA / neural)    │
│  OmniRoute :20128          │              │  • record_outcome(model, task,   │
│  • /v1/models (3628 models)│              │    success, cost, latency)        │
│  • dynamic auto routing    │              │  • hooks_model-outcome → SONA     │
│  • circuit-breaker/heal    │              │  • ReasoningBank pattern store    │
│  • one endpoint, easy swap │              └──────────────────────────────────┘
└───────────────────────────┘
```

### 3.1 What each piece is (verified this session)

| Piece | Where | Role | Ready? |
|---|---|---|---|
| `OmniRouteAvailabilityAdapter` | `llm_gate/availability.py` | Catalog + runtime → `AvailabilityReport` | ✅ |
| `ProbeRunner` | `llm_gate/probes.py` | Single-token live probe → truth | ✅ tested |
| `AvailabilityCache` | `llm_gate/availability_cache.py` | TTL + stale-while-revalidate (#56 merged) | ✅ |
| `EligibilityGate` | `llm_gate/eligibility.py` | Filter before ranking, fail-closed | ✅ (worktree) |
| `ProbeEnrichedAdapter` | `llm_gate/availability.py` | Merges probe truth into candidates | ✅ (worktree) |
| `IntelligenceService.route` | `llm_gate/intelligence.py` | **Currently** tier-based selector | ⚠️ must decouple |
| `intelligence-route` (ruflo) | ruflo plugin | `hooks_model-route` / `hooks_model-outcome` | ✅ docs |
| `neural-train` / SONA | ruflo plugin | Train/retrieve learned patterns | ✅ docs |
| `swarm-orchestration` / `agent-coordination` | ruflo skill | Spawn swarms / agent teams | ✅ docs |
| `claims` | ruflo skill | Parent↔worker accountability | ✅ docs |
| OpenRouter `@openrouter/agent` | npm `@openrouter/agent` | AgentSDK: `callModel` + tools + `stopWhen` | ✅ live docs |
| OpenRouter `openrouter:subagent` | server tool | Fixed-worker subagent delegation | ✅ live docs |

---

## 4. The Orchestrator Loop (the reusable procedure)

Codified so it is never improvised per task. The frontier model runs this once per unit of work:

1. **Research** — understand the task, the codebase, the required tools/docs. (RAG: Hindsight / AgentDB.)
2. **Review available models** — pull `GET /v1/models` from OmniRoute; each model exposes
   `id`, `pricing.input/output`, `context_length`, `capabilities`, `rating`. Select by metadata,
   not by a tier name.
3. **Slice & assign** — break the work into deliverable slices; pick the *appropriate* model per
   slice (free for docs, mid for routine logic, frontier for money-level decisions).
4. **Spec** — write the slice as a ruflo ticket / `claims` entry (accountability + acceptance criteria).
5. **Dispatch** — via swarm / agent-team / AgentSDK per the dispatch matrix (§6).
6. **Share standards** — push context + claims + TDD + lint config to the worker.
7. **Verify** — review worker output; run tests/lint; confirm nothing broke.
8. **Learn** — `record_outcome(model, task_class, success, cost, latency)` → SONA/ReasoningBank.

> Each task is owned by a **parent subagent** responsible for the *entire* cycle:
> research → plan → spec → orchestrate → verify → integrate → confirm green.

---

## 5. The Learning Loop (SONA / neural)

Goal: the router gets smarter about *which model suits what*, from real outcomes.

```
worker completes slice
        │  effectiveness (success / cost / latency / quality)
        ▼
record_outcome(model_id, task_class, success, cost, latency)
        │  ruflo hooks_model-outcome  (subprocess, same pattern as
        │  IntelligenceService._probe_managed_backend)
        ▼
SONA neural-train  →  ReasoningBank pattern store  →  future hooks_model-route
```

- Implemented as a thin client (`llm_gate/learning_feedback.py`) calling `ruflo hooks_model-outcome`
  — mirrors the existing `intelligence.py` subprocess pattern. No new transport.
- Patterns persist in ruflo's ReasoningBank / AgentDB; **not** baked into llm-gate's request path
  (keeps llm-gate deterministic for fail-closed enforcement).

---

## 6. Dispatch Matrix (when to use what)

| Situation | Mechanism | Why |
|---|---|---|
| Many independent slices | `ruflo swarm` (hierarchical) | Parallel, coordinated |
| One dependent slice, needs tools | `ruflo agent-coordination` / agent team | Shared context |
| Multi-turn + tool loop, TS | OpenRouter `@openrouter/agent` `callModel` + `tool()` + `stopWhen` | Managed loops |
| Simple request/response | OpenRouter Python SDK `open_router.chat.send` | Lean |
| Worker must be a specific model | `openrouter:subagent` server tool (worker fixed in tool def) | Fixed assignment |
| Dynamic model swap mid-task | `nextTurnParams` (AgentSDK) / OmniRoute `auto/*` | Adaptive |

**OpenAI-compatible base_url override (spitball, validated as viable):** every OpenRouter SDK is
OpenAI-compatible. Point them at the local gateway instead of `openrouter.ai`:

```python
from openrouter import OpenRouter
with OpenRouter(api_key=os.getenv("OMNIROUTE_API_KEY"),
                base_url="http://localhost:20128/v1") as client:
    client.chat.send(model="openai/gpt-5-nano", messages=[...])
```

This means **any** OpenAI-compatible SDK can target OmniRoute with a one-line change — trivial model
switching across the whole catalog, exactly the substrate the principle needs.

---

## 7. Fail-Closed & Accountability

- **Protected work** (money-level/trading): dispatched only to workers the gate marks `ready`
  (never below the safety floor). The gate is the *enforcer*, the orchestrator is the *selector*.
- **EligibilityGate** drops any candidate whose live state is not `eligible`/`ready`/`degraded`;
  for protected work it fails **closed** when runtime truth is absent (never optimistically admit).
- **`/v1/route/explain` (#73)** exposes the full candidate set, the pre-ranking eligible set,
  per-candidate exclusion reasons, and cache confidence/refresh_error — full auditability.
- **`claims`** give parent↔worker accountability: a slice is not "done" until its claim verifies.

---

## 8. Improvements & Recommendations (research findings)

1. **Retire `classifier.py` tiers for non-protected path.** Replace with live-metadata selection
   (capabilities + rating + pricing) reviewed by the orchestrator. Keep a deterministic frontier
   floor *only* for protected work. (Precedent: `ADR-149`.)
2. **Make the orchestrator loop a first-class, callable procedure**, not improvised per task.
   This doc (§4) is the spec; a Hermes/ruflo skill should wrap it.
3. **Wire the learning loop end-to-end.** `record_outcome` → `hooks_model-outcome` → SONA is
   documented but **not yet connected to worker outcomes**. This is the highest-leverage gap.
4. **Catalog mirror must pass through full metadata** (`pricing`, `capabilities`, `rating`) so the
   orchestrator can "review all models like openrouter.ai." Current `/v1/models` may strip fields.
5. **Use OmniRoute `auto/*` + circuit-breaker as the resilience layer.** Do not re-implement
   self-healing in llm-gate — reuse it (score<0.2 → excluded 5 min; >50% down → incident mode).
6. **Probe only in production profile.** `ProbeEnrichedAdapter` is opt-in
   (`LLMGATE_AVAILABILITY_PROFILE=production`) so dev stays pure catalog/runtime.
7. **Cross-project pattern transfer** via `intelligence-transfer` (IPFS/Pinata) so a lesson learned
   in one repo improves routing in all of them.
8. **Accountability-native specs.** Every dispatched slice should be a `claims` entry with AC, so
   verification is mechanical, not trust-based.

---

## 9. Open Questions (resolve before finalizing the learning wiring)

- **Q1 — Protected-work frontier floor:** is the orchestrator *allowed* to pick a non-frontier
  worker for protected work, or is a deterministic frontier floor mandatory? (Plan assumes:
  protected → frontier-tier worker only, gate-enforced.)
- **Q2 — OmniRoute per-model detail endpoint:** docs reference a "fetch model details" capability;
  the **exact path is unconfirmed this session** — verify at wire time, do not guess the URL.
- **Q3 — Learning transport:** does `record_outcome` go to ruflo SONA directly, or through a
  Hindsight/AgentDB pattern store the router reads? (Plan assumes SONA hooks + ReasoningBank.)
- **Q4 — Orchestrator identity:** when the orchestrator *is* Hermes, is "the frontier model"
  Hermes's own model or `LLMGATE_PRIMARY`? (Plan treats `LLMGATE_PRIMARY` as the orchestrator.)

---

## 10. For Contributors / Models Pointed At This Repo

- Read this file before touching `router.py`, `intelligence.py`, `gate.py`, `availability.py`,
  `availability_cache.py`, `probes.py`, or `api.py`.
- If you are about to add a hardcoded model name, tier, or allowlist — **stop.** Derive it from the
  live catalog instead.
- The gate (eligibility/probe/fail-closed) is sacred and deterministic. The *selector* lives in the
  orchestrator + learning loop, not in the request path.
- See `docs/specs/ROUTING_POLICY.md`, `ENFORCEMENT_AND_LEARNING.md`, `ADR-149`, and the plan at
  `.hermes/plans/2026-07-19_051730-orchestrator-driven-routing.md`.

---

*This spec is the canonical intent record. When in doubt, optimize for: frontier model does less
basic work, nothing is hardcoded, and every delegation is accountable and learns.*
