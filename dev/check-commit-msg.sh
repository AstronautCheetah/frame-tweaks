#!/usr/bin/env bash
# Checks that a commit message follows Conventional Commits (.cz.toml; CONTRIBUTING.md, "Commit
# style"): with commitizen's `cz check` when it's installed, otherwise with the same pattern.
# Used by the commit-msg hook and CI.
#   dev/check-commit-msg.sh FILE          one message
#   dev/check-commit-msg.sh --all [REF]   every commit reachable from REF (default HEAD)
set -euo pipefail
root=$(git rev-parse --show-toplevel)
# commitizen's cz_conventional_commits pattern, and the prefixes it lets through unchecked.
pattern='^(build|ci|docs|feat|fix|perf|refactor|style|test|chore|revert|bump)(\([^)[:space:]]+\))?!?: [^[:space:]]'
allowed='^(Merge|Revert|Pull request|fixup!|squash!|amend!)'
check_file() {
    if command -v cz >/dev/null; then
        (cd "$root" && cz check --commit-msg-file "$1" >/dev/null 2>&1) && return 0
    else
        local subject; subject=$(grep -v '^#' "$1" | sed -n 1p)
        [[ $subject =~ $pattern || $subject =~ $allowed ]] && return 0
    fi
    echo "  not a Conventional Commit: $(grep -v '^#' "$1" | sed -n 1p)" >&2
    return 1
}
if [ "${1:-}" = --all ]; then
    tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT; bad=0
    for c in $(git rev-list "${2:-HEAD}"); do
        git log -1 --format=%B "$c" > "$tmp"
        check_file "$tmp" || { echo "    in commit ${c:0:7}" >&2; bad=1; }
    done
    exit "$bad"
fi
check_file "${1:?usage: dev/check-commit-msg.sh FILE | --all [REF]}"
