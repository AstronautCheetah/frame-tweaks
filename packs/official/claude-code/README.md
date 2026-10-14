---
title: Claude Code (command line)
emoji: 🤖
category: Developer
tier: extras
summary: >-
  Anthropic's coding agent for the terminal (`claude`), installed into your home folder
what: >-
  Claude Code, Anthropic's coding agent for the terminal (`claude`), installed with Anthropic's
  own installer.
why: >-
  Anthropic's installer needs no admin rights and supports the Frame's ARM processor, and it puts
  everything in your home folder, so SteamOS updates leave it alone.
author: Anthropic
source: {relation: from, url: https://code.claude.com/docs/en/setup}
icon: {theme: utilities-terminal}
run: {label: Open}
changes: "`~/.local/bin/claude` and `~/.local/share/claude` (Anthropic's installer)"
access: Downloads and runs Anthropic's installer (`https://claude.ai/install.sh`) over HTTPS
survives_updates: Yes (everything is in your home folder)
undo: >-
  `./install.sh uninstall claude-code` (keeps your login and settings in `~/.claude` and
  `~/.claude.json`)
---
# Claude Code (command line)

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Claude Code, Anthropic's coding agent for the terminal (`claude`), installed with Anthropic's own installer.

**Why on a Steam Frame:** Anthropic's installer needs no admin rights and supports the Frame's ARM processor, and it puts everything in your home folder, so SteamOS updates leave it alone.
<!-- /generated:intro -->

## Install

Tick it in the Frame Tweaks window, or:

```sh
./install.sh install claude-code
```

This downloads [Anthropic's installer](https://code.claude.com/docs/en/setup) and runs it. It
installs `claude` into `~/.local/bin`, which Frame Tweaks adds to your PATH. If `claude` is
already installed another way (for example with Homebrew), it's left as it is.

## Use

Open a terminal (Konsole) and run:

```sh
claude
```

The first time, it asks you to log in with your Claude account in a browser. Claude Code works on
the files in the folder you start it in: it can read and edit them and run commands there. By
default, it asks for your permission first.

**▶ Open** in the Frame Tweaks window starts it in a new Konsole window, in your home folder.
When you quit Claude Code, that window stays open with a normal shell.

## Good to know

- Claude Code installed this way keeps itself up to date (Anthropic's installer sets that up).
- Uninstalling removes the program but keeps your login and settings. If you installed it with
  Homebrew instead, uninstalling this tweak tells you the `brew` command to remove it.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `~/.local/bin/claude` and `~/.local/share/claude` (Anthropic's installer)
- **Unusual access:** Downloads and runs Anthropic's installer (`https://claude.ai/install.sh`) over HTTPS
- **Undo:** `./install.sh uninstall claude-code` (keeps your login and settings in `~/.claude` and `~/.claude.json`)
<!-- /generated:changes -->

## Credits
[Claude Code](https://www.anthropic.com/claude-code) is made by Anthropic. This tweak only runs
Anthropic's installer. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status claude-code` · Remove: `./install.sh uninstall claude-code`
