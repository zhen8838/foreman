#!/usr/bin/env bash
# Install foreman: symlink bin and skill out, seed local/ from examples/ the first time.
# Idempotent — run it as often as you like.
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BIN=${FOREMAN_BIN_DIR:-$HOME/.local/bin}
# One SKILL.md, symlinked into every agent framework present. claude and codex read the same
# frontmatter (name + description), so one copy serves both. Frameworks not installed are skipped.
SKILL_DIRS=${FOREMAN_SKILL_DIRS:-"$HOME/.claude/skills $HOME/.codex/skills"}

mkdir -p "$BIN" "$REPO/local" "$REPO/state/jobs"

ln -sfn "$REPO/bin/foreman" "$BIN/foreman"
echo "link  $BIN/foreman  -> $REPO/bin/foreman"

for skills in $SKILL_DIRS; do
  [[ -d $(dirname "$skills") ]] || { echo "skip  $skills (framework not installed)"; continue; }
  mkdir -p "$skills"
  ln -sfn "$REPO/skill" "$skills/foreman"
  echo "link  $skills/foreman  -> $REPO/skill"
done

# Seed only what local/ is missing; anything already there is left untouched
if [[ ! -f $REPO/local/foreman.toml ]]; then
  cp "$REPO/examples/foreman.toml" "$REPO/local/foreman.toml"
  echo "seed  local/foreman.toml (edit this one for mode defaults; leave examples/ alone)"
fi
if ! compgen -G "$REPO/local/*.toml" >/dev/null || \
   [[ $(find "$REPO/local" -maxdepth 1 -name '*.toml' ! -name foreman.toml | wc -l) -eq 0 ]]; then
  cp "$REPO/examples/project.toml" "$REPO/local/myproject.toml"
  echo "seed  local/myproject.toml (make it yours: main / worktree_root / rules / hook)"
fi

chmod +x "$REPO/bin/foreman" "$REPO"/local/*.sh 2>/dev/null || true

# Self-check
echo
python3 -c 'import tomllib, sys; assert sys.version_info >= (3, 11)' \
  && echo "ok    python3 $(python3 -V | cut -d' ' -f2) + tomllib"
command -v herdr >/dev/null && echo "ok    herdr $(herdr --version 2>/dev/null | head -1)" \
  || echo "miss  herdr — foreman builds worktrees and starts agents entirely through it"
command -v gh >/dev/null && echo "ok    gh (status needs it for the PR/CI column)" \
  || echo "note  no gh, so the PR column of foreman status stays empty"
"$BIN/foreman" --version

case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo; echo "note  $BIN is not on PATH — add it";;
esac
