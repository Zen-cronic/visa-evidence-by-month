"""Check the Skill's capability trace against UGREEN's capability catalog.

Usage: python3 -I tools/capcheck/check_trace.py <path-to-uliya-skill-kit>
Checks that every action the Skill relies on exists for the named CLI and agent, that every
parameter it relies on exists, that Steps 1 to 6 use only read actions, that every write
is in Step 8 behind an approval gate, and that SKILL.md's delegate targets and capability
evidence match the trace.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
kit = Path(sys.argv[1])
catalog = json.loads((kit / "data" / "capability-catalog.json").read_text())
trace = json.loads((ROOT / "tools" / "capcheck" / "trace.json").read_text())
skill = (ROOT / "relationship-evidence-pack" / "SKILL.md").read_text()

clis = {c["name"]: c for c in catalog["clis"]}
errors = []
if catalog["catalogVersion"] != trace["catalogVersion"]:
    errors.append(f"catalog {catalog['catalogVersion']} != trace {trace['catalogVersion']}")

rows = []
for s in trace["steps"]:
    cli = clis.get(s["cli"])
    if cli is None:
        errors.append(f"step {s['step']}: no CLI {s['cli']}")
        continue
    if cli.get("agent") != s["agent"]:
        errors.append(f"step {s['step']}: {s['cli']} belongs to {cli.get('agent')}, not {s['agent']}")
    actions = {a["name"]: a for a in cli["actions"]}
    for name in s["actions"]:
        a = actions.get(name)
        if a is None:
            errors.append(f"step {s['step']}: {s['cli']} has no action {name}")
            continue
        params = {p["name"] for p in a["parameters"]}
        for p in s.get("params", {}).get(name, []):
            if p not in params:
                errors.append(f"step {s['step']}: {s['cli']} {name} has no parameter {p}")
        effect, approval = a.get("effect"), a.get("approval")
        if s.get("writes"):
            if s["step"] != "8":
                errors.append(f"write action {name} outside Step 8")
            if approval in (None, "none"):
                errors.append(f"step 8: {name} has no approval gate")
        elif effect != "read":
            errors.append(f"step {s['step']}: {name} is {effect}, expected read")
        rows.append((s["step"], s["agent"], s["cli"], name, effect, approval))

targets = set(re.findall(r"delegate --target (\S+)", skill))
traced = {s["agent"] for s in trace["steps"]}
if targets != traced:
    errors.append(f"SKILL.md delegate targets {sorted(targets)} != traced agents {sorted(traced)}")
evidence = set(re.findall(r"^- `([\w-]+)` → `([\w-]+)`$", skill, re.M))
traced_pairs = {(s["cli"], s["agent"]) for s in trace["steps"]}
if evidence != traced_pairs:
    errors.append(f"capability evidence {sorted(evidence)} != traced {sorted(traced_pairs)}")

print(f"catalog {catalog['catalogVersion']}: {len(rows)} actions traced")
for r in rows:
    print("  step {:<3} {:<16} {:<14} {:<17} effect={:<13} approval={}".format(*r))
if errors:
    print("FAILED")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print("OK: every action exists, Steps 1-6 only read, every write is in Step 8 behind approval")
