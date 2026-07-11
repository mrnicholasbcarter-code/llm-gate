# Jcode Integration

Jcode is an advanced AI coding assistant that supports recursive multi-agent swarm coordination. 

When configuring a Jcode swarm (via `~/.jcode/swarm-prompt.md` or `.jcode/swarm-prompt.md`), you are encouraged to pass a `model` argument when spawning subagents. You can dynamically route these assignments by intercepting the CLI invocation.

### The Dynamic Alias

Add this to your `~/.bashrc`:

```bash
jcode_routed() {
    local task="$1"
    
    # Determine the safest model for this specific jcode task
    local model_id=$(llm-gate route "$task" | grep -o '• Model: .*' | awk '{print $3}' | sed 's/\[.*\]//g')
    
    # Run jcode, forcing the model selection
    JCODE_MODEL="$model_id" jcode "$task"
}
```

Now, typing `jcode_routed "audit the authentication middleware"` will instantly trigger an escalation in `llm-gate` (because of the keyword "authentication"), returning Tier-0 (e.g. `claude-3-opus`), and binding it to your Jcode session.
