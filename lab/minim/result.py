#!/usr/bin/env python3
"""BV-301: result.json of a lab test (the minimum of control's M6, BV-310's H1), from the steps the test
script recorded. The result is `yes` only when every expected step of the
criterion is recorded, once, as `ok`; anything else is `no`.

The file holds only ids, closed values, versions, dates, hashes and host
names: never raw output. Every value is checked against a fixed pattern and a
value that does not match stops the script, so nothing unexpected can reach
the published file.

usage: result.py CRITERION STEPS_FILE FACTS_FILE OUT_DIR

STEPS_FILE: one line per step, "<step id> ok" or "<step id> fail".
FACTS_FILE: one line per fact, "<key>=<value>".
Writes OUT_DIR/result.json and OUT_DIR/result.json.sha256, and prints one
line: "<criterion>: yes" or "<criterion>: no".
"""

import hashlib
import json
import os
import re
import sys

# The steps each criterion's test must pass, in order (BV-300 §1).
EXPECTED = {
    "M6": [
        "install",
        "start",
        "company",
        "agents",
        "wake",
        "two_running",
        "pause",
        "none_running_after_wait",
    ],
    # BV-310 H1: with Hermes Agent's terminal in a Docker container, where do
    # its memory and skill_manage tools write? yes = the control write stays
    # in the container and the three files appear on the computer.
    "H1": [
        "install",
        "import",
        "control_in_container",
        "memory_on_host",
        "skill_on_host",
        "skill_script_on_host",
    ],
}

HOST = r"[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+"
FACTS = {
    "product": re.compile(r"[a-z0-9-]{1,40}"),
    "product_version": re.compile(r"[0-9A-Za-z.+-]{1,40}"),
    "node_version": re.compile(r"v?[0-9]+\.[0-9]+\.[0-9]+"),
    "python_version": re.compile(r"[0-9]+\.[0-9]+\.[0-9]+"),
    "source_commit": re.compile(r"[0-9a-f]{40}"),
    "docker_image": re.compile(r"[a-z0-9./_-]{1,60}(:[A-Za-z0-9._-]{1,40})?"),
    "package_sha256": re.compile(r"[0-9a-f]{64}"),
    "runner_image": re.compile(r"[0-9A-Za-z._-]{1,60}"),
    "wait_seconds": re.compile(r"[0-9]{1,4}"),
    "install_hosts": re.compile(rf"({HOST})?(,{HOST})*"),
    "runs_running_seen": re.compile(r"[0-9]{1,5}"),
    "sleepers_seen": re.compile(r"[0-9]{1,5}"),
    "outside_connections_running": re.compile(r"[0-9]{1,5}"),
    "outside_connections_after": re.compile(r"[0-9]{1,5}"),
    "utc": re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"),
}


class Invalid(Exception):
    pass


def read_steps(path, expected):
    steps = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(" ")
        if len(parts) != 2 or parts[0] not in expected or parts[1] not in ("ok", "fail"):
            raise Invalid("a step line is not '<expected step> ok|fail'")
        steps.append({"id": parts[0], "result": parts[1]})
    return steps


def read_facts(path):
    facts = {}
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line:
            continue
        key, sep, value = line.partition("=")
        if not sep or key not in FACTS or not FACTS[key].fullmatch(value):
            raise Invalid("a fact line is not an allowed '<key>=<value>'")
        if key in facts:
            raise Invalid("a fact is recorded twice")
        facts[key] = value
    return facts


def verdict(steps, expected):
    """yes only if the expected steps are each recorded once, in order, as ok."""
    return "yes" if [s["id"] for s in steps] == expected and all(s["result"] == "ok" for s in steps) else "no"


def build(criterion, steps_path, facts_path):
    if criterion not in EXPECTED:
        raise Invalid("unknown criterion")
    expected = EXPECTED[criterion]
    steps = read_steps(steps_path, expected)
    facts = read_facts(facts_path)
    doc = {
        "schema": 1,
        "criterion": criterion,
        "result": verdict(steps, expected),
        "how": "test",
        "expected_steps": expected,
        "steps": steps,
    }
    for key in FACTS:
        if key in facts:
            value = facts[key]
            if key == "install_hosts":
                value = sorted(set(filter(None, value.split(","))))
            elif key in ("wait_seconds", "runs_running_seen", "sleepers_seen",
                         "outside_connections_running", "outside_connections_after"):
                value = int(value)
            doc[key] = value
    return doc


def main(argv):
    if len(argv) != 5:
        print("usage: result.py CRITERION STEPS_FILE FACTS_FILE OUT_DIR", file=sys.stderr)
        return 2
    criterion, steps_path, facts_path, out = argv[1:]
    try:
        doc = build(criterion, steps_path, facts_path)
    except Invalid as e:
        print(f"::error::result not written: {e}")
        return 1
    path = os.path.join(out, "result.json")
    data = (json.dumps(doc, indent=2, ensure_ascii=True) + "\n").encode()
    with open(path, "wb") as f:
        f.write(data)
    with open(path + ".sha256", "w", encoding="utf-8") as f:
        f.write(f"{hashlib.sha256(data).hexdigest()}  result.json\n")
    print(f"{criterion}: {doc['result']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
