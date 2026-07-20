# CLI Reference

```
verdict [global flags] <command> [args]
```

## Global Flags

| Flag | Description |
|------|-------------|
| `-h, --help` | Show help |
| `--version` | Show version |
| `--config <path>` | Config file path |
| `--verbose` | Verbose output |

---

## Commands

### `verdict route` — Route task to best model

```bash
verdict route "your task prompt" [flags]
```

| Flag | Description |
|------|-------------|
| `--terse` | Output model name only |
| `--verbose` | Show full reasoning |
| `--criticality <level>` | `low` \| `medium` \| `high` \| `critical` |
| `--context <json>` | Additional context for routing |
| `--policy <name>` | Policy name to use |

**Examples:**
```bash
verdict route "Write a Rust CLI tool" --terse
verdict route "Deploy to production" --criticality high --context '{"repo":"acme/api"}'
```

---

### `verdict explain` — Show eligibility ranking & freshness

```bash
verdict explain "your task prompt" [flags]
```

Shows candidate models, eligibility reasoning, freshness data, exclusion reasons.

---

### `verdict models` — List/refresh available models

```bash
verdict models [flags]
```

| Flag | Description |
|------|-------------|
| `--refresh` | Force refresh from OmniRoute |
| `--provider <name>` | Filter by provider |
| `--free-only` | Show only free tiers |

---

### `verdict policy` — Manage routing policies

```bash
verdict policy <subcommand> [args]
```

| Subcommand | Description |
|------------|-------------|
| `get [name]` | Show policy |
| `set <name> <file>` | Set policy from YAML/TOML |
| `validate <file>` | Validate policy syntax |
| `list` | List available policies |
| `delete <name>` | Delete policy |

---

### `verdict dashboard` — Launch/manage verdict-ui

```bash
verdict dashboard [flags]
```

| Flag | Description |
|------|-------------|
| `--port <n>` | Port (default: 8501) |
| `--host <ip>` | Host (default: localhost) |
| `--no-browser` | Don't open browser |

---

### `verdict config` — Manage local configuration

```bash
verdict config <subcommand> [args]
```

| Subcommand | Description |
|------------|-------------|
| `show` | Show effective config |
| `edit` | Open config in $EDITOR |
| `get <key>` | Get config value |
| `set <key> <value>` | Set config value |
| `reset` | Reset to defaults |

---

### `verdict completion` — Generate shell completions

```bash
verdict completion <shell>
```

| Shell | Install Command |
|-------|-----------------|
| `bash` | `verdict completion bash > /usr/local/etc/bash_completion.d/verdict` |
| `zsh` | `verdict completion zsh > ~/.zsh/completions/_verdict` |
| `fish` | `verdict completion fish > ~/.config/fish/completions/verdict.fish` |

---

### `verdict serve` — Launch FastAPI microservice

```bash
verdict serve [flags]
```

| Flag | Description |
|------|-------------|
| `--host <ip>` | Host (default: 127.0.0.1) |
| `--port <n>` | Port (default: 8000) |
| `--workers <n>` | Uvicorn workers |

---

### `verdict detect` — Detect available LLM providers

```bash
verdict detect
```

Scans for local providers (Ollama, LM Studio, etc.) and configured API keys.

---

### `verdict probe` — Run 1-token liveness probe

```bash
verdict probe <model_id>
```

---

### `verdict suggest` — Review intelligence suggestions

```bash
verdict suggest [flags]
```

---

### `verdict doctor` — Scan & repair config/connectivity

```bash
verdict doctor [flags]
```

| Flag | Description |
|------|-------------|
| `--fix` | Auto-fix issues |

---

### `verdict check` — Validate config syntax

```bash
verdict check [config_file]
```

---

### `verdict setup` — Interactive setup wizard

```bash
verdict setup
```

---

### `verdict stats` — View routing analytics

```bash
verdict stats [flags]
```

| Flag | Description |
|------|-------------|
| `--days <n>` | Lookback period |
| `--format <type>` | `json` \| `table` \| `csv` |

---

### `verdict benchmark` — Run reproducible benchmark

```bash
verdict benchmark [flags]
```

| Flag | Description |
|------|-------------|
| `--fixture <path>` | Benchmark fixture |
| `--runs <n>` | Number of runs |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VERDICT_CONFIG` | Config file path |
| `OMNIROUTE_BASE_URL` | OmniRoute endpoint |
| `LLMGATE_PRIMARY` | Primary model (legacy) |
| `LLMGATE_INTELLIGENCE_PROFILE` | Intelligence profile |
| `LLMGATE_LOG_PATH` | Decision log path |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Invalid arguments |
| `3` | Config error |
| `4` | Upstream unavailable |
| `5` | No eligible models |
