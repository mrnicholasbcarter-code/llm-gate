with open('llm_gate/cli.py', 'r') as f:
    text = f.read()

broken = """    elif args.command == "ui":
        from llm_gate.dashboard import start_ui
        start_ui()"""

fixed = """    elif args.command == "ui":
        try:
            from llm_gate.dashboard import start_ui
            start_ui()
        except ImportError:
            console.print("[bold red]❌ UI dependencies not found.[/bold red]")
            console.print("Please install the UI package suite:")
            console.print("\n  [bold cyan]pipx install \"llm-gate[all] @ git+https://github.com/mrnicholasbcarter-code/llm-gate.git\" --force[/bold cyan]\n")
            sys.exit(1)"""

fixed_content = text.replace(broken, fixed)
with open('llm_gate/cli.py', 'w') as f:
    f.write(fixed_content)
