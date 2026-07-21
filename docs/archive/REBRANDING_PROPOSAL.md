# Rebranding Proposal — `verdict` → **Verdict** (or alternatives)

> **Status**: Ready for review. No repos renamed until name chosen.
> **Scope**: All 7 `verdict-*` repos, documentation, CLI, install scripts, dashboard, memory system.

---

## Why Rename?

| Current | Problem |
|---------|---------|
| `verdict` | Generic, undersells product; sounds like a simple proxy |
| `verdict-core` | Doesn't convey "control plane" or "safety gate" |
| `verdict-strategy` | "Strategy" implies trading, not routing |
| `verdict-risk` | "Risk" implies only risk mgmt, not full routing |
| `verdict-node` | Language-specific naming fragments ecosystem |
| `verdict-cockpit` | "Cockpit" is UI-only, not the product |
| `verdict-ecosystem` | Meta-repo name leaks internal structure |

**What the product actually is**: A **policy-gated, availability-aware LLM routing control plane** with deterministic safety floors, quantitative-trading-grade execution, and closed-loop telemetry.

---

## Recommended Name: **Verdict**

| Aspect | Score (1-5) | Rationale |
|--------|-------------|-----------|
| **Metaphor fit** | 5 | "The gate rules on each task" — deterministic safety verdict |
| **CLI verbs** | 5 | `verdict route`, `verdict explain`, `verdict policy`, `verdict models` |
| **Sub-brand room** | 5 | `verdict-core`, `verdict-edge`, `verdict-risk`, `verdict-ui`, `verdict-node` |
| **Searchability** | 4 | Unique in dev tools; "verdict" + "routing" = clear intent |
| **Trademark risk** | 4 | Low — common word, but distinctive in AI routing context |
| **Pronounceability** | 5 | Two syllables, crisp, memorable |
| **Visual identity** | 5 | Gavel, scales, checkmark, shield — strong iconography |

---

## Alternative Names (ranked)

| Name | Metaphor | CLI Verbs | Sub-brands | Risk |
|------|----------|-----------|------------|------|
| **Helmsman** | Nautical steering | `helm route`, `helm policy` | `helm-core`, `helm-edge` | Moderate (K8s Helm conflict) |
| **Waypoint** | Navigation | `waypoint route`, `waypoint models` | `waypoint-core`, `waypoint-ui` | Low |
| **Beacon** | Signal + telemetry | `beacon route`, `beacon explain` | `beacon-core`, `beacon-sense` | Low |
| **Tollgate** | Hard gate emphasis | `tollgate route`, `tollgate check` | `tollgate-core`, `tollgate-risk` | Medium (negative connotation) |
| **Sentinel** | Guardrail-first | `sentinel route`, `sentinel guard` | `sentinel-core`, `sentinel-watch` | Low |
| **Arbiter** | Judicial/decision | `arbiter route`, `arbiter decide` | `arbiter-core`, `arbiter-edge` | Low |
| **Compass** | Direction finding | `compass route`, `compass models` | `compass-core`, `compass-ui` | High (overused) |

---

## Unified Ecosystem Scheme (with **Verdict**)

| Current Repo | Purpose | Proposed Name | Package / CLI |
|--------------|---------|---------------|---------------|
| `verdict-core` | Routing/eligibility control plane (flagship) | **verdict-core** | `verdict`, `verdict-core` |
| `verdict-ecosystem` | Umbrella / meta repo | **verdict** | (meta only) |
| `verdict-strategy` | Edge Mining Framework | **verdict-edge** | `verdict-edge` |
| `verdict-risk` | Risk/cost validation, WAL | **verdict-risk** | `verdict-risk` |
| `verdict-node` | TypeScript/Node SDK | **verdict-node** | `@verdict/node`, `verdict-node` |
| `verdict-cockpit` | Dashboard/UI | **verdict-ui** | `verdict-ui`, `verdict dashboard` |
| `verdict-backtest` | Historical simulation | **verdict-backtest** | `verdict backtest` |

**Installation unified**:
```bash
# Single installer for everything
curl -fsSL https://verdict.sh/install.sh | bash

# Or via package managers
npm i -g verdict        # CLI + Node SDK
pip install verdict     # Python SDK
cargo install verdict   # Rust (future)
```

---

## Documentation Makeover Plan

### Current State vs. Trending Standards

| Standard | Trending Repos (Ollama, LangChain, RAGFlow) | verdict Current | Gap |
|----------|---------------------------------------------|------------------|-----|
| **Hero section** | Logo + tagline + badges + 3 CTAs | Text only | Add badges, CTAs, logo |
| **Quickstart** | 3-step code block (< 30 sec) | Missing | Add `verdict route "task"` |
| **Architecture diagram** | Mermaid/PlantUML + explanation | `architecture.md` (4 lines) | Expand with diagram |
| **Install methods** | Tabbed: curl, brew, npm, pip, docker | None | Add all |
| **Configuration** | TOML/YAML examples + env vars | Scattered | Centralize in `config.toml` |
| **CLI reference** | Auto-generated + examples | Partial | Generate from Cobra/Click |
| **API reference** | OpenAPI/Swagger + examples | Missing | Add from FastAPI |
| **Integrations** | Grid: Cursor, VSCode, Aider, Continue, LiteLLM | `integration-guide.md` | Expand to matrix |
| **Troubleshooting** | FAQ + common errors | None | Add |
| **Contributing** | Issue templates, PR guide, dev setup | `CONTRIBUTING.md` (thin) | Expand |

### New Documentation Structure

```
docs/
├── README.md                    # ← Hero + quickstart + badges
├── GETTING_STARTED.md           # ← 3-step quickstart
├── INSTALLATION.md              # ← All install methods
├── CONFIGURATION.md             # ← config.toml + env vars
├── CLI_REFERENCE.md             # ← Auto-generated
├── API_REFERENCE.md             # ← OpenAPI-based
├── ARCHITECTURE.md              # ← Mermaid diagrams + deep dive
├── INTEGRATIONS.md              # ← Matrix table
├── TROUBLESHOOTING.md           # ← FAQ + errors
├── CONTRIBUTING.md              # ← Dev setup + PR guide
├── CHANGELOG.md                 # ← Keep
├── SECURITY.md                  # ← Keep
├── LICENSE.md                   # ← Keep
├── guides/
│   ├── routing-policies.md
│   ├── custom-models.md
│   ├── local-development.md
│   ├── production-deployment.md
│   ├── dashboard-setup.md
│   └── memory-system.md
├── architecture/
│   ├── eligibility-gate.md
│   ├── intelligence-service.md
│   ├── proxy-layer.md
│   └── telemetry-loop.md
├── api/
│   ├── openapi.yaml
│   └── examples/
└── assets/
    ├── logo.svg
    ├── architecture.mmd
    └── screenshots/
```

---

## Install Script Upgrade

### Current: Non-existent
### Target: Single cross-platform installer (`install.sh`)

```bash
#!/usr/bin/env bash
# verdict/install.sh — Universal installer
set -euo pipefail

REPO="verdict/verdict"
INSTALL_DIR="${VERDICT_INSTALL_DIR:-$HOME/.verdict/bin}"
VERSION="${VERDICT_VERSION:-latest}"

# Detect platform
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
case $ARCH in
  x86_64) ARCH="amd64" ;;
  aarch64|arm64) ARCH="arm64" ;;
esac

# Download and install
TMP=$(mktemp -d)
curl -fsSL "https://github.com/${REPO}/releases/download/${VERSION}/verdict-${OS}-${ARCH}.tar.gz" | tar -xz -C "$TMP"
mkdir -p "$INSTALL_DIR"
mv "$TMP/verdict" "$INSTALL_DIR/"
rm -rf "$TMP"

# PATH guidance
echo "✅ verdict installed to $INSTALL_DIR"
echo "Add to PATH: export PATH=\"$INSTALL_DIR:\$PATH\""
echo "Run: verdict route \"your task\""
```

**Also publish to**:
- Homebrew: `brew install verdict/tap/verdict`
- npm: `npm i -g verdict`
- PyPI: `pip install verdict`
- Cargo: `cargo install verdict` (future)
- Docker: `docker pull verdict/verdict:latest`

---

## CLI Upgrade

### Current State
- Python `llm_gate/cli.py` with basic `route`, `explain`, `models`
- No subcommand structure, no completion, no config management

### Target Structure (Cobra-style)

```bash
verdict [global flags] <command> [args]

Commands:
  route        Route a task to the best model
  explain      Show eligibility & ranking for a task
  models       List/refresh available models
  policy       Manage routing policies (get/set/validate)
  dashboard    Launch/manage verdict-ui
  config       Manage local configuration
  completion   Generate shell completions
  version      Show version info

Global flags:
  --api-base       Gateway endpoint (default: http://localhost:20128)
  --api-key        API key (or VERDICT_API_KEY env)
  --profile        Config profile to use
  --output         json|yaml|table|text
  --verbose        Debug logging
```

### Enhanced `verdict route`
```bash
verdict route "deploy production" --criticality high --context '{"repo":"acme/api"}'
verdict route "format json" --tier free --dry-run
verdict route "write test" --explain --output json
```

### Config Management
```bash
verdict config init                    # Create ~/.verdict/config.toml
verdict config set api.base http://localhost:20128
verdict config profiles add staging --api-base https://staging.verdict.sh
verdict config profiles use staging
verdict config show
```

---

## Dashboard (`verdict-ui`) Upgrade

### Current: Basic Next.js cockpit
### Target: Full routing management console

| Feature | Status |
|---------|--------|
| **Live routing log** | ✅ (WebSocket) |
| **Policy editor (YAML/TOML)** | 🔲 |
| **Model catalog with pricing** | 🔲 |
| **Eligibility gate visualizer** | 🔲 |
| **Cost/latency analytics** | 🔲 |
| **A/B testing dashboard** | 🔲 |
| **Team workspaces** | 🔲 |
| **Audit log export** | 🔲 |

**Tech**: Next.js 14 + Tailwind + shadcn/ui + TanStack Query + WebSocket

---

## Project-Local Memory System

### Concept
Each project gets a `.verdict/` directory with:
```
.verdict/
├── config.toml           # Project-specific routing config
├── memory/
│   ├── decisions.jsonl   # Routing decisions for this project
│   ├── patterns.json     # Learned task→model patterns
│   └── feedback.jsonl    # User corrections
├── cache/
│   └── models.json       # Cached model catalog
└── logs/
    └── verdict.log       # Local execution log
```

### CLI Integration
```bash
verdict init                    # Creates .verdict/ in current dir
verdict route "task" --project  # Uses .verdict/config.toml
verdict memory export           # Export learned patterns
verdict memory import patterns.json
```

---

## Cleanup: Remove Obsolete Docs

Move to `docs/archive/`:
- `BENCHMARKS.md` → integrate into `guides/benchmarks.md`
- `DEMO.md` → integrate into `GETTING_STARTED.md`
- `TOOLING_STACK_DIGEST.md` → internal only
- `PROJECT_MEMORY.md` → integrate into `guides/memory-system.md`
- `contracts-migration.md` → done, archive
- `handoff-july-2026.md` → internal only
- `memory-source-index.md` → internal only
- `audit-2026-07-13.md` → internal only
- `continuation-runbook.md` → internal only
- `plan-flagship-completion.md` → done, archive

---

## Implementation Order

| Phase | Tasks | Est. Effort |
|-------|-------|-------------|
| **1. Name & Identity** | Finalize name, register domains, design logo | 1 day |
| **2. Repo Renames** | Rename all 7 repos, update imports, CI/CD | 2 days |
| **3. Install Script** | Build `install.sh`, publish to package managers | 2 days |
| **4. CLI Rewrite** | Cobra/Click rewrite with full command tree | 3 days |
| **5. Documentation** | Full docs rewrite per new structure | 3 days |
| **6. Dashboard** | Policy editor, analytics, model catalog | 5 days |
| **7. Memory System** | `.verdict/` local memory + CLI integration | 2 days |
| **8. Polish** | Completions, man pages, shell integrations | 1 day |

**Total**: ~19 days for full rebrand + upgrade

---

## Decision Required

**Choose the name**:
- [ ] **Verdict** (recommended)
- [ ] Helmsman
- [ ] Waypoint
- [ ] Beacon
- [ ] Tollgate
- [ ] Sentinel
- [ ] Arbiter
- [ ] Other: ___________

Once chosen, I'll:
1. Reserve GitHub org (`verdict` or chosen name)
2. Create the install script
3. Begin repo renames
4. Rewrite documentation
5. Rewrite CLI
6. Upgrade dashboard

**Shall I proceed with "Verdict"?**
