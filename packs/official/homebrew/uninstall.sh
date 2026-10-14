#!/bin/bash
# Homebrew isn't removed automatically: other tweaks' programs live in it.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
cat <<MSG
Homebrew was left installed: Dictation (wl-clipboard, whisper.cpp), Android Mirror (scrcpy),
Screen snip (tesseract) and anything you installed yourself live in it.
To remove it and everything in it, use Homebrew's own uninstaller:
  /bin/bash -c "\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/uninstall.sh)"
MSG
