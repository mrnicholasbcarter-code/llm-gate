# Configuration Reference

Verdict uses TOML configuration with layered precedence:

1. **Defaults** (built-in)
2. **Global**: `~/.verdict/config.toml`
3. **Project**: `.verdict/config.toml` (highest priority)
4. **Environment variables** (override all)

---

## Complete Configuration Schema

```toml
# Gateway / routing
[gateway]
primary_model = "anthropic/claude-3-opus-20240229"  # Fallback model
providers = {}  # Provider-specific config

# Intelligence / ranking (advisory only - cannot bypass gate)
[intelligence]
profile = "balanced"           # fast | balanced | thorough
timeout_ms = 8000
allow_client_model_override = false
log_path = "verdict-decisions.jsonl"
log_full_task = false
discovery_ttl = 60
ruflo_command = "ruflo"
ruvector_command = "ruvector"
frontier_allowlist = []        # Models allowed for frontier tier

# Availability cache (issue #56)
[availability]
ttl_seconds = 60
stale_window_seconds = 30
omniroute_base_url = "http://localhost:20128"  # Optional

# Eligibility gate (hard safety floors)
[eligibility]
capability_required = []       # e.g. ["tools", "vision"]
min_context_tokens = 4096
budget_usd_per_1k = 0.0
privacy_level = "standard"     # standard | strict | paranoid

# Capacity admission (deterministic headroom)
[capacity]
enabled = true
headroom_factor = 1.2
max_concurrent_per_model = 100
effort_reservation_pct = 0.15

# Security / redaction
[security]
redact_api_keys = true
redact_pii = true
allow_private_hosts = false

# Telemetry / SONA feedback loop
[telemetry]
enabled = true
endpoint = "http://localhost:20128/v1/telemetry"
batch_size = 100
flush_interval_ms = 5000

# Dashboard
[dashboard]
host = "localhost"
port = 8501
auto_open = true
```

---

## Environment Variable Overrides

| Variable | Config Path | Example |
|----------|-------------|---------|
| `VERDICT_CONFIG` | — | `/path/to/config.toml` |
| `OMNIROUTE_BASE_URL` | `availability.omniroute_base_url` | `http://localhost:20128` |
| `LLMGATE_PRIMARY` | `gateway.primary_model` | `anthropic/claude-3-opus-20240229` |
| `LLMGATE_INTELLIGENCE_PROFILE` | `intelligence.profile` | `thorough` |
| `LLMGATE_INTELLIGENCE_TIMEOUT_MS` | `intelligence.timeout_ms` | `15000` |
| `LLMGATE_ALLOW_CLIENT_MODEL_OVERRIDE` | `intelligence.allow_client_model_override` | `true` |
| `LLMGATE_LOG_PATH` | `intelligence.log_path` | `/var/log/verdict.jsonl` |
| `LLMGATE_DISCOVERY_TTL_SECONDS` | `intelligence.discovery_ttl` | `120` |
| `LLMGATE_RUFLO_COMMAND` | `intelligence.ruflo_command` | `ruflo` |
| `LLMGATE_RUVECTOR_COMMAND` | `intelligence.ruvector_command` | `ruvector` |
| `LLMGATE_FRONTIER_ALLOWLIST` | `intelligence.frontier_allowlist` | `model1,model2` |
| `LLMGATE_AVAILABILITY_TTL_SECONDS` | `availability.ttl_seconds` | `60` |
| `LLMGATE_AVAILABILITY_STALE_WINDOW_SECONDS` | `availability.stale_window_seconds` | `30` |

---

## Example: Production Config

```toml
# .verdict/config.toml
[gateway]
primary_model = "openai/gpt-4o"
providers.openai.api_key_env = "OPENAI_API_KEY"
providers.anthropic.api_key_env = "ANTHROPIC_API_KEY"

[intelligence]
profile = "thorough"
timeout_ms = 15000
frontier_allowlist = ["anthropic/claude-3-opus-20240229", "openai/gpt-4o"]

[availability]
ttl_seconds = 30
stale_window_seconds = 15
omniroute_base_url = "https://omniroute.company.internal/v1"

[eligibility]
capability_required = ["tools"]
min_context_tokens = 8192
budget_usd_per_1k = 0.05
privacy_level = "strict"

[capacity]
enabled = true
headroom_factor = 1.5
max_concurrent_per_model = 200

[security]
redact_api_keys = true
redact_pii = true

[telemetry]
enabled = true
endpoint = "https://telemetry.company.internal/v1/ingest"
```
