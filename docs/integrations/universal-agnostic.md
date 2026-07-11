# Universal / Agnostic Integration

If you need to inject `llm-gate` into a completely unknown, proprietary, or brand-new AI tool, you have two universal fallbacks. 

Because `llm-gate` determines the routing policy without needing to proxy the actual bytes, you can inject it anywhere.

### 1. The Terse CLI Pipe (For Bash/CLI tools)

Every CLI tool on earth accepts environment variables or configuration flags. You can use the `--terse` flag to make `llm-gate` output **only** the model name evaluated for the prompt.

```bash
# Returns literally just: "anthropic/claude-3-opus-20240229"
TARGET_MODEL=$(llm-gate route "Review my database schema" --terse)

# Pipe this into ANY unknown CLI tool
unknown-ai-agent --model "$TARGET_MODEL" --execute
```

### 2. The Microservice Webhook (For web/backend tools)

If the tool doesn't live in a terminal (e.g., a SaaS platform, a Ruby on Rails backend, or a proprietary C++ trading system), run the `llm-gate` microservice.

```bash
llm-gate serve --port 8000
```

From any language, fire a standard HTTP POST request before you make your LLM call:

```bash
curl -X POST http://localhost:8000/v1/route \
  -H "Content-Type: application/json" \
  -d '{"task": "Analyze this CSV file", "criticality": "medium"}'

# Response:
# {"model": "groq/llama-3-8b", "tier": 3, "escalated": false, ...}
```
Extract `.model` from the JSON and pass it to your LLM API request.
