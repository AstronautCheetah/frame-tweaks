#!/usr/bin/env bash
# Keep one GitHub issue in step with a report (dev/check-upstream.sh's, for
# .github/workflows/upstream.yml; dev/check-links.py's, for linked.yml): opened when the report
# lists anything, its text replaced (and a comment added, so watchers are notified) only when the
# report changes, closed when all clear.
#   dev/upstream-issue.sh REPORT.md [LABEL TITLE ABOUT]    (needs gh, authenticated; GH_REPO in CI)
set -euo pipefail
report=$1
label=${2:-upstream-check}
title=${3:-"Upstream check: outside changes to look at"}
about=${4:-"Weekly dev/check-upstream.sh"}
# (an empty report means dev/check-upstream.sh broke: fail the run rather than empty the issue)
[ -s "$report" ] || { echo "upstream-issue: $report is empty; did dev/check-upstream.sh fail?" >&2; exit 1; }
gh label create "$label" --color FBCA04 --description "$about" --force >/dev/null
num=$(gh issue list --label "$label" --state open --json number --jq '.[0].number // empty')
# (the first line is the date; compare the rest)
body() { tail -n +2 "$1"; }
if grep -q '^All clear' "$report"; then
    [ -z "$num" ] || gh issue close "$num" --comment "All clear now: $(head -1 "$report")"
    exit 0
fi
if [ -z "$num" ]; then
    gh issue create --title "$title" --label "$label" --body-file "$report"
    exit 0
fi
old=$(mktemp); trap 'rm -f "$old"' EXIT
gh issue view "$num" --json body --jq .body > "$old"
if [ "$(body "$old")" != "$(body "$report")" ]; then
    gh issue edit "$num" --body-file "$report"
    gh issue comment "$num" --body "The report changed: see the issue text. ($(head -1 "$report"))"
fi
