#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
exec "$REPO_DIR/firefox/install.sh" --remove
