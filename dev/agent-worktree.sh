#!/usr/bin/env bash
# A separate git worktree for each piece of work done in parallel. No branches: each worktree is a
# detached checkout of origin/main, and its commits are published straight to main with
# dev/safe-push.sh. Two sessions in one working tree can sweep each other's work into the
# wrong commit (`git add`); separate worktrees remove the shared index entirely.
#
#   dev/agent-worktree.sh add <slug>       # create tmp/<slug> from origin/main
#   dev/agent-worktree.sh remove <slug>    # remove it (refuses if it has unpushed work)
#   dev/agent-worktree.sh list
#   dev/agent-worktree.sh prune [--apply]  # reap clean worktrees whose work is on origin/main
#
# Worktrees live in <repo>/tmp/<slug>, kept out of `git status` by .git/info/exclude.
# NEVER mv or rm -rf a worktree by hand: use `remove`. (Maintainers: one worktree per parallel session.)
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
ROOT="$REPO_ROOT/tmp"
cmd="${1:-}" slug="${2:-}"

usage() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; }

unpushed() {   # unpushed <path>: commits there that origin/main doesn't have (by content)
    git -C "$1" cherry origin/main HEAD 2>/dev/null | grep -c '^+' || true
}

nested() {     # nested <path>: worktrees made inside it (its tmp/), which removing it would delete
    git worktree list --porcelain | sed -n 's/^worktree //p' | grep -cF "$1/" || true
}

case "$cmd" in
add)
    [ -n "$slug" ] || { usage; exit 1; }
    path="$ROOT/$slug"
    mkdir -p "$ROOT"
    if ! git check-ignore -q "tmp/.probe" 2>/dev/null; then
        exclude="$(git rev-parse --git-common-dir)/info/exclude"
        mkdir -p "$(dirname "$exclude")"
        printf '\n# agent worktrees (dev/agent-worktree.sh), local only\n/tmp/\n' >> "$exclude"
    fi
    # A worktree removed by hand leaves an orphaned admin dir; reusing its slug would hand out a
    # stale index, so committing an untouched file would silently revert upstream work.
    git worktree prune
    if [ -e "$(git rev-parse --git-common-dir)/worktrees/$slug" ]; then
        echo "agent-worktree: .git/worktrees/$slug already exists (a live or unpruned worktree)." >&2
        echo "  Inspect with 'git worktree list'; if it's defunct: $0 remove $slug" >&2
        exit 1
    fi
    git fetch -q origin main || true
    base=main
    git rev-parse -q --verify origin/main >/dev/null && base=origin/main
    git worktree add -q --detach "$path" "$base"
    # Clean at birth, or it's a stale checkout: tear it down rather than hand it out.
    dirty="$(git -C "$path" status --porcelain)"
    if [ -n "$dirty" ]; then
        echo "agent-worktree: FATAL: fresh worktree $path is not clean (stale checkout):" >&2
        echo "$dirty" | sed 's/^/    /' >&2
        git worktree remove --force "$path"
        exit 1
    fi
    echo "worktree ready: $path (detached at $base, verified clean)"
    echo "work and commit there; publish with dev/safe-push.sh; then: $0 remove $slug"
    ;;
remove)
    [ -n "$slug" ] || { usage; exit 1; }
    path="$ROOT/$slug"
    git fetch -q origin main || true
    if [ -n "$(git -C "$path" status --porcelain 2>/dev/null)" ]; then
        echo "agent-worktree: $path has uncommitted changes; commit or discard them first." >&2
        exit 1
    fi
    n=$(unpushed "$path")
    if [ "${n:-0}" -gt 0 ]; then
        echo "agent-worktree: $path has $n unpushed commit(s); a detached worktree's commits are" >&2
        echo "  lost when it's removed. Publish with dev/safe-push.sh first." >&2
        exit 1
    fi
    n=$(nested "$path")
    if [ "${n:-0}" -gt 0 ]; then
        echo "agent-worktree: $path holds $n other worktree(s); removing it would delete them, and" >&2
        echo "  their uncommitted work. Remove those first (see: $0 list)." >&2
        exit 1
    fi
    git worktree remove --force "$path"
    echo "worktree removed: $path"
    ;;
list)
    git worktree list
    ;;
prune)
    apply=0; [ "$slug" = --apply ] && apply=1
    git fetch -q origin main 2>/dev/null || true
    git worktree list --porcelain | awk '/^worktree /{print $2}' | while read -r wt; do
        case "$wt" in "$ROOT"/*) ;; *) continue ;; esac
        if [ -n "$(git -C "$wt" status --porcelain 2>/dev/null)" ]; then
            echo "keep:   $wt (uncommitted changes)"
        elif [ "$(unpushed "$wt")" -gt 0 ]; then
            echo "keep:   $wt (unpushed commits)"
        elif [ "$(nested "$wt")" -gt 0 ]; then
            echo "keep:   $wt (other worktrees inside it)"
        elif [ "$apply" = 1 ]; then
            git worktree remove --force "$wt" && echo "pruned: $wt"
        else
            echo "prune:  $wt (clean, on origin; 'prune --apply' removes it)"
        fi
    done
    ;;
*)
    usage; exit 1 ;;
esac
