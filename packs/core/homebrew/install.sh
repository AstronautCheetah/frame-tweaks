#!/bin/bash
# Homebrew, the package manager several tweaks install their programs with.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
need_brew
say "$(t '%s is ready: %s' "$(brew --version | sed -n 1p)" "$(brew --prefix)")"
