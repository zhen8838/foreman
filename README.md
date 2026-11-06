# foreman

**A workflow for handing work out.** You settle a plan in your main worktree, `foreman` sends
it into a git worktree of its own, agents work there until a PR exists, and you review and
merge.

Your main worktree is never touched by anyone else, several jobs run genuinely in parallel,
and each one keeps its progress, its conversation and its diff in its own window. Underneath
is [herdr-core](https://github.com/herdrdev/herdr-core) (`hc`): one terminal per agent, and
[herdr-app](https://github.com/herdrdev/herdr-app) shows each job as a space of its own.

```mermaid
flowchart LR
    subgraph MAIN["main worktree —— where you talk"]
        direction TB
        YOU["you"] <--> PL["Planner<br/>(one session or several)"]
    end

    subgraph SOLO["new worktree · solo"]
        A["agent<br/>write → test → commit"]
    end

    subgraph PAIR["new worktree · pair —— one tab, split impl | review"]
        direction TB
        IM["impl<br/>the only one writing"] -- "milestone done,<br/>asks for the gate" --> RV["review<br/>read-only, holds the gate"]
        RV -- "PASS / numbered findings" --> IM
    end

    PL -- "assign solo" --> A
    PL -- "assign pair" --> IM

    PL -. "status / say<br/>look in, cut in" .-> A
    PL -. "status / say" .-> IM

    A -- "opens a PR" --> PR
    IM -- "after the last PASS" --> PR

    PR["PR<br/>you review, you merge"]

    classDef human fill:#FFE0B2,stroke:#E65100,stroke-width:2px,color:#1A1A1A
    classDef agent fill:#D6E4FF,stroke:#2952CC,stroke-width:1.5px,color:#1A1A1A
    classDef artifact fill:#F0F0F0,stroke:#757575,stroke-width:1.5px,color:#1A1A1A
    class YOU human
    class PL,A,IM,RV agent
    class PR artifact
```

Two modes:

- **solo** — one agent, start to finish. Small, unambiguous work.
- **pair** — two agents in one worktree: `impl` writes, `review` is **read-only and holds the
  gate**. impl stops at each milestone to ask for the gate and continues only on PASS; no PR
  before the last one. Anything needing a human call — scope, public contracts, design
  trade-offs — neither settles alone; review raises it with you.

## Install

```bash
git clone <this repo> ~/src/foreman && cd ~/src/foreman && ./install.sh
```

Symlinks `bin/foreman` into `~/.local/bin` and `skill/` into every agent framework you have
(`~/.claude/skills` and `~/.codex/skills` share one SKILL.md), then seeds `local/` from
`examples/`. Idempotent.

Needs `python3 >= 3.11` and `hc` (herdr-core) on the machine that holds the checkouts; `gh` is
optional (the PR/CI column of `status` uses it).

## Setup

**All real config lives in `local/`, which is gitignored** — editing it never produces a dirty
diff and never fights `git pull`. `install.sh` seeds an annotated copy the first time; edit
that:

```
foreman/
├─ bin/foreman
├─ install.sh
├─ templates/                      the shipped prompts: solo · pair-impl · pair-review
├─ examples/                       annotated samples; whatever local/ lacks is seeded from here
│
├─ local/                          ★ the only layer you touch
│  ├─ foreman.toml                 which agent each mode defaults to: kind / model / effort / tier
│  ├─ <project>.toml               where main is, where new worktrees go, per-role notes, hook.
│  │                               One per project; add more and you can dispatch more projects
│  ├─ <project>-post-worktree.sh   optional: runs after the worktree exists, cwd inside it
│  ├─ <project>-worker-env.sh      optional: sourced before every Agent Session and restart
│  ├─ <project>-pre-done.sh        optional: preserves artifacts and releases project resources
│  └─ templates/                   (optional) override the shipped prompts, see Prompts below
│
└─ state/jobs/<task>.json          one ledger per job, written by foreman; ignore it
```

`git worktree add` brings no submodules, no `.venv`, no untracked local files — restoring
those **is written only in that hook script** (a non-zero exit aborts the dispatch). It is
also the thing to run when you create a worktree by hand, which is why the steps should not be
repeated in your project docs.

Use `[hooks].source_env` for exports and a `cd` that must be inherited by the agent. Each role
runs a launch script that Foreman writes to `state/jobs/<task>/`: it sources the hook, then
`exec`s the agent in the same shell, and `foreman restart` runs it again. It receives
`FOREMAN_PROMPT`, `FOREMAN_PLAN` and a
`FOREMAN_AGENT_ARGS_FILE` path in addition to the normal worktree fields. A hook may write a
JSON array of strings to that file; Foreman appends those arguments to this agent's launch
command. This is intended for runtime values discovered by the hook, such as a container's
dynamic SSH endpoint. Set `source_env_timeout_ms` when setup can legitimately take longer than
the default 60 seconds. Hook failure is reported immediately with the terminal's last output.

Use `[hooks].pre_done` for project-specific finish work. `foreman done` first stops the agents
so their sessions are flushed, then runs this hook while their terminals (stopped, still
readable), worktree and ledger still exist. It receives `FOREMAN_REMOVE_WORKTREE=1` for `done --rm` and a JSON description of the
roles in `FOREMAN_AGENTS_JSON`. Archive transcripts, move durable artifacts and remove
containers here. A non-zero exit stops teardown; Foreman keeps the terminals, worktree and
ledger so the finish step can be fixed and retried.

`solo_notes`, `impl_notes` and `review_notes` in `<project>.toml` are free text and go into
that role's opening prompt verbatim — point at the project's own rules file (**point, don't
copy**) and add the commands that file doesn't already give you. One key per role and no
shared fallback, so review can be told something impl isn't; a key you leave out means that
role gets no notes and its heading disappears.

## Usage

```bash
foreman assign pair --plan docs/plans/13-installed-surface-smoke.md
foreman assign solo --prompt "replace X with Y" --task chore-xy

# Pi can use either provider without changing the mode default:
foreman assign solo --prompt "replace X with Y" --task chore-xy \
  --kind pi --model anthropic/<claude-model-id> --effort xhigh
foreman assign solo --prompt "replace X with Y" --task chore-xy \
  --kind pi --model openai-codex/<gpt-model-id> --effort xhigh

foreman assign pair --plan <file> --dry-run    # see what it would do, and the exact prompts
```

`--kind pi` is a per-dispatch override; it does not change `[modes.solo.agent]`.
Pi accepts `provider/model` through Foreman's existing `--model` option, so Claude and GPT
selection stays explicit. Omit `--model` to let Pi use its own saved provider/model.

Pick the mode first, then that mode's flags (`solo` never shows `--review-*`). The work itself
is `--plan <file>` or `--prompt "one sentence"`. It reports each agent's name and address when
it's done.

The remaining four are self-explanatory under `foreman --help`: `say` (message an agent),
`status` (who is paired with whom, PR and CI), `restart` (restart one role in place), `done`
(wrap up).

## Where the agents are

Every agent runs in an `hc` terminal of its own, named `<task>` (solo) or `<task>-impl` /
`<task>-rev` (pair). That name is the address to use everywhere — `foreman say`, `hc read`,
`hc attach` (leave with Ctrl+\\) — because Foreman sets it and the agent cannot change it.
The `t1b`-style address changes when `foreman restart` replaces the terminal.

herdr-app shows a terminal only when it carries `herdr.space` / `herdr.tab` labels
([herdr-app #290](https://github.com/herdrdev/herdr-app/issues/290)), so Foreman gives each job
a new space id and a new tab id. The space is named after the worktree folder. Terminals that
share a tab are split side by side in the order herdr-app adopts them, so a pair shows impl on
the left and review on the right. `foreman restart` starts a new terminal, and herdr-app adds it
on the right: after `restart impl`, impl is on the right. Labels cannot place a pane yet
([herdr-app #313](https://github.com/herdrdev/herdr-app/issues/313)), and herdr-app reads them
only once, so changing the labels of a shown terminal does not move it. `foreman done` removes
the terminals, and herdr-app drops the space with them.

Terminals are started with `--no-parent`: a job outlives the session that dispatched it, and
the dispatcher's input is not filled with a note for every turn the agents finish.

`[kinds.*]` in `local/foreman.toml` says how to start each agent (`command`, `args`, the flag
templates) and how to accept its folder-trust dialog (`trust_prompt`, `trust_keys`). Agents
draw that dialog without reporting a status, so Foreman can only find it on screen.

For an end-to-end test on config and ledgers of its own, point `FOREMAN_LOCAL` at another
`local/` and `FOREMAN_STATE` at another `state/`.

## Prompts — changing what an agent is told

Everything a dispatched agent knows arrives in one opening prompt, rendered from a template.
Four of them:

```
templates/solo.md            the lone agent
templates/pair-impl.md       "you are impl"
templates/pair-review.md     "you are review"
templates/pair-protocol.md   the gate loop — spliced into both pair roles, so it can't drift
```

The role templates are short and say only **who you are**; the protocol holds **how the two of
you work together**. Rendered, a prompt reads: identity (your name and your partner's) → the
task → `## Role` → `## Collaboration` → `## Notes`. The last one is the free text from your
project toml — `{solo_notes}`, `{impl_notes}` or `{review_notes}`, one per template, so the
three can be overridden apart; leave one empty and its heading disappears.

To change any of it, drop an edited copy into a layer that outranks the shipped one:

```
local/templates/<project>/pair-impl.md    this project only
local/templates/pair-impl.md              this machine
templates/pair-impl.md                    shipped default
```

So `cp templates/pair-protocol.md local/templates/` and edit is how you rewrite the gate
protocol for every project on this machine. `--dry-run` prints which file it ended up using,
and the full rendered prompt.
