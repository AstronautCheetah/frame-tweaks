---
title: Shared clipboard
emoji: 📋
category: Convenience
tier: core
summary: >-
  One clipboard for desktop mode and VR floating windows (clipboard-sync, built from upstream)
what: "Copy in a floating VR window, paste in the desktop, and back."
why: >-
  The Frame's VR session and its nested desktop each have their own clipboard. This runs
  [clipboard-sync](https://github.com/dnut/clipboard-sync), built from upstream, as
  steam-frame-nix does.
author: dnut (clipboard-sync); approach from lhns/steam-frame-nix
source: {relation: uses, url: https://github.com/dnut/clipboard-sync}
icon: {theme: edit-paste}
run: {label: Restart}
processes: [^~/.local/bin/clipboard-sync]
changes: >-
  `clipboard-sync` built from source (with a temporary, pinned Rust toolchain), KDE autostart
  entry
access: Reads and writes both sessions' clipboards
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall clipboard`"
---
# Clipboard: one clipboard for desktop mode and VR windows

**Problem:** the Frame runs two sessions: Steam/VR (its floating windows live on X display
`:0`) and the nested Plasma desktop (its own Wayland and X `:2`). They have **separate
clipboards**, so copying in a floating VR window and pasting in the desktop (or back) doesn't
work.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** `clipboard-sync` built from source (with a temporary, pinned Rust toolchain), KDE autostart entry
> - **Unusual access:** Reads and writes both sessions' clipboards
> - **Undo:** `./install.sh uninstall clipboard`
<!-- /generated:glance -->

**Fix:** [dnut/clipboard-sync](https://github.com/dnut/clipboard-sync) watches every X11 and
Wayland clipboard it can reach and keeps them in sync. Started with the desktop session, it
sees both.

```sh
./install.sh install clipboard
```

- Built from **upstream source**, at the commit pinned in `pin`, with a pinned Rust toolchain
  (`rust.pin`) set up in a temporary folder for the build and deleted afterwards (about 600 MB
  while it builds, nothing after). The build takes a minute or two. Older versions used
  Homebrew's Rust, which stays installed (3.4 GB with its LLVM): if you don't use it,
  `brew uninstall rust && brew autoremove`.
- One small change is applied before building, [`keep-images.patch`](keep-images.patch):
  clipboard-sync shares text only, and when you copied an image (e.g. Copy image in the screen
  snip) it saw "no text" as a change and put the last text back everywhere a moment later,
  so the image never pasted. With the patch it leaves a clipboard without text alone.
- Only one copy runs: starting it (desktop login, Restart) stops any left over from a desktop
  session that was restarted, which otherwise kept syncing too.
- Starts with desktop mode via KDE autostart (`~/.config/autostart/clipboard-sync.desktop`).
  It needs the desktop session's environment: started from VR or a user service, it wouldn't
  see the desktop's clipboard.

## Credits
This is the approach of [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix)'s
`clipboardSync` module (Apache-2.0), done without Nix; the tool is
[dnut/clipboard-sync](https://github.com/dnut/clipboard-sync). See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status clipboard` · Remove: `./install.sh uninstall clipboard`
