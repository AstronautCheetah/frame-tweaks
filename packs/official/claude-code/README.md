---
title: Claude Code (command line)
emoji: 🤖
category: Developer
tier: extras
summary: >-
  Anthropic's coding agent in the terminal (claude), installed into your home folder
what: >-
  Anthropic's coding agent in the terminal (`claude`), via Anthropic's own installer.
why: >-
  The native installer runs without root on arm64 and updates itself, so SteamOS updates leave
  it alone.
author: Anthropic
source: {relation: from, url: https://code.claude.com/docs/en/setup}
icon: {theme: utilities-terminal}
run: {label: Open}
changes: "`~/.local/bin/claude` and `~/.local/share/claude` (Anthropic's installer)"
access: Downloads Anthropic's installer over HTTPS
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall claude-code`"
---
# Claude Code (command line)

Anthropic's coding agent in the terminal: `claude` in Konsole. It reads and edits files in
the folder you start it in and runs commands there, asking first.

<!-- generated:glance (dev/gen-docs.py, from each tweak's README front matter) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** `~/.local/bin/claude` and `~/.local/share/claude` (Anthropic's installer)
> - **Unusual access:** Downloads Anthropic's installer over HTTPS
> - **Undo:** `./install.sh uninstall claude-code`
<!-- /generated:glance -->

```sh
./install.sh install claude-code
claude          # in any terminal; the first run logs in through your browser
```

Installed with [Anthropic's native installer](https://code.claude.com/docs/en/setup)
(`curl -fsSL https://claude.ai/install.sh | bash`) into `~/.local/bin/claude`, which
updates itself. Linux arm64 is supported, and it lives in your home folder, so SteamOS updates
leave it alone. If `claude` is already installed another way (for example Homebrew's
`claude-code` cask), the installer leaves it as it is.

**▶ Open** starts it in a new Konsole window in your home folder.

Remove: `./install.sh uninstall claude-code` (keeps `~/.claude` and your login).

## Credits
Made by [Anthropic](https://www.anthropic.com/claude-code). This tweak only runs Anthropic's installer.

---
Check: `./install.sh status claude-code` · Remove: `./install.sh uninstall claude-code`
