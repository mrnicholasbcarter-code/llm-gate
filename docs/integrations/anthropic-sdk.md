# Anthropic Claude & Agent SDKs

If you are writing raw Python or TypeScript using the official Anthropic SDKs (or Anthropic's newer Agent/Tool-Use Frameworks), you can use `llm-gate` directly in your code as a policy function. 

This prevents your agent loops from burning `opus` tokens on simple tool iterations.

### Python SDK Integration

```python
import anthropic
from llm_gate import Gate

# Initialize your Anthropic client and the Router
client = anthropic.Anthropic()
gate = Gate(primary_model="claude-3-opus-20240229")

def execute_agent_loop(prompt: str):
    # 1. Ask llm-gate what model is safe to use for this specific step
    decision = gate.route(prompt)
    
    # 2. Extract just the model name (stripping 'anthropic/' if necessary)
    target_model = decision.model.replace("anthropic/", "")
    
    # 3. Execute the official SDK call
    response = client.messages.create(
        model=target_model,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response

# This triggers the T0 gate (keywords: 'payment') -> runs on Opus
execute_agent_loop("Implement the payment confirmation webhook")

# This is a safe task -> offloads to Haiku/Sonnet based on your config
execute_agent_loop("Format these text strings into a Python List")
```

This pattern works identically for the **TypeScript SDK** by querying the `llm-gate serve` HTTP endpoint before building the `anthropic.messages.create()` payload.
