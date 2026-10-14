---
title: Homebrew
emoji: 🍺
category: System
tier: helper
summary: The package manager several tweaks install their programs with
what: >-
  Homebrew, a package manager for command-line programs. It installs everything into
  `/home/linuxbrew`.
why: >-
  SteamOS's system partition is read-only and wiped by updates, so programs installed there
  don't last. Homebrew installs outside it, and several tweaks use it for that reason.
author: Homebrew project
source: {relation: uses, url: https://brew.sh}
icon: {theme: package-x-generic}
changes: "`/home/linuxbrew`; one line in `~/.bashrc` so terminals find `brew`"
access: "**Needs your sudo password once**, to create `/home/linuxbrew`"
survives_updates: Yes (it lives in /home/linuxbrew)
undo: >-
  Not removed automatically, because other tweaks' programs live in it; `./install.sh uninstall
  homebrew` prints Homebrew's own uninstaller
test: {offline: true}
---
# Homebrew

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Homebrew, a package manager for command-line programs. It installs everything into `/home/linuxbrew`.

**Why on a Steam Frame:** SteamOS's system partition is read-only and wiped by updates, so programs installed there don't last. Homebrew installs outside it, and several tweaks use it for that reason.
<!-- /generated:intro -->

## Install
Tick it in the Frame Tweaks window, or:

```sh
./install.sh install homebrew
```

You don't have to install it yourself: tweaks that need it offer to install it when it's
missing. This row lets you see it and install it up front.

**It needs your sudo (admin) password once.** Homebrew's installer uses it to create
`/home/linuxbrew`. If your user has no password yet, the install stops and asks you to set one:
run `passwd` in a terminal, then try again. Frame Tweaks never asks for sudo for Homebrew after
that, and installing or updating programs with `brew` doesn't need it.

## Use
In a terminal (open a new one after installing):

```sh
brew install <program>      # anything from https://formulae.brew.sh
brew upgrade                # update everything it installed
```

**Used by:** [Dictation](../dictation/) (wl-clipboard and whisper.cpp),
[Android Mirror](../adb-scrcpy/) (scrcpy) and [Screen snip + Narrate](../snip/) (Tesseract, for reading
text in screenshots).

## How it works
Frame Tweaks downloads Homebrew's official installer at a fixed, reviewed version and checks
its SHA-256 checksum before running it. It then adds Homebrew's setup line to `~/.bashrc`, so
new terminals find `brew` and the programs it installs.

## Good to know
- Removing this row leaves Homebrew in place, because other tweaks' programs (and anything you
  installed with `brew`) live in it. It prints Homebrew's own uninstaller command if you really
  want it gone; that removes everything Homebrew installed.
- The status line shows Homebrew's version and how many packages it has installed.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (it lives in /home/linuxbrew)
- **Changes:** `/home/linuxbrew`; one line in `~/.bashrc` so terminals find `brew`
- **Unusual access:** **Needs your sudo password once**, to create `/home/linuxbrew`
- **Undo:** Not removed automatically, because other tweaks' programs live in it; `./install.sh uninstall homebrew` prints Homebrew's own uninstaller
<!-- /generated:changes -->

## Credits
[Homebrew](https://github.com/Homebrew/brew) (BSD-2-Clause), installed with its official
installer ([Homebrew/install](https://github.com/Homebrew/install), BSD-2-Clause). See also
[CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status homebrew` · Remove: `./install.sh uninstall homebrew`
