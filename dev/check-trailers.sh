#!/usr/bin/env bash
# Finds tool attribution lines in commit messages; human co-authors are never flagged. Reads
# commit messages from the files given, or from stdin; prints each such line and exits 1 if
# there is one. Opt-in: the commit-msg and pre-push hooks run it only with
# `git config frame-tweaks.refuseToolTrailers true` (for people who don't want them in their own
# commits; other contributors' commits may carry them).
#
#   Always refused:  Claude-Session: / Assisted-by: / Generated-by: lines, "Generated with [...]"
#   Refused when it names an AI tool or bot:  Co-authored-by: (Claude, Anthropic, Copilot,
#                    ChatGPT, OpenAI, Gemini, Codex, Cursor, Aider, any [bot] account)
# Anchored to the line start, so prose that merely discusses a trailer is fine.
set -euo pipefail
always='^[[:space:]]*((Claude-Session|Assisted-by|Generated-by)[[:space:]]*:|(🤖[[:space:]]*)?Generated with \[)'
coauthor='^[[:space:]]*Co-authored-by[[:space:]]*:'
ai='claude|anthropic|copilot|chatgpt|openai|gemini|codex|cursor(agent| agent|@)|aider|\[bot\]|-bot@|noreply@(anthropic|openai)'
bad=$(cat "$@" | grep -iE "$always|$coauthor" | grep -iE "$always|$ai" || true)
if [ -n "$bad" ]; then
    printf '%s\n' "$bad" | sed 's/^/  refused: /' >&2
    exit 1
fi
