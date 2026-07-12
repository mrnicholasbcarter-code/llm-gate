import re

with open("llm_gate/dashboard.py", "r") as f:
    text = f.read()

# Replace load_data logic to handle FileNotFoundError
broken = """def load_data(path):
    data = []
    with open(path, "r") as f:"""

fixed = """def load_data(path):
    import os
    data = []
    if not os.path.exists(path):
        return pd.DataFrame(columns=["ts", "req_tier", "latency_ms", "model", "provider", "tier", "reason", "escalated", "escalation_reason", "alternatives"])
    with open(path, "r") as f:"""

if broken in text:
    with open("llm_gate/dashboard.py", "w") as f:
        f.write(text.replace(broken, fixed))
