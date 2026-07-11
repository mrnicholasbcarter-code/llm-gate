"""Command line interface for llm-gate."""
import argparse
import json
import dataclasses
from llm_gate.gate import Gate
from llm_gate.models import ProviderConfig

def main() -> None:
    parser = argparse.ArgumentParser(description="Route LLM tasks by criticality.")
    subparsers = parser.add_subparsers(dest="command")

    route_p = subparsers.add_parser("route", help="Route a task")
    route_p.add_argument("task", help="Task description")
    route_p.add_argument("--criticality", default="medium", choices=["critical", "high", "medium", "low"])

    args = parser.parse_args()

    if args.command == "route":
        # Simplified default Gate for the CLI demo
        gate = Gate(
            primary_model="anthropic/claude-3-5-sonnet",
            providers={
                "public_ollama": ProviderConfig(base_url="http://localhost:11434/v1")
            }
        )
        dec = gate.route(args.task, args.criticality)
        print(json.dumps(dataclasses.asdict(dec), indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
