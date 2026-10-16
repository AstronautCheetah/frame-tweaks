---
title: Full Keyboard (VR)
emoji: ⌨️
category: Convenience
tier: core
summary: >-
  TaiKeid's full-size VR keyboard, shown with the SteamVR dashboard, installed from its newest
  release
what: >-
  TaiKeid's Full Keyboard: a full-size keyboard you type on with the controller lasers, with
  arrows, F-keys, a numpad, Ctrl/Alt and Copy/Paste. It shows while the SteamVR dashboard is
  open, and types into the app you're using, desktop mode's included.
why: >-
  Steam's own VR keyboard lacks keys the desktop needs, such as up/down arrows, Ctrl and F-keys.
  Linked: it installs from its newest release with its own installer, the way its README
  describes.
author: TaiKeid (steam-frame-full-keyboard)
source:
  relation: from
  url: https://github.com/TaiKeid/steam-frame-full-keyboard
icon: {theme: input-keyboard}
run: {label: Open}
processes: [/framekeyboard( |$)]
config: [~/.config/framekeyboard]
app: Full Keyboard
link:
  install: d=$(mktemp -d) && trap 'rm -rf "$d"' EXIT && cd "$d" && u=https://github.com/TaiKeid/steam-frame-full-keyboard/releases/latest/download && curl -fsSLO "$u/SHA256SUMS" && f=$(grep -o 'framekeyboard-.*-aarch64\.tar\.gz' SHA256SUMS) && v=${f#framekeyboard-} && v=${v%-aarch64.tar.gz} && if [ -e ~/.local/share/framekeyboard/releases/$v ]; then echo "Full Keyboard $v, its newest release, is already installed"; else curl -fsSLO "$u/$f" && sha256sum -c --ignore-missing SHA256SUMS && tar -xzf "$f" && bash "${f%.tar.gz}/install.sh"; fi
  uninstall: rm -f ~/.local/bin/framekeyboard ~/.local/share/applications/framekeyboard.desktop && rm -rf ~/.local/share/framekeyboard
  installed: ~/.local/share/framekeyboard/current
  run: gtk-launch framekeyboard
  readme: https://github.com/TaiKeid/steam-frame-full-keyboard#readme
changes: >-
  Whatever Full Keyboard's own installer sets up (its README lists it): its newest release in
  `~/.local/share/framekeyboard`, with `~/.local/bin/framekeyboard` and an app-menu entry
access: A SteamVR overlay; types into the app you're using
survives_updates: Yes (everything is in your home folder)
undo: >-
  Uncheck it, or `./install.sh uninstall full-keyboard`: Full Keyboard's own removal steps (keeps
  its settings in `~/.config/framekeyboard`)
---
# Full Keyboard

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
TaiKeid's Full Keyboard: a full-size keyboard you type on with the controller lasers, with arrows, F-keys, a numpad, Ctrl/Alt and Copy/Paste. It shows while the SteamVR dashboard is open, and types into the app you're using, desktop mode's included.

**Why on a Steam Frame:** Steam's own VR keyboard lacks keys the desktop needs, such as up/down arrows, Ctrl and F-keys. Linked: it installs from its newest release with its own installer, the way its README describes.
<!-- /generated:intro -->

A **link**: Frame Tweaks runs Full Keyboard's own steps, as its
[README](https://github.com/TaiKeid/steam-frame-full-keyboard#readme) gives them, in the terminal
it opens for installs, and doesn't pin or change what they install.

- **Install** (tick it): downloads the newest release and its `SHA256SUMS` from GitHub, checks
  the one against the other (`sha256sum -c`), unpacks it and runs its `install.sh`. Nothing else
  to do.
- **Update:** when TaiKeid publishes a newer release, its row says so; ↻ installs it the same
  way. Frame Tweaks' own updates leave it alone. Full Keyboard's installer keeps the previous
  release for rollback.
- **Uninstall** (untick it): removes `~/.local/bin/framekeyboard`, its app-menu entry and
  `~/.local/share/framekeyboard` (every installed release), and keeps your settings, layouts and
  themes in `~/.config/framekeyboard`.

Install, update and uninstall close the keyboard first if it's open.

## Use

With the VR session running, open **Full Keyboard** from the dashboard's app launcher. Focus a
text field, then type with the controller laser. Opening it again re-centres it. It's a separate
app: the system keyboard button still opens Steam's keyboard. The full guide is TaiKeid's
[README](https://github.com/TaiKeid/steam-frame-full-keyboard#readme).

- **It shows only while the SteamVR dashboard is open**, whichever menu started it: closing the
  dashboard hides it. To type into desktop mode, open the dashboard over it.
- **To move it,** point at it and squeeze grip, with either hand; while you hold grip, the
  thumbstick moves it nearer or farther. After opening it, let go of grip once first. It reads
  the grip of the Frame's own controllers only.

Not sure which keyboard to use? See the [keyboard guide](../../core/arrowpad/README.md#which-keyboard-when).

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** Whatever Full Keyboard's own installer sets up (its README lists it): its newest release in `~/.local/share/framekeyboard`, with `~/.local/bin/framekeyboard` and an app-menu entry
- **Unusual access:** A SteamVR overlay; types into the app you're using
- **Undo:** Uncheck it, or `./install.sh uninstall full-keyboard`: Full Keyboard's own removal steps (keeps its settings in `~/.config/framekeyboard`)
<!-- /generated:changes -->

## Credits

Full Keyboard is by [TaiKeid](https://github.com/TaiKeid/steam-frame-full-keyboard) (MIT).
Frame Tweaks only runs its install steps. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status full-keyboard` · Remove: `./install.sh uninstall full-keyboard`
