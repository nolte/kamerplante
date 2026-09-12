#!/usr/bin/env bash
# Create a git worktree under the configurable portfolio worktree root.
#
# Wired in Taskfile.yml as `task worktree:add -- <branch> [slug]`. It is the
# correct counterpart to the guard-nested-worktree pre-commit hook: that guard
# rejects commits made from a worktree nested under .claude/worktrees/ (where
# the harness materialises isolation worktrees that have no resumable top-level
# transcript), and this helper is the supported way to get a worktree in the
# right place instead.
#
# Guarantees, so every worktree lands in the same predictable place:
#   - <root> comes from NOLTE_WORKTREE_ROOT (default ~/repos/.worktrees)
#   - <repo> is derived from the origin remote, never guessed
#   - the branch is created with an explicit base ref (origin/develop) after a
#     fetch, so the worktree starts from the remote tip and the primary
#     checkout's local develop is irrelevant
set -euo pipefail

usage() {
  cat >&2 <<EOF
Usage: task worktree:add -- <branch> [slug]

  <branch>  Full branch name including its prefix, e.g. feat/parser-fix.
            Allowed prefixes: feat/ fix/ chore/ docs/ exp/ ci/
  [slug]    Optional kebab-case directory name under the worktree root.
            Defaults to the branch name with its prefix stripped.

The worktree is created at:
  \${NOLTE_WORKTREE_ROOT:-~/repos/.worktrees}/<repo>/<slug>/
based on origin/develop. Start a top-level (resumable) session with:
  cd <that path> && claude
EOF
  exit 2
}

branch="${1:-}"
slug="${2:-}"

[ -n "$branch" ] || usage

# Branch-prefix rule — keep in sync with the project's branching convention.
case "$branch" in
  feat/*|fix/*|chore/*|docs/*|exp/*|ci/*) : ;;
  *)
    echo "✖ Branch '$branch' lacks an allowed prefix (feat/ fix/ chore/ docs/ exp/ ci/)." >&2
    echo "  The path slug may drop the prefix, but the branch MUST NOT." >&2
    exit 1
    ;;
esac

# Default slug: branch name minus the prefix segment.
if [ -z "$slug" ]; then
  slug="${branch#*/}"
fi

# A slug MUST be a single path segment — never a traversal or nested path.
case "$slug" in
  */*|*..*|"")
    echo "✖ Slug '$slug' must be a single kebab-case path segment." >&2
    exit 1
    ;;
esac

# Resolve the configurable root. Tilde in the env value is not expanded by the
# shell when it arrives as a variable, so expand a leading ~ ourselves.
root="${NOLTE_WORKTREE_ROOT:-$HOME/repos/.worktrees}"
# shellcheck disable=SC2088 # False positive: "~" and "~/" here are case PATTERNS that
# match a literal tilde arriving inside a variable, not paths meant to expand. Expanding
# them is what the branch bodies do, which is the whole point of this block. The
# directive must sit in front of the entire `case` — shellcheck rejects it on a single
# branch (SC1124) — so it also covers the "~" branch, which reports nothing today.
case "$root" in
  "~") root="$HOME" ;;
  "~/"*) root="$HOME/${root#\~/}" ;;
esac

# Derive <repo> from the origin remote — never inferred from the cwd.
origin_url="$(git remote get-url origin)"
repo="$(basename "$origin_url" .git)"

dest="$root/$repo/$slug"

if [ -e "$dest" ]; then
  echo "✖ Destination already exists: $dest" >&2
  exit 1
fi

echo "→ Worktree root : $root"
echo "→ Repository    : $repo"
echo "→ Branch        : $branch"
echo "→ Destination   : $dest"

git fetch origin develop --quiet
git worktree add -b "$branch" "$dest" origin/develop

# Seed the plan-before-work stub (#1375).
#
# `spec/project/parallel-working-copies/` §"Lifecycle: Plan before work" makes the
# plan a MUST and the stub a SHOULD for exactly this helper: the gate is
# convention-driven, no hook aborts work when the plan is absent, so the only
# thing that makes authoring it the path of least resistance is finding the
# headings already there. Written once, never overwritten; the existence check
# below says exactly what that does and does not cover.
#
# `.resume/` is gitignored, so this is a worktree-local working aid and never
# competes with the branch's real changes for review attention. The
# `no .resume/ artifacts on the branch` pre-commit hook keeps it that way.
#
# The existence check below is a BELT, not a braces: `$dest` is refused above if it
# already exists and `git worktree add` creates it fresh, so the file cannot be
# there on this path today. It stays because the cost is one `[ -e ]` and the
# failure it guards against — overwriting a plan somebody filled in — is the exact
# thing the plan-before-work gate exists to preserve. An earlier version of this
# comment claimed the check covered "a worktree re-entered after a crash"; it does
# not. Re-entry is a `cd`, and never runs this script.
plan_dir="$dest/.resume/$slug"
plan_file="$plan_dir/plan.md"
base_commit="$(git rev-parse --short origin/develop)"

if [ -e "$plan_file" ]; then
  echo "→ Plan          : $plan_file (exists, left untouched)"
else
  mkdir -p "$plan_dir"
  cat > "$plan_file" <<PLAN
# Plan: $branch

- **Worktree**: \`$dest\`
- **Branch**: \`$branch\` (from \`origin/develop\` @ \`$base_commit\`)
- **Created**: $(date -u +%Y-%m-%dT%H:%M:%SZ)

> Seeded by \`scripts/worktree_add.sh\`. **Fill this in before substantive work
> begins** — the sections below are the shape
> \`spec/project/parallel-working-copies/\` §"Lifecycle: Plan before work"
> prescribes, and an unfilled stub is worth no more than an absent plan.

## Goal

<!-- One paragraph: what is true when this branch is done that is not true now. -->

## Current state, researched

<!-- What the code/spec actually does today, MEASURED rather than assumed.
     Name the files and the line numbers you read. If an issue states a cause,
     verify it here before building on it. -->

## Design decision

<!-- The load-bearing choice and why the alternatives lose. -->

### Open questions to confirm before work starts

<!-- Anything whose answer changes the work. Confirm these first; a question
     answered after the fact is a rewrite. -->

## Work steps, ordered

1.

## Invariants and guardrails

<!-- Carried from CLAUDE.md and the governing specs. What must stay true that
     this change could quietly break. -->

## Status / resume anchor

<!-- The first unchecked box is where the next session resumes. -->

- [ ] Plan filled in
- [ ] Work steps drafted
- [ ] Implementation
- [ ] Falsification: the guard/test observed RED against the pre-fix state
- [ ] Full suites green
- [ ] Pull request opened
PLAN
  echo "→ Plan          : $plan_file (stub — fill it in before you start)"
fi

echo
echo "✓ Worktree ready. Start a top-level (resumable) session scoped to it with:"
echo "    cd $dest && claude"
echo
echo "  Before substantive work: fill in .resume/$slug/plan.md"
echo "  (spec/project/parallel-working-copies §Lifecycle: Plan before work)"
