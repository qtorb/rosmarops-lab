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
| `minim-paperclip.yml` | `workflow_dispatch` | none: no environment, no secret, `permissions: {}` |

Spending is capped outside this repository: a separate Anthropic organisation
with 10 USD prepaid credit and no auto-reload, and an OpenAI project with a 10
USD hard limit. Claude Code calls also carry `--max-budget-usd 0.25`.

## Rules

- The keys exist only as secrets of the `lab-captures` environment.
- `main` changes only through a pull request reviewed by Albert.
- Nothing from here reaches the website until its own pull request is merged.

## Minimum of control: Paperclip M6

A separate test (BV-301), unrelated to the captures above. It answers one
criterion of RosmarOps's «minimum of control» for orchestrators, M6: *an
agent, and every run at once, can be stopped from the product.* Paperclip
documents how to pause one agent, but not how to stop everything at once.
Its code has one action that should: setting the company's status to
`paused` (`PATCH /api/companies/{id}`). This test checks what that action
does.

It uses no key and calls no model. The two agents use Paperclip's `process`
adapter and only run `sleep 600`. The workflow has no environment, no secret
and `permissions: {}`.

### What it installs

- Node 24.11, with `actions/setup-node`. Paperclip asks for Node `>=24.11.0`.
- `paperclipai@2026.1117.0` from npm, the release tagged `v2026.1117.0`
  (commit `c0f132898d2a2677312d8c72096187b27a3d9a38`). It is installed from
  its tarball, whose SHA-256 goes into the result.
- Nothing else. Paperclip brings its own embedded PostgreSQL.

### The steps

`lab/minim/paperclip.sh` records each step as `ok` or `fail`. The first
failed step ends the test.

| Step | What is checked |
|---|---|
| `install` | `npm pack paperclipai@2026.1117.0`, then `npm install` of that tarball into a temporary folder; the installed version is 2026.1117.0 |
| `start` | Paperclip starts with an empty environment (below) and `GET /api/health` answers 200 |
| `company` | `POST /api/companies` creates a made-up company |
| `agents` | `POST /api/companies/{id}/agents`, twice: adapter `process`, `command` `sleep`, `args` `["600"]` |
| `wake` | `POST /api/agents/{id}/heartbeat/invoke` for both |
| `two_running` | the company has two runs `running` (`GET /api/companies/{id}/heartbeat-runs`) and two `sleep 600` processes are alive |
| `pause` | one call: `PATCH /api/companies/{id}` with `{"status":"paused"}` |
| `none_running_after_wait` | after 60 seconds, no run is `running` and no `sleep 600` is left |

The result is `yes` only if every step is `ok`, and `no` otherwise.
`lab/minim/result.py` writes it to `result.json`, with:

- the steps;
- if the two agents did not both start, how many runs were `running` and how
  many `sleep 600` processes were alive at the last look;
- the Paperclip and Node versions;
- the package's SHA-256;
- the UTC date and the runner image;
- the hosts npm fetched from;
- two counts of Paperclip's connections to other machines.

Every value is checked against a fixed pattern, so no raw output can reach
the file. `result.json` and its SHA-256 are kept as a 7-day artifact; there
is no release.

The job's log is public. It shows only the step ids, `ok`/`fail` and the
result. Paperclip's output, npm's output and the API's answers stay in a
temporary folder that is neither printed nor uploaded.

### The recipe, to repeat it elsewhere

```sh
# 1. Node 24.11 or later, then the exact version from its tarball.
npm pack paperclipai@2026.1117.0
npm install --prefix ./pc --no-audit --no-fund ./paperclipai-2026.1117.0.tgz

# 2. Start it with an empty, explicit environment. --yes takes the Quickstart
#    defaults (local_trusted: loopback only, no login, port 3100) and starts
#    the server in the foreground.
mkdir -p ./home
setsid env -i \
  HOME="$PWD/home" \
  PATH="$PWD/pc/node_modules/.bin:$(dirname "$(command -v node)"):/usr/bin:/bin" \
  LANG=C.UTF-8 \
  PAPERCLIP_TELEMETRY_DISABLED=1 \
  DO_NOT_TRACK=1 \
  PAPERCLIP_UPDATE_CHECK=0 \
  paperclipai onboard --yes --no-install-service </dev/null &

# 3. In local_trusted mode, calls from this machine act as the local board,
#    with no login and no key.
curl -s http://127.0.0.1:3100/api/health
```

Three of those variables were not in the plan. They are needed because the
environment is empty:

- **`PAPERCLIP_TELEMETRY_DISABLED=1` and `DO_NOT_TRACK=1`.** Paperclip sends
  anonymous telemetry by default, to `telemetry.paperclip.ing`
  (`packages/shared/src/telemetry/client.ts`). It turns telemetry off by
  itself only when it sees `CI`, `GITHUB_ACTIONS` or a similar variable
  (`packages/shared/src/telemetry/config.ts`), and `env -i` removes those.
  Either variable turns it off by name.
- **`PAPERCLIP_UPDATE_CHECK=0`.** It stops the command line from asking
  `registry.npmjs.org` for a newer version (`cli/src/update-notice.ts`).

One more fact found on the first run (25-11-2026): the `process` adapter runs
`command` with `args` and **no shell** (`spawn` with `shell: false`,
`packages/adapter-utils/src/server-utils.ts`). A `command` of `sleep 600`
looks for a program named «sleep 600» and the run fails at once. The
adapter's page calls `command` a «Shell command to execute» and shows
`"command": "python3 /path/to/agent.py"` (`docs/adapters/process.md`), which
would fail the same way on Linux. The test uses `"command": "sleep",
"args": ["600"]`.

Why the environment is empty: Paperclip gives each agent its own environment,
minus its `PAPERCLIP_*` variables. Its `process` adapter builds the child's
environment from `sanitizeInheritedPaperclipEnv(process.env)`
(`server/src/adapters/process/execute.ts`). Starting it with `env -i` means no
variable of the job can reach an agent.

### Where it connects

No network limit is set in this job: it holds no secret and calls no model.
What it records, with no extra tool:

- **While installing:** the host names in npm's http log (`install_hosts`).
  Only npm's own requests are there; a download made by a package's
  install script would not show.
- **While running:** how many established TCP connections Paperclip's
  `node` and `postgres` processes have to an address that is not this
  machine. It is sampled twice, while the two agents run and after the
  pause. `ss` gives addresses, not names, so these are counts only.

Not yet observed: this section is completed with the first run's
`result.json`.
