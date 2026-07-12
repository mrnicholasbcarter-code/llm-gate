# AI Agent Constraints & Architectural Context (.claude.md)

**Target Ecosystem:** Express.js Middleware / Next.js Routing
**Language:** Python 3.10+
**Primary Directive:** LLM API Cost Optimization and Fallback Orchestration.

## Directory Boundaries
- `/llm_gate/gate.py`: Core routing engine. Modifying heuristic logic here requires validating the execution tree in `tests/test_gate_unit.py`.
- `/llm_gate/discovery.py`: The integration connector. Only add OpenRouter/Ollama parsers here. 
- `/llm_gate/api.py`: FastAPI server layer. Must never be instantiated in global execution scopes.

## RAG Memory & Constraints
If an agent edits the parsing logic in `models.py`, ensure data structures remain mapped as `dataclass(frozen=True)` to prevent mutation across asynchronous generation loops.

## Deployment Gating
Do not update `pyproject.toml` dependencies natively without also checking `[server]` and `[ci]` optional blocks. `llm-gate` is headless by design.
