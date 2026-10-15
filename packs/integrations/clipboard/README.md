---
title: Shared clipboard
emoji: 📋
category: Convenience
tier: core
summary: One clipboard for desktop mode and VR floating windows, files and pictures included
what: >-
  Copy in a floating VR window and paste in the desktop, and the other way round: text, files
  and pictures, and the text you select for a middle-click paste. It runs Frame Tweaks' build of
  [clipboard-sync](https://github.com/dnut/clipboard-sync), with the changes the Frame needs.
why: >-
  The Frame's VR session and its desktop mode each have their own clipboard, so text copied in
  one can't be pasted in the other.
author: dnut (clipboard-sync); Frame Tweaks (its fork); approach from lhns/steam-frame-nix
source: {relation: uses, url: https://github.com/AstronautCheetah/clipboard-sync}
icon: {theme: edit-paste}
run: {label: Restart}
processes: [^~/.local/bin/clipboard-sync]
app: clipboard-sync
changes: >-
  `clipboard-sync` (Frame Tweaks' build, a pinned and checked release) in
  `~/.local/share/frame-tweaks/`, a KDE autostart entry
access: Reads and writes both sessions' clipboards
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall clipboard`"
upstream_readme: https://raw.githubusercontent.com/AstronautCheetah/clipboard-sync/v0.2.0-ft.1/README.md
---
# Shared clipboard

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Copy in a floating VR window and paste in the desktop, and the other way round: text, files and pictures, and the text you select for a middle-click paste. It runs Frame Tweaks' build of [clipboard-sync](https://github.com/dnut/clipboard-sync), with the changes the Frame needs.

**Why on a Steam Frame:** The Frame's VR session and its desktop mode each have their own clipboard, so text copied in one can't be pasted in the other.
<!-- /generated:intro -->

## Install
Tick it in the Frame Tweaks window, or:

```sh
./install.sh install clipboard
```

It downloads Frame Tweaks' build of clipboard-sync (about 1 MB) and checks it against the
checksum in [`pin`](pin). If desktop mode is running, it starts right away; otherwise it starts
the next time you open desktop mode.

## Use
Nothing to do: copy as usual in a floating VR window or in the desktop, and paste in the other.

- **Text**, as you'd expect, and the text you select (for a middle-click paste: Arrow Pad's **M**
  key in VR).
- **Files** copied in a file manager paste as files in the other session (both see the same
  files): in a file manager there, or an app that takes files. A cut is shared as a copy there,
  so a paste in the other session never moves a file.
- **Pictures** (PNG, JPEG, BMP, GIF or WebP, up to 32 MB), for example from a browser's **Copy
  Image** or [Screen snip + Narrate](../../original/snip/)'s **Copy**.
- **Passwords** a password manager copies (KeePassXC, …) can be pasted in the other session, and
  go from there when the password manager clears them.

It runs while desktop mode is running. If copying stops working, press **Restart** on its row
in the Frame Tweaks window.

## How it works
The Frame runs two sessions side by side: Steam and VR (where floating windows live), and the
desktop, which runs nested inside it with its own displays. Each has its own clipboard.
[clipboard-sync](https://github.com/dnut/clipboard-sync) watches every X11 and Wayland clipboard
it can reach and copies new text to the others. Started with the desktop session, it can reach
both.

- **Frame Tweaks' build:** [AstronautCheetah/clipboard-sync](https://github.com/AstronautCheetah/clipboard-sync)
  is clipboard-sync with Frame Tweaks' changes as commits, offered upstream too. Its Build
  workflow tests it and makes the aarch64 binary for each release; [`pin`](pin) names the
  release and its SHA256, which the install checks. (Older versions built it on the Frame, with a
  temporary Rust toolchain and about 600 MB of space; reinstalling removes what they left.)
- **Frame Tweaks' changes** (clipboard-sync shared text only, and wrote it into every clipboard):
  - **Copying an image** looked like "no text" to it, so it put the last text back a moment
    later and the image never pasted.
  - **Everything else:**
    - **A copy is never written back where it came from.** It was, as text, replacing what the
      app had put there: a file cut or copied in Dolphin then pasted only as its address
      ("Paste Clipboard Contents"), formatted text lost its formatting, and a password manager's
      "don't keep this in the clipboard history" mark was dropped. The desktop's own X11
      clipboard is left to KWin, which already passes copies between it and the desktop's
      Wayland one.
    - **Files, pictures and the selection are shared**, not just text. VR's X11 clipboards get a
      copy with all its formats at once (text and a file list, say), from a clipboard owner of
      its own (adapted from x11-clipboard's, MIT).
    - **Copies are noticed as they happen**: from the desktop's Wayland clipboard (its
      data-control protocol) and VR's X11 ones (XFixes), instead of reading every clipboard five
      times a second. A picture copied over another is noticed too, and it uses next to no
      processor time while nothing is copied.
    - **Passwords**: a copy its password manager marks secret is shared with the mark where the
      clipboard can carry it, and the copies are emptied when the original is. (Which session a
      password came from is noted in the runtime folder, in memory; never the password.)
    - **Starting replaces nothing.** It starts again every 10 minutes, and each start wrote test
      values, then the first text it found, into every clipboard: a file or picture copied but
      not yet pasted was replaced. Now only a clipboard with nothing on it gets what the others
      hold (a copy it had shared there goes when it restarts).
- **Starts with desktop mode** through KDE autostart
  (`~/.config/autostart/clipboard-sync.desktop`). It needs the desktop session's environment;
  started from VR or as a background service, it wouldn't see the desktop's clipboard.
- **Only one copy runs:** starting it (at desktop login, or with Restart) first stops any copy
  that is still running, for example from a desktop session that was restarted.

## Good to know
- Formats beyond text, files and pictures (a spreadsheet's cells, an app's own formats) stay
  where you copied them; the other session gets their text, if they have any.
- Android Mirror can pass the clipboard on to the phone: see its setting **Share the clipboard
  with the phone**.
- The status line shows the build's version, and warns if it isn't running, if more than one
  copy is running, or if an older version's build lacks these changes (reinstall it to fix that).
- If you have Homebrew's Rust installed and don't use it yourself, installing or removing this
  tweak reminds you that you can free about 3.4 GB with
  `brew uninstall rust && brew autoremove`.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `clipboard-sync` (Frame Tweaks' build, a pinned and checked release) in `~/.local/share/frame-tweaks/`, a KDE autostart entry
- **Unusual access:** Reads and writes both sessions' clipboards
- **Undo:** `./install.sh uninstall clipboard`
<!-- /generated:changes -->

## Credits
This is the approach of [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix)'s
`clipboardSync` module (Apache-2.0), done without Nix; the tool is
[dnut/clipboard-sync](https://github.com/dnut/clipboard-sync) (MIT or Apache-2.0), which Frame
Tweaks' fork builds on. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status clipboard` · Remove: `./install.sh uninstall clipboard`

<!-- generated:upstream (dev/gen-docs.py, from upstream.md) -->
---

*The rest of this page is [AstronautCheetah/clipboard-sync](https://github.com/AstronautCheetah/clipboard-sync)'s own README at `v0.2.0-ft.1`, © its authors, under [MIT](https://raw.githubusercontent.com/spdx/license-list-data/v3.27.0/text/MIT.txt) or [Apache-2.0](https://raw.githubusercontent.com/spdx/license-list-data/v3.27.0/text/Apache-2.0.txt), as its author wrote it (only links and heading levels adjusted), included for its instructions and credits. Everything above is Frame Tweaks'.*

## Clipboard Sync

Synchronizes the clipboard across multiple X11 and wayland instances running on the same machine.

> **This fork** is the clipboard-sync that [Frame Tweaks](https://github.com/AstronautCheetah/frame-tweaks)
> installs as its Shared clipboard on the Steam Frame, where desktop mode is a nested KWin (Wayland,
> with its own Xwayland) inside the VR session's gamescope (X11). It's
> [dnut/clipboard-sync](https://github.com/dnut/clipboard-sync) plus two commits (see the log):
> a copied image is no longer replaced by the last text; and files, pictures and the primary
> selection are shared, a copy is never written back where it came from, a password manager's
> secret mark is kept, copies are noticed as they happen (data-control, XFixes) instead of polled,
> and a start replaces nothing. [Releases](https://github.com/AstronautCheetah/clipboard-sync/releases)
> have a prebuilt aarch64 Linux binary (glibc 2.39 or newer, libxcb) with its SHA256SUMS, built by
> this repository's Build workflow. The changes are offered upstream too; licence as upstream's
> (MIT or Apache-2.0, in Cargo.toml).

To use clipboard sync, you only need to install it and start the service. It identifies and synchronizes your clipboards automatically.

Example use cases:

- **Improve Wayland compatibility**: You have already enabled support for wayland in your system, but your computer does not synchronize the clipboard between X11 and wayland windows. clipboard-sync can solve this problem. [more details](https://github.com/dnut/clipboard-sync/issues/9#issuecomment-1502368133)
- **VNC**: You run a VNC server and would like all host and client logins from the same user to share the same clipboard.
- **Multiple displays**: You run two or more desktop environments or window managers in separate ttys, switching between desktops using ctrl-alt-F*.
- **Nested Wayland**: You run a wayland compositor within a window. examples:
  - you primarily use kde, but run sway in a window to consolidate all your messenger apps into a single tiled/tabbed window.
  - you use gnome and develop extensions for gnome, so you run a nested gnome environment for testing.

Table of Contents:
- [Installation](#installation)
- [Usage](#usage)
- [Build From Source](#build-from-source)

## Installation
Install clipboard-sync with your system's package manager. If your system is not supported, please vote on [the appropriate issue](https://github.com/dnut/clipboard-sync/issues?q=is%3Aissue+label%3Adistribution), or create one if it does not exist.

#### Arch Linux
[clipboard-sync](https://aur.archlinux.org/packages/clipboard-sync) is available in the Arch User Repository.

#### Ubuntu & Debian
Install from the official repository:
```bash
sudo wget -P /etc/apt/sources.list.d/ https://raw.githubusercontent.com/dnut/deb/master/dnut.list
sudo apt update && sudo apt install clipboard-sync
```
You can also manually [build and install a deb package from source](#deb-package).

#### Fedora & CentOS
We don't have a repository yet, but you can build an RPM and install it.

```bash
# clone the repo
git clone https://github.com/dnut/clipboard-sync.git
cd clipboard-sync

# install the build dependencies
sudo dnf install rpm-build rpmdevtools libxcb-devel systemd-rpm-macros rust cargo

# build the package
make rpm

# install the package (you may want to specify the explicit path in case there are dupes)
sudo dnf install ~/rpmbuild/RPMS/*/clipboard-sync-0*.rpm
```

#### NixOS
Add this repo to your flake inputs:
```nix
clipboard-sync.url = "github:dnut/clipboard-sync";
```

Put `clipboard-sync.nixosModules.default` into flake modules.

To enable the systemd service, add `services.clipboard-sync.enable = true;` into the `configuration.nix`.

### Advanced Installation
If your system is not supported, you have two other options:
- [Generic Linux](#generic-linux)
  - automatically and cleanly installs or uninstalls the entire package.
  - requires extra steps to acquire the source code.
- [Cargo](#cargo)
  - only installs the executable, which needs to be run manually.
  - requires extra steps to manually edit and install a systemd service if desired.
  - If you use [cargo-update](https://crates.io/crates/cargo-update), it can make updates to the executable easier.

#### Generic Linux
[Build from Source](#build-from-source), then install ***either*** system-wide ***or*** for only the current user:
```bash
sudo make install  # system
make user-install  # user
```
It can be easily uninstalled:
```bash
sudo make uninstall  # system
make user-uninstall  # user
```

#### Cargo
[clipboard-sync](https://crates.io/crates/clipboard-sync) is published to crates.io, so it can be installed as a normal binary crate.

1. Install rust: https://www.rust-lang.org/tools/install
2. Install clipboard-sync
```bash
cargo install clipboard-sync
```
3. If you want it to run in the background, you can use tmux, or you can manually download the systemd service file and copy it to a systemd folder. You can download it to the correct path using this command, after which you may need to manually edit the file to point the correct binary location:
```bash
wget -P "$HOME/.config/systemd/user/" https://raw.githubusercontent.com/dnut/clipboard-sync/master/clipboard-sync.service
```
It can be easily uninstalled:
```bash
cargo uninstall clipboard-sync
rm -r "$HOME/.config/systemd/clipboard-sync.service"
```

## Usage
The typical set-and-forget approach is to enable to service:
```bash
systemctl --user enable --now clipboard-sync
```

If you don't want it to run constantly, only on-demand, don't use systemd. Directly call the binary as needed:
```bash
clipboard-sync
```

You can also daemonize clipboard-sync using tmux instead of systemd. ~/.bashrc aliases may be handy for these commands.
```bash
tmux new-session -ds clipboard-sync clipboard-sync  # start in background
tmux attach -t clipboard-sync                       # view status
ctrl-b, d                                           # while viewing status, send back to background
ctrl-c                                              # while viewing status, terminate the process
```

## Build from Source

1. Ensure you have the build dependencies: rust make gcc libc libxcb
- install rust using rustup: https://www.rust-lang.org/tools/install
- For the rest:
  - arch linux: `sudo pacman -Syu make gcc libxcb`
  - debian/ubuntu: `sudo apt install make gcc libxcb1-dev libxcb-render0-dev libxcb-shape0-dev libxcb-xfixes0-dev`

2. Download the source from [the releases page](https://github.com/dnut/clipboard-sync/releases/) and unzip it. Alternatively, select *one* of these commands to download the source:
```bash
wget -O- https://github.com/dnut/clipboard-sync/archive/refs/tags/0.2.0.tar.gz | tar xvz
curl -L https://github.com/dnut/clipboard-sync/archive/refs/tags/0.2.0.tar.gz | tar xvz
git clone https://github.com/dnut/clipboard-sync.git --branch stable
```

3. Compile the program
```bash
cd clipboard-sync*
make
```

The executable is here:
```bash
./target/release/clipboard-sync
```

#### Deb package
In addition to installing from the official repository for Debian and Ubuntu, you can also build and install the deb package from source. Follow the instructions above, then you can simple create a deb package with a single command.
```bash
# build
make deb

# install
sudo apt install ./dist/deb/clipboard-sync_*.deb
```
<!-- /generated:upstream -->
