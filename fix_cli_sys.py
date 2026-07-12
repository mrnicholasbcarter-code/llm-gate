with open("llm_gate/cli.py", "r") as f:
    orig = f.read()

# Make sure sys is imported to prevent UnboundLocalError
if "import sys" not in orig:
    orig = "import sys\n" + orig

with open("llm_gate/cli.py", "w") as f:
    f.write(orig)
