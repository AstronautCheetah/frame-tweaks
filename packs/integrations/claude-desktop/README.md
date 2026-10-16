---
title: Claude Desktop
emoji: 🤖
category: Developer
tier: extras
summary: "Anthropic's Claude Desktop app for Linux (arm64), installed without apt"
what: >-
  Claude Desktop, Anthropic's official Linux app (arm64), installed into your home folder and
  updated with one command.
why: >-
  Anthropic ships it as an apt package for Ubuntu and Debian. SteamOS has no apt and its system
  files are read-only, so this unpacks the package into your home folder instead.
author: Anthropic
source: {relation: from, url: https://claude.com/download}
icon: {theme: help-about}
run: {label: Open}
wallet_apps: [com.anthropic.Claude]
config: [~/.config/Claude]
app: Claude Desktop
changes: >-
  The app in `~/.local/opt/claude-desktop`, `claude-desktop` and `claude-desktop-update` in
  `~/.local/bin`, an app-menu entry and icons
access: >-
  Downloads from Anthropic's apt repository (`downloads.claude.ai`) and checks the SHA256 it
  lists; Claude keeps your sign-in in the KDE wallet
survives_updates: Yes (everything is in your home folder)
undo: >-
  `./install.sh uninstall claude-desktop` (keeps your Claude settings in `~/.config/Claude`)
---
# Claude Desktop

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Claude Desktop, Anthropic's official Linux app (arm64), installed into your home folder and updated with one command.

**Why on a Steam Frame:** Anthropic ships it as an apt package for Ubuntu and Debian. SteamOS has no apt and its system files are read-only, so this unpacks the package into your home folder instead.
<!-- /generated:intro -->

## Install

Tick it in the Frame Tweaks window, or:

```sh
./install.sh install claude-desktop
```

Nothing else to do.

## Use

Open **Claude** from the app menu, from Steam's VR **+** menu, or with **▶ Open** in the Frame
Tweaks window. The first time, sign in with your Claude account.

**Updates:** this copy doesn't update itself. When a newer version is out, the Frame Tweaks window
shows **↑ … available · Update** on this tweak's row. Or run, in a terminal:

```sh
claude-desktop-update
```

It does nothing if you're already up to date. If Claude is open, it stops and asks you to quit
Claude first, so you don't lose anything you were typing. To have it close Claude for you, run
`claude-desktop-update --restart`, then open Claude again.

## How it works

`claude-desktop-update` reads the list of packages in Anthropic's apt repository, downloads the
newest arm64 `.deb`, checks it against the SHA256 the list gives, and unpacks it into
`~/.local/opt/claude-desktop`. The list itself comes over HTTPS; its apt signature isn't
checked. It also adds Claude's app-menu entry and icons.

Claude always starts through a small launcher, `~/.local/bin/claude-desktop`, which tells it to
keep your sign-in in the KDE wallet. Without the wallet, Claude can't store it securely and asks
you to sign in again after every restart. With the [Shared KDE wallet](../../core/wallet/) tweak, it uses
the same wallet in desktop mode and in VR, and it's listed on that tweak's **Wallet apps** page.

## Good to know

- If the Frame Tweaks window warns that Claude can't reach the KDE wallet, quit Claude and open
  it again, so it keeps your sign-in.
- Uninstalling closes Claude if it's open and removes the app, but keeps your Claude settings.
- **"Hardware acceleration disabled"** after a restart: if Claude is open when the Frame restarts
  or shuts down, its graphics go away under it, it takes that for repeated graphics problems and
  turns hardware acceleration off. Turn it back on from Claude's **Help** menu, then quit and
  open Claude again.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** The app in `~/.local/opt/claude-desktop`, `claude-desktop` and `claude-desktop-update` in `~/.local/bin`, an app-menu entry and icons
- **Unusual access:** Downloads from Anthropic's apt repository (`downloads.claude.ai`) and checks the SHA256 it lists; Claude keeps your sign-in in the KDE wallet
- **Undo:** `./install.sh uninstall claude-desktop` (keeps your Claude settings in `~/.config/Claude`)
<!-- /generated:changes -->

## Credits
Claude Desktop is made by Anthropic. This tweak only downloads it from Anthropic's apt repository,
checks its checksum and unpacks it. Frame Tweaks isn't affiliated with Anthropic. See also
[CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status claude-desktop` · Remove: `./install.sh uninstall claude-desktop`
