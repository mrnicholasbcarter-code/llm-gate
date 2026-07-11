# Aider Integration

[Aider](https://aider.chat/) is one of the most popular terminal-based AI coding agents. While Aider is incredibly powerful, it can consume massive amounts of tokens reading files.

You can safely wrap Aider so that it dynamically switches to a cheaper model for simple queries and escalates for complex architecture refactors.

### Bash Wrapper

```bash
# Add to ~/.bashrc or ~/.zshrc
aider_routed() {
    local task="$*"
    # Evaluate criticality
    TARGET=$(llm-gate route "$task" | grep -o '• Model: .*' | awk '{print $3}' | sed 's/\[.*\]//g')
    
    # Execute Aider with the dynamic model override
    aider --model "$TARGET" --message "$task"
}
```
