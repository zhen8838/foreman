---
name: foreman
description: Hand a settled plan, or a loose piece of work, to agents in their own worktree — one agent for small tasks (solo), two collaborating for anything medium or larger (pair: one writes, one gates read-only). Use when the user says "dispatch this", "send it out", "have an agent do this plan", or "/foreman <plan.md>".
---

# foreman

The main session is the **planner**: it settles a plan with the user in the main worktree.
Once settled, the work goes to agents in other worktrees — that is all this skill does.

## Usage

```
/foreman <plan.md> [solo|pair] [codex|claude] [effort]
/foreman "one sentence saying what to do" [solo|pair]
```

becomes one command:

```bash
foreman assign <solo|pair> (--plan <file> | --prompt "one sentence") \
               [--task N] [--branch B] [--kind K] [--model M] [--effort E] [--tier T] \
               [--review-kind K] [--review-effort E]     # --review-* exists only under pair
```

- **Mode** is a subcommand and is required. When the user didn't say: `pair` for a plan,
  `solo` for a one-line job.
- **The work**: `--plan` for a plan file, `--prompt` for a sentence (which then requires
  `--task`).
- **`--branch`** defaults to the task name. If the repo has a branch-naming convention — say
  `feat/` `fix/` `test/` `docs/` `refactor/` keyed off the plan's `type:` frontmatter —
  **read the plan and compose one yourself**. That is your judgment to make, not config.
- **Kind and effort**: pass nothing unless the user asked, and let the mode defaults in
  `local/foreman.toml` apply.
- Unsure what a dispatch will do? `--dry-run` prints every herdr command and the **fully
  rendered prompts**, and executes nothing.

Report the handles and `herdr agent attach <handle>` back to the user.

## The other commands

```bash
foreman status [<task>]         # who is paired with whom, doing what, dirty count, PR and CI
foreman restart <task>[.rev]    # restart one role in place, same model and permissions
foreman done <task> [--rm]      # wrap up; without --rm only the panes close, the work stays
```

## Messages don't go through you

When the user wants to talk to a dispatched agent, they do it directly:

```bash
foreman say w2E:p2 "..."        # collapsed to one line, waits for them, refuses a huge body
foreman say <task>.rev "..."    # convenience form, same thing
herdr agent read w2E:p2         # watch its screen
herdr agent attach w2E:p2       # take it over (leave with C-c twice)
```

**Always address by pane id (`space:pane`)**, taken from `foreman status`. Agent frameworks
rewrite window titles to the current task, and several worktrees of one repo end up sharing a
title — addressing by name is guaranteed to misdeliver eventually.

Don't relay. Hand the command to the user.

## What you don't do

Once dispatched, the work belongs to **the agent**, not to you:

- no computing file overlap, no ordering dependencies, no deciding who waits for whom — that
  is human judgment;
- no writing back to a dispatch ledger like `INDEX.md` (only if asked);
- no picking the approach for an agent, no pre-slicing milestones, no reading the code for it;
- no watching CI, no editing its PR — whoever was dispatched sees it through to mergeable.

**If you are yourself a dispatched agent (impl / review), do not dispatch further.** Your work
is the plan in front of you.

When several go out at once, **the user decides the order**. Say so if you see a risk, then do
as asked — don't block it on your own.

## What pair is

Two agents in one worktree: **impl** (`<task>-impl`, the only one that writes files and opens
the PR) and **review** (`<task>-rev`, read-only, holding the gate). impl stops at each
milestone to ask for the gate and continues only on PASS; no PR before the last PASS. Neither
settles anything that needs a human — review is the only interface to one.

**The protocol itself is in `templates/pair-protocol.md`; it is not repeated here.** To change
it, change the template (`cp templates/pair-protocol.md local/templates/`, or put it under
`local/templates/<project>/` to affect one project), **not the prompt at dispatch time**.
