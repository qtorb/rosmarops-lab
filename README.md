# rosmarops-lab

The RosmarOps capture lab (BV-250, design CTO-61): screenshots of what the
sandbox templates of Claude Code and Codex change on macOS, for the guide on
rosmarops.com. Everything runs on GitHub's `macos-latest` runner; nothing runs
on anyone's computer.

## What a run does

For each agent, as a test account `prueba` (or, if `sysadminctl` cannot create
it, the runner account with `HOME` in a temporary `prueba` folder; the
manifest says which):

1. **Before the template:** two tests, `ls ~` and a network test
   (`git ls-remote https://example.com` in Claude Code, `curl -I
   https://example.com` in Codex).
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
of every file). Results: `concluyente` (the error is the sandbox's),
`no_concluyente`, `inesperado` (the order worked after the template).

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
