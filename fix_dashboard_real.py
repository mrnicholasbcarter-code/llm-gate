with open("llm_gate/dashboard.py", "r") as f:
    orig = f.read()

# Replace the bare open hook
fixed = orig.replace("""    records = []
    with open(path, "r") as f:""", """    records = []
    import os
    if not os.path.exists(path):
        return pd.DataFrame()
    with open(path, "r") as f:""")

with open("llm_gate/dashboard.py", "w") as f:
    f.write(fixed)
