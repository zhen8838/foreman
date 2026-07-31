#!/usr/bin/env bash
# What a post_worktree hook looks like. The cwd is already the new worktree; a non-zero exit
# aborts the dispatch.
#
# Receives: FOREMAN_WORKTREE  FOREMAN_MAIN  FOREMAN_TASK  FOREMAN_BRANCH  FOREMAN_MODE
#
# git worktree add brings tracked files and nothing else — submodules, venvs and untracked
# local config are all yours to restore.
set -euo pipefail

# 1. Borrow the heavy things from the main worktree instead of cloning or downloading again
# ln -sfn "$FOREMAN_MAIN/third_party/big-headers" third_party/big-headers

# 2. Untracked files every worktree needs: symlink, so there stays one source
# ln -sfn "$FOREMAN_MAIN/CONTRIBUTING.local.md" CONTRIBUTING.local.md

# 3. This worktree's own environment (idempotent: already there means skip, so restart and a
#    repeated assign don't reinstall)
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -e '.[test,dev]'
fi

# 4. Self-check — fail here if the install went sideways, not after an agent has started
.venv/bin/python -c "import myproject; print('editable ->', myproject.__file__)"
