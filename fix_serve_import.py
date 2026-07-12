with open('llm_gate/cli.py', 'r') as f:
    text = f.read()

broken = """    elif args.command == "serve":
        from llm_gate.api import start_server
        start_server(args.port)"""

fixed = """    elif args.command == "serve":
        try:
            from llm_gate.api import start_server
            start_server(args.port)
        except ImportError:
            console.print("[bold red]❌ Server dependencies not found.[/bold red]")
            console.print("Please install the FastAPI server suite:")
            console.print("\n  [bold cyan]pipx install \"llm-gate[all] @ git+https://github.com/mrnicholasbcarter-code/llm-gate.git\" --force[/bold cyan]\n")
            sys.exit(1)"""

fixed_content = text.replace(broken, fixed)
with open('llm_gate/cli.py', 'w') as f:
    f.write(fixed_content)
