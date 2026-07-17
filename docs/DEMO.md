# Reproducible flagship demo

The public demo is intentionally a mock scenario, not a provider integration.
It proves the contract and explainability slice without credentials, network
access, a running gateway, or a mutable local decision log.

## Run it

From the repository root:

```bash
python scripts/flagship_demo.py
```

For a clean-room check, unset provider variables first if desired:

```bash
env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u LLMGATE_UPSTREAM_API_KEY \
  python scripts/flagship_demo.py
```

The command prints one JSON document. The fixture timestamp, policy version,
candidate IDs, and ordering are fixed, so repeated runs produce byte-identical
output. It does not read environment variables or write files.

## What the scenario demonstrates

The task asks for `tools` and `structured_output` and is protected. Four fake
catalog/runtime rows are evaluated:

| Candidate | Result | Evidence |
|---|---|---|
| `demo/frontier-tools` | eligible and selected | Required capabilities, healthy observation, quota remaining |
| `demo/no-tools` | excluded | Missing `tools` |
| `demo/quota-empty` | excluded | Quota exhausted |
| `demo/unverified` | excluded | Health unknown; protected work cannot use it |

The JSON contains the original `TaskSpec`, normalized requirements, the eligible
list, every candidate explanation, and a `RoutingDecisionContract` with the
selected route and exclusions. No prompt beyond the fixed fixture objective,
credentials, provider responses, or raw runtime payloads are emitted.

## Verify it

```bash
python scripts/flagship_demo.py > /tmp/llm-gate-demo-1.json
python scripts/flagship_demo.py > /tmp/llm-gate-demo-2.json
cmp /tmp/llm-gate-demo-1.json /tmp/llm-gate-demo-2.json
.venv/bin/pytest -q tests/test_flagship_demo.py
```

The test also checks that the selected route and all exclusion reasons remain
stable. This is evidence for the deterministic contract/eligibility slice; it
is not evidence of provider quality, end-to-end model execution, or production
readiness.
