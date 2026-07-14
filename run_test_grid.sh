#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ -z "${PYTHON:-}" ]]; then
  if [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
    PYTHON="$VIRTUAL_ENV/bin/python"
  elif [[ -x "$ROOT/.venv/bin/python" ]]; then
    PYTHON="$ROOT/.venv/bin/python"
  else
    cat >&2 <<'EOF'
No project Python environment was found.
Create one and install the declared test dependencies:

  python3 -m venv .venv
  .venv/bin/python -m pip install -e '.[dev,server]'

To use another environment, set PYTHON=/absolute/path/to/python.
EOF
    exit 2
  fi
fi

if ! "$PYTHON" -c 'import pytest, fastapi' >/dev/null 2>&1; then
  cat >&2 <<'EOF'
The selected Python environment is missing llm-gate test dependencies.
Install the declared test environment with:

  "$PYTHON" -m pip install -e '.[dev,server]'
EOF
  exit 2
fi

echo "=== RUNNING FUNCTIONAL TEST GRID ==="
if [[ "${FULL:-0}" == "1" ]]; then
  TARGET="tests"
else
  TARGET="${TEST_TARGET:-tests/test_cli_smoke.py}"
fi

"$PYTHON" -m pytest "$TARGET"
