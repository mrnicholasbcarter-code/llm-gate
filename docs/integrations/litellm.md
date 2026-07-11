# LiteLLM Integration

[LiteLLM](https://litellm.ai/) is the industry standard open-source API proxy. If you run a centralized LiteLLM proxy for your team, you can use `llm-gate` as a custom Python router directly inside it.

Because `llm-gate` is a pure Python library, you can import it in your LiteLLM custom routing script to evaluate incoming traffic:

```python
# custom_router.py for LiteLLM
from litellm import Router
from llm_gate import Gate

gate = Gate(primary_model="anthropic/claude-3-opus-20240229")

async def custom_routing_logic(kwargs):
    prompt_text = str(kwargs.get("messages", ""))
    
    # Zero-network overhead evaluation
    decision = gate.route(prompt_text)
    
    # Overwrite the model before LiteLLM proxies the request
    kwargs["model"] = decision.model
    return kwargs
```
