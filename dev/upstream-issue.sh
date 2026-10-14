#!/usr/bin/env bash
# Keep one GitHub issue (label "upstream-check") in step with dev/check-upstream.sh's report, for
# .github/workflows/upstream.yml: opened when the report lists anything, its text replaced (and a
# comment added, so watchers are notified) only when the report changes, closed when all clear.
#   dev/upstream-issue.sh REPORT.md       (needs gh, authenticated; GH_REPO set in CI)
set -euo pipefail
report=$1
# (an empty report means dev/check-upstream.sh broke: fail the run rather than empty the issue)
[ -s "$report" ] || { echo "upstream-issue: $report is empty; did dev/check-upstream.sh fail?" >&2; exit 1; }
label=upstream-check
title="Upstream check: outside changes to look at"
gh label create "$label" --color FBCA04 --description "Weekly dev/check-upstream.sh" --force >/dev/null
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
