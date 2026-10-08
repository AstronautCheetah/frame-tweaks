#!/bin/bash
# Homebrew, the package manager several tweaks install their programs with.
source "$(dirname "$0")/../lib/common.sh"
need_brew
say "$(brew --version | sed -n 1p) is ready: $(brew --prefix)"
