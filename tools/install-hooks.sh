#!/bin/bash
# Point git at the repo's hooks (per-clone setting, so run it once after cloning).
set -euo pipefail
cd "$(dirname "$0")/.."
git config core.hooksPath tools/git-hooks
echo "hooks enabled: core.hooksPath=tools/git-hooks"
