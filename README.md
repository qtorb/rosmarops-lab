# rosmarops-lab

The RosmarOps capture lab (BV-250, design CTO-61): screenshots of what the
sandbox templates of Claude Code and Codex change on macOS, for the guide on
rosmarops.com. Everything runs on GitHub's `macos-latest` runner; nothing runs
on anyone's computer.

## What a run does

For each agent, as a test account `prueba` (or, if `sysadminctl` cannot create
it, the runner account with `HOME` in a temporary `prueba` folder; the
manifest says which):

1. **Before the template:** two tests, a listing of the home folder and a
   network test (the orders are in the table below).
2. **Step 1:** the template, written from the `templates.macos` field of
   `observatory/data/agents/<agent>.json` in qtorb/rosmarops-web at the commit
   given to the run. The capture is each file's content with its path.
3. **After the template:** the same two tests.

Only `claude -p` and `codex exec -c cli_auth_credentials_store=ephemeral` are
used: no interactive session, no tmux, no login (Albert, 16-11 20:09).

Each screen is saved as text first, reviewed for the key (its exact value,
compared without printing it, and the prefixes `sk-ant-`, `sk-proj-` and
`sk-`), and only then drawn as a PNG with
[freeze](https://github.com/charmbracelet/freeze) from that same text. A hit
stops the run and names only the file.

The results go to a release `lab-AAAAMMDD` with the PNGs, the reviewed texts,
`meta.json` per agent and `manifest.json` (agent, step, test, before/after,
command, result, versions, runner image, UTC date, web commit and the SHA-256
of every file).

## The orders

Each test asks the agent to run one order exactly and show its output:

| Agent | Test | Order | Allowed tool (Claude Code) |
|---|---|---|---|
| Claude Code | `ls` | `python3 -c "import os; print(sorted(os.listdir(os.path.expanduser('~'))))"` | `Bash(python3 *)` |
| Claude Code | `red` | `git ls-remote https://example.com` | `Bash(git ls-remote *)` |
| Codex | `ls` | `ls ~` | — |
| Codex | `red` | `curl -I https://example.com` | — |

Claude Code's `ls` test lists the home folder from Python, because Claude
Code refuses `ls ~` by itself, before any template: the home folder is outside
its working directory. A plain `ls ~` would show that refusal both before and
after, and nothing of the sandbox.

## How a result is read

The same fixed expressions read every answer (`lab/classify.py`):

| | The order worked | The order failed | Anything else (not run, another answer) |
|---|---|---|---|
| **Before the template** | `concluyente`: the starting point is seen | `inesperado`: it was expected to work before the template, so before and after cannot show what the template changes | `no_concluyente` |
| **After the template** | `inesperado`: the template did not stop it | `concluyente`: the error is the sandbox's | `no_concluyente`, also for a permission prompt or a missing folder |

Before the template, «worked» means that `ls` lists the four entries of the
test account (`Desktop`, `Documents`, `Downloads`, `proyecto`) and that the
network test reaches `example.com` (an HTTP answer or error, not a connection
error).

## Workflows

| Workflow | Trigger | Environment and secrets |
|---|---|---|
| `captures.yml` | `workflow_dispatch`, `main` only | `lab-captures` (Albert approves): `ANTHROPIC_API_KEY`, `CODEX_API_KEY` |
| `dry-run.yml` | `workflow_dispatch` | none: the agents are installed but never called |
| `checks.yml` | pull requests | none |

Spending is capped outside this repository: a separate Anthropic organisation
with 10 USD prepaid credit and no auto-reload, and an OpenAI project with a 10
USD hard limit. Claude Code calls also carry `--max-budget-usd 0.25`.

## Rules

- The keys exist only as secrets of the `lab-captures` environment.
- `main` changes only through a pull request reviewed by Albert.
- Nothing from here reaches the website until its own pull request is merged.
