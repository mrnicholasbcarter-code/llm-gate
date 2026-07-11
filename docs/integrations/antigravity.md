# Antigravity (agy) Integration

Google DeepMind's Antigravity (`agy`) is a powerful agentic execution environment. By default, it runs on Gemini or your configured default model. You can seamlessly inject `llm-gate` into the `agy` execution path using a simple bash wrapper or environment variable injection.

### The Bash Wrapper Method

Add this to your `~/.bashrc` or `~/.zshrc`:

```bash
# llm-gate wrapper for Antigravity
agy_routed() {
    local task="$*"
    
    # 1. Ask llm-gate for the best model based on the task description
    echo "⚙️ Evaluating Antigravity task criticality..."
    local target_model=$(llm-gate route "$task" --criticality high | grep -o '• Model: .*' | awk '{print $3}' | sed 's/\[.*\]//g')
    
    echo "🚀 llm-gate selected: $target_model"
    
    # 2. Execute Antigravity with the dynamically routed model
    AGY_MODEL_OVERRIDE="$target_model" agy "$task"
}
```

**Usage:**
Instead of typing `agy "build a fast API"`, type `agy_routed "build a fast API"`. 
`llm-gate` intercepts the prompt, evaluates rate limits and regex gates, and forces `agy` to use the optimal model!
