with open('llm_gate/cli.py', 'r') as f:
    orig = f.read()

# I will cleanly rewrite those lines
new_content = orig.replace('console.print("\n  [bold cyan]', 'console.print("  [bold cyan]')
new_content = new_content.replace('--force[/bold cyan]\n")', '--force[/bold cyan]")')

# Wait, in the actual file it is literally a multiline string from bash expansion.
# I will just write a regex or explicit replace for the exact lines 186-188 and 196-198.
lines = new_content.split('\n')

cleaned_lines = []
skip = False
for i, line in enumerate(lines):
    if line.startswith('            console.print("') and len(line) == 27:
        cleaned_lines.append('            console.print("\\n  [bold cyan]pipx install \\"llm-gate[all] @ git+https://github.com/mrnicholasbcarter-code/llm-gate.git\\" --force[/bold cyan]\\n")')
        continue
    if line.startswith('  [bold cyan]pipx install "llm-gate[all]'):
        continue
    if line.startswith('")'):
        continue
    cleaned_lines.append(line)

with open('llm_gate/cli.py', 'w') as f:
    f.write('\n'.join(cleaned_lines))
