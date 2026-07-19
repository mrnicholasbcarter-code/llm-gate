# Project Memory (Hindsight) Configuration

llm-gate can run its long-term memory (fact extraction + recall) entirely
through the local OmniRoute gateway, so memory never depends on a single paid
provider or a cloud memory service that can hit usage limits.

Hindsight resolves its extraction LLM in this priority order:

1. `HINDSIGHT_API_LLM_*` environment variables (highest priority)
2. Plugin `settings.json` (`llmProvider`, `llmModel`, `llmApiKeyEnv`)
3. Auto-detected provider env vars

## Recommended setup: route memory through OmniRoute (free / unlimited)

Point Hindsight at the local OmniRoute OpenAI-compatible endpoint and a free
or unlimited model. Set these in your shell (or a sourced `.env`):

```bash
export HINDSIGHT_API_LLM_PROVIDER=openai
export HINDSIGHT_API_LLM_BASE_URL=http://localhost:20128/v1
export HINDSIGHT_API_LLM_API_KEY="$OPENAI_API_KEY"      # OmniRoute key
export HINDSIGHT_API_LLM_MODEL=openrouter/tencent/hy3:free
```

`openrouter/tencent/hy3:free` is reasoning-capable (262K context) and is the
current reliable default. OmniRoute performs cooldown-aware retry and
account-fallback automatically, so a single free-tier stall degrades
gracefully.

## Verify the model before relying on it

Use the built-in one-token liveness probe (no user data, `max_tokens=1`):

```bash
llm-gate probe openrouter/tencent/hy3:free
```

`LIVE` with HTTP 200 means memory extraction will work. Probe a few
candidates and keep the ones that pass:

```bash
llm-gate probe \
  openrouter/tencent/hy3:free \
  oc/minimax-m3-free \
  openrouter/nvidia/nemotron-nano-9b-v2:free
```

## Fallback chain

Prefer models from different upstream families so one provider's rate limit
does not take memory down. Verified-first ordering (re-probe periodically):

1. `openrouter/tencent/hy3:free`   (OpenRouter free, reasoning)
2. `oc/minimax-m3-free`            (OpenCode, unlimited)
3. `openrouter/nvidia/nemotron-nano-9b-v2:free`
4. `openrouter/google/gemma-4-31b-it:free`

Note: OmniRoute combo aliases such as `auto/mimo` may reject the probe payload
shape (HTTP 400 on `tools: []`); prefer concrete model IDs for memory.

## Notes

- The OmniRoute gateway must be running on `:20128` (its default).
- Nothing here writes secrets into the repo; the API key is read from the
  environment at runtime.
