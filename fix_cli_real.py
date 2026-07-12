with open('llm_gate/cli.py', 'r') as f:
    orig = f.read()

broken = """    elif args.command == "ui":
        try:
            import streamlit
            import llm_gate.dashboard as dash
            import subprocess, sys, os
            dash_path = os.path.abspath(dash.__file__)
            subprocess.run([sys.executable, "-m", "streamlit", "run", dash_path])"""

fixed = """    elif args.command == "ui":
        try:
            import streamlit
            import subprocess, sys, os
            # Resolve the path dynamically without executing the file
            import importlib.util
            spec = importlib.util.find_spec("llm_gate.dashboard")
            if not spec or not spec.origin:
                console.print("[bold red]❌ Dashboard module missing.[/bold red]")
                sys.exit(1)
            subprocess.run([sys.executable, "-m", "streamlit", "run", spec.origin])"""

new_content = orig.replace(broken, fixed)
with open('llm_gate/cli.py', 'w') as f:
    f.write(new_content)
