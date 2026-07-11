# Claude Code Integration (OmniRoute/9router)

Want to stop burning your precious `Claude Max` API quota on formatting files and finding regex matches? 

You can bind `llm-gate` directly into the terminal tooling of Claude Code by using the `userPromptSubmit` lifecycle hook. Every time you submit a prompt, `llm-gate` evaluates the criticality and intercepts the `CLAUDE_MODEL` environment variable.

### 1. Install llm-gate
Ensure it is installed in your system path or virtual environment:
```bash
pipx install llm-gate
```

### 2. Add the Hook
Create the `.claude/hooks/` directory in your project if you haven't already. Create an executable bash script named `userPromptSubmit.sh`.

```bash
mkdir -p .claude/hooks
touch .claude/hooks/userPromptSubmit.sh
chmod +x .claude/hooks/userPromptSubmit.sh
```

### 3. The Hook Script
Copy this into `.claude/hooks/userPromptSubmit.sh`:

```bash
#!/usr/bin/env bash
# Claude Code Intercept Hook via llm-gate

PROMPT="$1"

# 1. Ask llm-gate to evaluate the prompt (returns JSON)
# We default to "medium" criticality. llm-gate will bump it to "critical" automatically
# if it detects words like "auth", "payment", or "production_api" in the prompt text.
DECISION_JSON=$(llm-gate route "$PROMPT" --criticality medium 2>/dev/null | sed -n '/^{/,$p')

# 2. Extract the safe model target
TARGET_MODEL=$(echo "$DECISION_JSON" | grep -o '"model": "[^"]*' | cut -d'"' -f4)

# 3. Export the target override for OmniRoute / claude-code
if [ -n "$TARGET_MODEL" ]; then
    export CLAUDE_MODEL="$TARGET_MODEL"
    echo "[llm-gate] Routing task to: $TARGET_MODEL"
fi

# Pass control back to Claude Code
exit 0
```

### Expected Behavior
Now, when you type a prompt in Claude Code:
1. `"Write a new JWT validation function"` -> `llm-gate` detects the security keyword, sets `CLAUDE_MODEL="claude-3-opus-20240229"`.
2. `"Can you add docstrings to this file?"` -> `llm-gate` checks headroom and sets `CLAUDE_MODEL="claude-3-5-haiku-20241022"` (saving you roughly 95% of the token cost).
