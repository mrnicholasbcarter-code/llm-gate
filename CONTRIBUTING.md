# Contributing to llm-gate

Thanks for your interest. Here's how to contribute.

## Setup

```bash
git clone https://github.com/mrnicholasbcarter-code/llm-gate.git
cd llm-gate
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
```

## Running Tests

```bash
pytest
ruff check .
mypy llm_gate/
```

## Pull Requests

1. Fork the repo and create a branch from `main`.
2. Add tests for any new functionality.
3. Ensure `pytest`, `ruff check`, and `mypy` all pass.
4. Write a clear PR description explaining what and why.

## Design Principles

- **Zero dependencies.** The core library uses only the Python standard library.
- **Fail open.** If routing fails, fall back to the primary model. Never block work.
- **No magic.** The default router is a deterministic tier + keyword matcher. ML is optional.
- **Decision transparency.** Every routing decision is logged and explainable.

## Code Style

- Ruff for linting and formatting.
- Type hints on all public APIs.
- Docstrings on all public functions and classes.
- Tests live in `tests/` and mirror the `llm_gate/` structure.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
