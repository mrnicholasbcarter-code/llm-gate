#!/usr/bin/env bash
set -e

# llm-gate headless quickstart script
# Usage: curl -sSL https://.../quickstart.sh | bash -s -- [options]
# Options:
#   --primary-model MODEL   Set the Tier-0 critical model (default: anthropic/claude-3-opus-20240229)
#   --lite                  Do not install the rich TUI CLI elements (engine only)

PRIMARY_MODEL="anthropic/claude-3-opus-20240229"
INSTALL_TARGET="llm-gate[rich,pyyaml]"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --primary-model) PRIMARY_MODEL="$2"; shift ;;
        --lite) INSTALL_TARGET="llm-gate" ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo "⚙️  Configuring llm-gate headless mode..."
echo "✅ Targeting Primary Model: $PRIMARY_MODEL"

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/llm-gate"
mkdir -p "$CONFIG_DIR"

cat << YAML > "$CONFIG_DIR/llm-gate.yaml"
primary_model: "$PRIMARY_MODEL"
log_path: "llm-gate-decisions.jsonl"
providers:
  anthropic:
    base_url: "https://api.anthropic.com/v1"
    api_key_env: "ANTHROPIC_API_KEY"
    priority: 10
  groq:
    base_url: "https://api.groq.com/openai/v1"
    api_key_env: "GROQ_API_KEY"
    priority: 8
  ollama:
    base_url: "http://localhost:11434/v1"
    priority: 5
YAML

echo "✅ Created baseline config at $CONFIG_DIR/llm-gate.yaml"
echo "📦 Installing $INSTALL_TARGET via pip..."

if command -v pipx &> /dev/null; then
    pipx install "$INSTALL_TARGET"
else
    pip install "$INSTALL_TARGET"
fi

echo "🚀 llm-gate setup complete!"
echo "Run 'llm-gate route \"hello world\"' to verify."
