import re

with open("llm_gate/cli.py", "r") as f:
    text = f.read()

broken = """    elif args.command == "ui":
        try:
            from llm_gate.dashboard import start_ui
            start_ui()"""

# We use subprocess to spin up the streamlit server wrapper directly grabbing the file path from the pipx venv
fixed = """    elif args.command == "ui":
        try:
            import streamlit
            import llm_gate.dashboard as dash
            import subprocess, sys, os
            dash_path = os.path.abspath(dash.__file__)
            subprocess.run([sys.executable, "-m", "streamlit", "run", dash_path])
        """

if broken in text:
    with open("llm_gate/cli.py", "w") as f:
        f.write(text.replace(broken, fixed))

# Wait, the end of dashboard.py also actually tries to run UI code globally!
# In Streamlit, all code evaluates top-to-bottom. If there is a `start_ui()` wrapper with the code inside, it won't render unless it's outside. 
# Let me look at dashboard.py to make sure it's valid Streamlit code.
