# Codex / Hermes Integration

For agents like **Codex Companion** and **Hermes**, which rely on heavily partitioned AgentDB memory state namespaces (e.g., `codex-kalshi-trader` vs `hermes-kalshi-trader`), enforcing strict model boundaries is critical so cheap models don't pollute your Vector store with low-quality insights.

### Global Intercept Hook

Because these tools are often invoked from inside other programmatic loops, the safest integration is a global executable wrapper.

Create `/usr/local/bin/codex-routed`:

```bash
#!/usr/bin/env bash
TASK="$1"

# LLM-Gate strict evaluation
TARGET=$(llm-gate route "$TASK" | grep -o '• Model: .*' | awk '{print $3}' | sed 's/\[.*\]//g')

if [[ "$TARGET" != "" ]]; then
    export CODEX_MODEL_NAME="$TARGET"
fi

exec codex "$@"
```

By hooking this layer, your agentic databases remain populated only by Tier-0 or Tier-1 models when handling critical code reasoning, while formatting tasks silently fall back to Tier-3 models, saving massive schema costs.
