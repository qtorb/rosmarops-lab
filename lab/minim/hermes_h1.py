#!/usr/bin/env python3
"""BV-310 H1: with Hermes Agent's terminal backend set to docker, do its
`memory` and `skill_manage` tools still write on the computer?

It calls the tools the way Hermes does, with no model and no key:
- `write_file` and `skill_manage` through model_tools.handle_function_call,
  the agent's own dispatch;
- `memory` through tools.memory_tool.memory_tool with the on-disk store, as
  the agent loop does (agent/inline_tool_executors.py, _memory).

The steps, each recorded as "<id> ok|fail" in STEPS_FILE:
- import: Hermes's tool modules load;
- control_in_container: a write_file to a fresh /tmp path is readable back
  through read_file and is absent from the computer, so the docker backend
  is the one in use. If this fails, the test proves nothing;
- memory_on_host: memory add writes <HERMES_HOME>/memories/*.md here;
- skill_on_host: skill_manage create writes a SKILL.md under
  <HERMES_HOME>/skills here;
- skill_script_on_host: skill_manage write_file writes scripts/run.py of that
  skill here.

The job's log is public: only the step ids and ok/fail are printed. Any error
goes to ERRORS_FILE, which is neither printed nor uploaded.

If the import fails, FACTS_FILE gets import_error (the exception's type)
and, for a missing module, import_missing_module (its name): closed values,
checked here and again by result.py, never raw output.

usage: hermes_h1.py HERMES_REPO STEPS_FILE ERRORS_FILE FACTS_FILE
"""

import json
import os
import re
import pathlib
import sys
import traceback
import uuid

repo, steps_path, errors_path, facts_path = sys.argv[1:5]
home = pathlib.Path(os.environ["HERMES_HOME"])
sys.path.insert(0, repo)


def record(step, ok):
    with open(steps_path, "a", encoding="utf-8") as f:
        f.write(f"{step} {'ok' if ok else 'fail'}\n")
    print(f"step {step}: {'ok' if ok else 'fail'}", flush=True)
    if not ok:
        sys.exit(0)  # the first failed step ends the test: the result is no


def note(step):
    with open(errors_path, "a", encoding="utf-8") as f:
        f.write(f"--- {step}\n{traceback.format_exc()}\n")


def fact(key, value, pattern):
    """A closed fact for result.json: written only if it matches pattern."""
    if isinstance(value, str) and re.fullmatch(pattern, value):
        with open(facts_path, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")


def success(raw):
    """A tool's JSON answer that is not an error."""
    try:
        d = json.loads(raw)
    except Exception:
        return False
    return isinstance(d, dict) and d.get("success") is not False and not d.get("error")


try:
    import model_tools
    from tools import memory_tool as mt

    ok = True
except Exception as e:
    note("import")
    fact("import_error", type(e).__name__, r"[A-Za-z][A-Za-z0-9_]{0,59}")
    if isinstance(e, ModuleNotFoundError):
        fact("import_missing_module", e.name, r"[A-Za-z_][A-Za-z0-9_.]{0,99}")
    ok = False
record("import", ok)

# The control: a file tool runs in the container, so its file is not here.
marker = f"rosmarops-lab-h1-{uuid.uuid4().hex}"
control = f"/tmp/{marker}.txt"
try:
    w = model_tools.handle_function_call("write_file", {"path": control, "content": marker}, task_id="lab-h1")
    r = model_tools.handle_function_call("read_file", {"path": control}, task_id="lab-h1")
    ok = success(w) and marker in r and not os.path.exists(control)
except Exception:
    note("control_in_container")
    ok = False
record("control_in_container", ok)

# memory: the agent loop's call, with the on-disk store.
try:
    store = mt.load_on_disk_store()
    raw = mt.memory_tool(action="add", target="memory", content="RosmarOps lab test note.", store=store)
    written = list((home / "memories").glob("*.md")) if (home / "memories").exists() else []
    ok = success(raw) and any(p.stat().st_size > 0 for p in written)
except Exception:
    note("memory_on_host")
    ok = False
record("memory_on_host", ok)

# skill_manage create: a SKILL.md under <HERMES_HOME>/skills.
skill_md = "---\nname: rosmarops-lab-h1\ndescription: A test skill made by the RosmarOps lab.\n---\n\n# Lab test\n\nNothing to do.\n"
try:
    raw = model_tools.handle_function_call(
        "skill_manage", {"action": "create", "name": "rosmarops-lab-h1", "content": skill_md}, task_id="lab-h1")
    found = list((home / "skills").rglob("rosmarops-lab-h1/SKILL.md")) if (home / "skills").exists() else []
    ok = success(raw) and len(found) == 1
except Exception:
    note("skill_on_host")
    ok = False
record("skill_on_host", ok)

# skill_manage write_file: a script of that skill.
try:
    raw = model_tools.handle_function_call(
        "skill_manage",
        {"action": "write_file", "name": "rosmarops-lab-h1", "file_path": "scripts/run.py", "file_content": "print('lab')\n"},
        task_id="lab-h1")
    found = list((home / "skills").rglob("rosmarops-lab-h1/scripts/run.py"))
    ok = success(raw) and len(found) == 1
except Exception:
    note("skill_script_on_host")
    ok = False
record("skill_script_on_host", ok)
