# Rebrand Proposals — `llm-gate` Ecosystem

Status: proposal for review. No repos are renamed until a name is chosen.

## Why rename

`llm-gate` is generic and undersells the product. The stack is a
**policy-gated, availability-aware LLM routing control plane** with a
quantitative-trading application layer. The name should signal the
*deterministic safety gate + intelligent routing* core and be
20k-star memorable.

## What the product actually is

- Control plane that normalizes a task to a versioned `TaskSpec`, applies
  deterministic policy/capability/privacy/budget/availability gates, and
  explains the eligible candidate set.
- Advisory intelligence ranks eligible candidates but cannot bypass a hard gate.
- OpenAI-compatible proxy with availability caching, provider detection,
  and a telemetry feedback loop.

## Naming shortlist (core repo)

| Candidate | Rationale | Package / CLI |
| --- | --- | --- |
| **Verdict** | The gate "rules" on each task — a deterministic safety verdict. Short, brandable, unclaimed feel. | `verdict`, `verdict route` |
| **Helmsman** | Steers each request to the right model; nautical, confident. | `helm`, `helm route` |
| **Waypoint** | Routing + navigation metaphor; enterprise-friendly. | `waypoint` |
| **Beacon** | Routing signal + telemetry loop. | `beacon` |
| **Tollgate** | Emphasizes the hard safety gate/allowance checks. | `tollgate` |
| **Sentinel** | Guardrail-first framing. | `sentinel` |

Recommendation: **Verdict** (clear gate metaphor, easy CLI verbs, room for a
trading-edge sub-brand).

## Unified ecosystem scheme (example with "verdict")

| Current repo | Purpose | Proposed |
| --- | --- | --- |
| `llm-gate-core` | Routing/eligibility control plane (flagship) | `verdict-core` |
| `llm-gate-ecosystem` | Umbrella / meta repo | `verdict` |
| `llm-gate-strategy` | Edge Mining Framework | `verdict-edge` |
| `llm-gate-risk` | Trade Risk Engine | `verdict-risk` |
| `llm-gate-backtest` | Backtest Harness | `verdict-backtest` |
| `llm-gate-cockpit` | React/TS dashboard | `verdict-cockpit` |
| `llm-gate-node` | Node integration | `verdict-node` |

## Rename mechanics (once a name is chosen)

1. Python import package stays a valid identifier (e.g. `verdict`), dist name
   matches (`verdict-core`), console script renamed (`verdict`).
2. `pyproject.toml`: set `[project].name`, `[project.scripts]`, and
   `[tool.hatch.build.targets.wheel].packages` together.
3. GitHub repo renames keep redirects; update README badges and URLs.
4. Keep `llm-gate` as a deprecated alias for one release for CLI users.
