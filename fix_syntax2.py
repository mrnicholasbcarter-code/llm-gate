with open('llm_gate/cli.py', 'r') as f:
    orig = f.read()

bad_str = 'console.print("  [bold cyan]pipx install "llm-gate[all] @ git+https://github.com/mrnicholasbcarter-code/llm-gate.git" --force[/bold cyan]")'
good_str = "console.print('  [bold cyan]pipx install \"llm-gate[all] @ git+https://github.com/mrnicholasbcarter-code/llm-gate.git\" --force[/bold cyan]')"

new_content = orig.replace(bad_str, good_str)
with open('llm_gate/cli.py', 'w') as f:
    f.write(new_content)
