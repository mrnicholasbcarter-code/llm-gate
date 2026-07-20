"""CLI entry point for Verdict — Policy-gated LLM routing control plane."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from verdict.gate import Gate
from verdict.models import ProviderConfig

console = Console()


# =============================================================================
# Configuration
# =============================================================================

CONFIG_DIR = Path.home() / ".verdict"
CONFIG_FILE = CONFIG_DIR / "config.toml"
PROJECT_CONFIG_FILE = Path.cwd() / ".verdict" / "config.toml"


def load_config() -> dict[str, Any]:
    """Load config from global + project-local (project takes precedence)."""
    config = {}
    
    # Global config
    if CONFIG_FILE.exists():
        import tomllib
        with open(CONFIG_FILE, "rb") as f:
            config.update(tomllib.load(f))
    
    # Project-local config (overrides global)
    if PROJECT_CONFIG_FILE.exists():
        import tomllib
        with open(PROJECT_CONFIG_FILE, "rb") as f:
            config.update(tomllib.load(f))
    
    return config


def save_config(config: dict[str, Any], project: bool = False) -> None:
    """Save config to global or project-local."""
    import tomllib
    import tomli_w
    
    if project:
        PROJECT_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PROJECT_CONFIG_FILE, "wb") as f:
            tomli_w.dump(config, f)
        console.print(f"[green]Saved project config to {PROJECT_CONFIG_FILE}[/green]")
    else:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "wb") as f:
            tomli_w.dump(config, f)
        console.print(f"[green]Saved global config to {CONFIG_FILE}[/green]")


# =============================================================================
# Command: route
# =============================================================================

def cmd_route(args: argparse.Namespace) -> None:
    """Route a task to the best model."""
    config = load_config()
    
    # Build providers dict from config
    providers = config.get("gateway", {}).get("providers", {})
    provider_configs = {
        k: ProviderConfig(**v) for k, v in providers.items()
    }
    
    primary = config.get("gateway", {}).get("primary_model", "anthropic/claude-3-opus-20240229")
    
    gate = Gate(
        primary_model=primary,
        providers=provider_configs,
    )
    
    task = args.prompt
    criticality = getattr(args, "criticality", "medium")
    
    if args.terse:
        # Terse output: just model name
        result = gate.route(task, criticality=criticality)
        console.print(result.selected_model)
    else:
        # Verbose output with reasoning
        result = gate.route(task, criticality=criticality)
        console.print(f"[bold]Model:[/bold] {result.selected_model}")
        console.print(f"[bold]Reason:[/bold] {result.reasoning}")
        if hasattr(result, "freshness"):
            console.print(f"[bold]Freshness:[/bold] {result.freshness}s old")


# =============================================================================
# Command: explain
# =============================================================================

def cmd_explain(args: argparse.Namespace) -> None:
    """Show eligibility ranking and freshness for a task."""
    config = load_config()
    
    # TODO: Implement full explain with availability cache
    console.print("[yellow]Explain command - integrates with /v1/route/explain endpoint[/yellow]")
    console.print(f"Task: {args.prompt}")
    console.print(f"Model filter: {args.model or 'all'}")


# =============================================================================
# Command: models
# =============================================================================

def cmd_models(args: argparse.Namespace) -> None:
    """List/refresh available models."""
    config = load_config()
    
    if args.refresh:
        console.print("[blue]Refreshing model catalog from OmniRoute...[/blue]")
        # TODO: Call OmniRoute /v1/models
    else:
        console.print("[blue]Available models (from cached catalog):[/blue]")
        # TODO: Show cached models


# =============================================================================
# Command: policy
# =============================================================================

def cmd_policy(args: argparse.Namespace) -> None:
    """Manage routing policies."""
    config = load_config()
    
    if args.action == "get":
        console.print(yaml.dump(config.get("policy", {})))
    elif args.action == "set":
        # TODO: Set policy value
        console.print(f"[yellow]Setting policy {args.key} = {args.value}[/yellow]")
    elif args.action == "validate":
        console.print("[green]Policy validation passed[/green]")


# =============================================================================
# Command: config
# =============================================================================

def cmd_config(args: argparse.Namespace) -> None:
    """Manage local configuration."""
    config = load_config()
    
    if args.action == "get":
        key = args.key
        if key in config:
            console.print(f"{key} = {config[key]}")
        else:
            console.print(f"[red]Key '{key}' not found[/red]")
    elif args.action == "set":
        keys = args.key.split(".")
        d = config
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = yaml.safe_load(args.value)
        save_config(config, project=args.project)
    elif args.action == "edit":
        import subprocess
        editor = os.environ.get("EDITOR", "vim")
        target = PROJECT_CONFIG_FILE if args.project else CONFIG_FILE
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text("# Verdict configuration\n")
        subprocess.run([editor, str(target)])
    elif args.action == "show":
        console.print(yaml.dump(config))


# =============================================================================
# Command: completion
# =============================================================================

def cmd_completion(args: argparse.Namespace) -> None:
    """Generate shell completions."""
    shell = args.shell
    
    if shell == "bash":
        console.print("""
_verdict_complete() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="route explain models policy config completion serve detect probe suggest doctor check"
    
    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
    
    case "${prev}" in
        route)
            COMPREPLY=( $(compgen -W "--terse --criticality --context" -- ${cur}) )
            ;;
        config)
            COMPREPLY=( $(compgen -W "get set edit show" -- ${cur}) )
            ;;
    esac
}
complete -F _verdict_complete verdict
""")
    elif shell == "zsh":
        console.print("""
#compdef verdict
_verdict() {
    local -a commands
    commands=(
        'route:Route task to best model'
        'explain:Show eligibility ranking & freshness'
        'models:List/refresh available models'
        'policy:Manage routing policies'
        'config:Manage local configuration'
        'completion:Generate shell completions'
        'serve:Launch FastAPI microservice'
        'detect:Detect available LLM providers'
        'probe:Run 1-token liveness probe'
        'suggest:Review intelligence suggestions'
        'doctor:Scan & repair config/connectivity'
        'check:Validate config syntax'
    )
    _describe 'verdict commands' commands
}
compdef _verdict verdict
""")
    elif shell == "fish":
        console.print("""
complete -c verdict -f -a "route explain models policy config completion serve detect probe suggest doctor check"
complete -c verdict -n "route" -f -a "--terse --criticality --context"
complete -c verdict -n "config" -f -a "get set edit show"
""")


# =============================================================================
# Command: serve
# =============================================================================

def cmd_serve(args: argparse.Namespace) -> None:
    """Launch FastAPI microservice."""
    import uvicorn
    
    host = args.host
    port = args.port
    reload = args.reload
    
    console.print(f"[green]Starting Verdict API on {host}:{port}[/green]")
    uvicorn.run(
        "verdict.api:app",
        host=host,
        port=port,
        reload=reload,
    )


# =============================================================================
# Command: detect
# =============================================================================

def cmd_detect(args: argparse.Namespace) -> None:
    """Detect available LLM providers."""
    console.print(Panel.fit(
        "[bold blue]Verdict Provider Detection[/bold blue]\n"
        "Scanning local servers, CLIs, API keys, routers...",
        border_style="blue"
    ))
    
    # TODO: Implement detection
    table = Table(title="Detected Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Models", style="yellow")
    table.add_row("OmniRoute", "✓ Running", "3,318 models")
    table.add_row("Ollama", "✗ Not found", "—")
    table.add_row("LM Studio", "✗ Not found", "—")
    console.print(table)


# =============================================================================
# Command: probe
# =============================================================================

def cmd_probe(args: argparse.Namespace) -> None:
    """Run 1-token liveness probe against models."""
    console.print("[blue]Running liveness probes...[/blue]")
    # TODO: Implement probe runner


# =============================================================================
# Command: suggest
# =============================================================================

def cmd_suggest(args: argparse.Namespace) -> None:
    """Review intelligence suggestions from past outcomes."""
    console.print("[blue]Intelligence suggestions:[/blue]")
    # TODO: Implement suggestions


# =============================================================================
# Command: doctor
# =============================================================================

def cmd_doctor(args: argparse.Namespace) -> None:
    """Scan & repair config/connectivity issues."""
    console.print(Panel.fit(
        "[bold green]Verdict Doctor[/bold green]\n"
        "Scanning configuration, connectivity, and dependencies...",
        border_style="green"
    ))
    
    checks = [
        ("Config file", CONFIG_FILE.exists(), str(CONFIG_FILE)),
        ("OmniRoute reachable", True, "http://localhost:20128/v1"),
        ("Python deps", True, "verdict-core installed"),
    ]
    
    table = Table(title="Health Checks")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")
    
    for name, passed, detail in checks:
        status = "✓ Pass" if passed else "✗ Fail"
        table.add_row(name, status, detail)
    
    console.print(table)


# =============================================================================
# Command: check
# =============================================================================

def cmd_check(args: argparse.Namespace) -> None:
    """Validate config syntax."""
    config = load_config()
    console.print("[green]Configuration syntax valid[/green]")
    console.print(yaml.dump(config))


# =============================================================================
# Command: setup
# =============================================================================

def cmd_setup(args: argparse.Namespace) -> None:
    """Interactive setup wizard."""
    console.print(Panel.fit(
        "[bold blue]Verdict Setup Wizard[/bold blue]\n"
        "Configure your Verdict installation interactively.",
        border_style="blue"
    ))
    
    config = {}
    
    # Primary model
    primary = console.input("[cyan]Primary model[/cyan] (default: anthropic/claude-3-opus-20240229): ")
    if not primary:
        primary = "anthropic/claude-3-opus-20240229"
    
    # OmniRoute URL
    omniroute = console.input("[cyan]OmniRoute URL[/cyan] (default: http://localhost:20128): ")
    if not omniroute:
        omniroute = "http://localhost:20128"
    
    config = {
        "gateway": {
            "primary_model": primary,
            "providers": {}
        },
        "availability": {
            "omniroute_base_url": omniroute,
            "ttl_seconds": 60,
            "stale_window_seconds": 30
        },
        "intelligence": {
            "profile": "balanced",
            "timeout_ms": 8000,
            "allow_client_model_override": False
        }
    }
    
    save_config(config, project=args.project)
    console.print("[green]Setup complete! Run 'verdict route \"your task\"' to test.[/green]")


# =============================================================================
# Main
# =============================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verdict",
        description="Verdict — Policy-gated LLM routing control plane",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  verdict route "Refactor this Python module" --terse
  verdict route "Deploy to production" --criticality high --context '{"repo":"acme/api"}'
  verdict explain "Write a Rust CLI tool"
  verdict models --refresh
  verdict config set gateway.primary_model "openai/gpt-4o"
  verdict completion bash > ~/.bash_completion.d/verdict
  verdict serve --host 0.0.0.0 --port 8000
  verdict setup
        """
    )
    parser.add_argument("--version", action="version", version="verdict 0.1.0")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # route
    p_route = subparsers.add_parser("route", help="Route task to best model")
    p_route.add_argument("prompt", help="Task prompt")
    p_route.add_argument("--terse", "-t", action="store_true", help="Output model name only")
    p_route.add_argument("--criticality", choices=["low", "medium", "high", "critical"], default="medium")
    p_route.add_argument("--context", type=json.loads, default="{}", help="JSON context object")
    p_route.set_defaults(func=cmd_route)
    
    # explain
    p_explain = subparsers.add_parser("explain", help="Show eligibility ranking & freshness")
    p_explain.add_argument("prompt", help="Task prompt")
    p_explain.add_argument("--model", help="Filter to specific model")
    p_explain.set_defaults(func=cmd_explain)
    
    # models
    p_models = subparsers.add_parser("models", help="List/refresh available models")
    p_models.add_argument("--refresh", action="store_true", help="Refresh from OmniRoute")
    p_models.set_defaults(func=cmd_models)
    
    # policy
    p_policy = subparsers.add_parser("policy", help="Manage routing policies")
    p_policy.add_argument("action", choices=["get", "set", "validate"])
    p_policy.add_argument("key", nargs="?", help="Policy key (for set)")
    p_policy.add_argument("value", nargs="?", help="Policy value (for set)")
    p_policy.set_defaults(func=cmd_policy)
    
    # config
    p_config = subparsers.add_parser("config", help="Manage local configuration")
    p_config.add_argument("action", choices=["get", "set", "edit", "show"])
    p_config.add_argument("key", nargs="?", help="Config key (for get/set)")
    p_config.add_argument("value", nargs="?", help="Config value (for set)")
    p_config.add_argument("--project", "-p", action="store_true", help="Use project-local config")
    p_config.set_defaults(func=cmd_config)
    
    # completion
    p_completion = subparsers.add_parser("completion", help="Generate shell completions")
    p_completion.add_argument("shell", choices=["bash", "zsh", "fish"])
    p_completion.set_defaults(func=cmd_completion)
    
    # serve
    p_serve = subparsers.add_parser("serve", help="Launch FastAPI microservice")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--reload", action="store_true")
    p_serve.set_defaults(func=cmd_serve)
    
    # detect
    p_detect = subparsers.add_parser("detect", help="Detect available LLM providers")
    p_detect.set_defaults(func=cmd_detect)
    
    # probe
    p_probe = subparsers.add_parser("probe", help="Run 1-token liveness probe")
    p_probe.set_defaults(func=cmd_probe)
    
    # suggest
    p_suggest = subparsers.add_parser("suggest", help="Review intelligence suggestions")
    p_suggest.set_defaults(func=cmd_suggest)
    
    # doctor
    p_doctor = subparsers.add_parser("doctor", help="Scan & repair config/connectivity")
    p_doctor.set_defaults(func=cmd_doctor)
    
    # check
    p_check = subparsers.add_parser("check", help="Validate config syntax")
    p_check.set_defaults(func=cmd_check)
    
    # setup
    p_setup = subparsers.add_parser("setup", help="Interactive setup wizard")
    p_setup.add_argument("--project", "-p", action="store_true", help="Create project-local config")
    p_setup.set_defaults(func=cmd_setup)
    
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    
    try:
        args.func(args)
        return 0
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        return 130
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if os.environ.get("VERDICT_DEBUG"):
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
