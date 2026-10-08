#!/usr/bin/env bash
# Publish the current checkout's commits to main, safely, when other sessions may be pushing.
#  1. HEAD fast-forwards origin/main: push it.
#  2. Diverged: replay only the commits origin/main doesn't have onto it, in a throwaway
#     worktree, push that, verify origin advanced to it BEFORE tearing anything down, then
#     move this checkout onto it (only when clean). A replay conflict stops and leaves the
#     throwaway worktree for manual resolution.
# Never force-pushes. Don't chain it after a rebase in one command (see CLAUDE.md).
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
git fetch -q origin main
head=$(git rev-parse HEAD)
remote=$(git rev-parse origin/main)

if [ "$head" = "$remote" ]; then
    echo "safe-push: nothing to push (HEAD is origin/main)."
    exit 0
fi
if git merge-base --is-ancestor "$remote" "$head"; then
    git push origin "$head:refs/heads/main"
    exit 0
fi

mapfile -t new < <(git cherry origin/main HEAD | sed -n 's/^+ //p')
if [ "${#new[@]}" -eq 0 ]; then
    echo "safe-push: all of HEAD's commits are already on origin/main; nothing to push."
    exit 0
fi
replay="$REPO_ROOT/tmp/safe-push-$$"
git worktree add -q --detach "$replay" origin/main
for c in "${new[@]}"; do
    if ! git -C "$replay" cherry-pick "$c" >/dev/null; then
        echo "safe-push: conflict replaying $(git log -1 --format='%h %s' "$c")." >&2
        echo "  Resolve in $replay (git cherry-pick --continue), push from there, then remove it." >&2
        exit 1
    fi
done
tip=$(git -C "$replay" rev-parse HEAD)
git -C "$replay" push origin "$tip:refs/heads/main"
git fetch -q origin main
if [ "$(git rev-parse origin/main)" != "$tip" ]; then
    echo "safe-push: origin/main isn't at the replayed commit $tip; leaving $replay for inspection." >&2
    exit 1
fi
git worktree remove --force "$replay"
if [ -z "$(git status --porcelain)" ]; then
    if git symbolic-ref -q HEAD >/dev/null; then git reset -q --hard "$tip"; else git checkout -q --detach "$tip"; fi
    echo "safe-push: published ${#new[@]} commit(s) as $(git rev-parse --short "$tip"); this checkout is now there."
else
    echo "safe-push: published ${#new[@]} commit(s) as $(git rev-parse --short "$tip")."
    echo "  This checkout has uncommitted changes, so it wasn't moved; update it once they're committed."
fi
