---
title: Performance Overlay
emoji: 📈
category: System
tier: extras
summary: >-
  sasaken1102r's performance panel in VR: frame rate, CPU and GPU load, temperatures, memory and
  battery, on your wrist or in the dashboard
what: >-
  sasaken1102r's frame-perf-overlay: a small panel in VR with the frame rate and frame times,
  CPU and GPU load and clocks, temperatures, memory, battery and Wi-Fi. You choose what it shows
  and where, in its Perf tab in the SteamVR dashboard. It starts with SteamVR.
why: >-
  The Frame doesn't show its own temperatures, clocks or memory while you play, so a slowdown or
  a hot headset is hard to explain. Linked: it installs the release Frame Tweaks tested with its
  own installer, the way its README describes.
author: sasaken1102r (frame-perf-overlay)
source:
  relation: from
  url: https://github.com/sasaken1102r/frame-perf-overlay
icon: {file: frame-perf-overlay.png}
run: {label: Show}
processes: [/frame-perf-overlay( |$)]
config: [~/.config/frame-perf-overlay]
link:
  install: d=$(mktemp -d) && trap 'rm -rf "$d"' EXIT && cd "$d" && u=https://github.com/sasaken1102r/frame-perf-overlay/releases && if [ -n "$FT_LINK_VERSION" ]; then u=$u/download/$FT_LINK_VERSION; else u=$u/latest/download; fi && curl -fsSLO "$u/SHA256SUMS" && f=$(grep -o 'frame-perf-overlay-[0-9.]*\.tar\.gz' SHA256SUMS | head -1) && curl -fsSLO "$u/$f" && sha256sum -c --ignore-missing SHA256SUMS && tar -xzf "$f" && cd frame-perf-overlay && ./install.sh && (XDG_RUNTIME_DIR=/run/user/$(id -u) DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus systemctl --user enable frame-perf-overlay.service 2>/dev/null || true)
  uninstall: d=$(mktemp -d) && trap 'rm -rf "$d"' EXIT && cd "$d" && u=https://github.com/sasaken1102r/frame-perf-overlay/releases/latest/download && curl -fsSLO "$u/SHA256SUMS" && f=$(grep -o 'frame-perf-overlay-[0-9.]*\.tar\.gz' SHA256SUMS | head -1) && curl -fsSLO "$u/$f" && sha256sum -c --ignore-missing SHA256SUMS && tar -xzf "$f" && cd frame-perf-overlay && ./install.sh --uninstall
  installed: ~/.local/bin/frame-perf-overlay
  version: ~/.local/bin/frame-perf-overlay --version | awk '{print $2}'
  readme: https://github.com/sasaken1102r/frame-perf-overlay#readme
changes: >-
  Whatever frame-perf-overlay's own installer sets up (its README lists it):
  `~/.local/bin/frame-perf-overlay`, an app-menu entry and icons, a user service that starts and
  stops with SteamVR, and its updater in `~/.local/share/frame-perf-overlay`
access: A SteamVR overlay; reads the headset's sensors; asks GitHub once a day for a newer release
survives_updates: Yes (everything is in your home folder)
undo: >-
  Uncheck it, or `./install.sh uninstall perf-overlay`: frame-perf-overlay's own
  `install.sh --uninstall` (keeps its settings in `~/.config/frame-perf-overlay`)
---
# Performance Overlay

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
sasaken1102r's frame-perf-overlay: a small panel in VR with the frame rate and frame times, CPU and GPU load and clocks, temperatures, memory, battery and Wi-Fi. You choose what it shows and where, in its Perf tab in the SteamVR dashboard. It starts with SteamVR.

**Why on a Steam Frame:** The Frame doesn't show its own temperatures, clocks or memory while you play, so a slowdown or a hot headset is hard to explain. Linked: it installs the release Frame Tweaks tested with its own installer, the way its README describes.
<!-- /generated:intro -->

A **link**: Frame Tweaks runs frame-perf-overlay's own steps, as its
[README](https://github.com/sasaken1102r/frame-perf-overlay#readme) gives them, in the terminal
it opens for installs, and doesn't change what they install.

- **Install** (tick it): downloads the release Frame Tweaks tested (`link-perf-overlay` in
  `lib/tested-versions`) and its `SHA256SUMS` from GitHub, checks
  the one against the other (`sha256sum -c`), unpacks it and runs its `install.sh`. Its README
  also offers a one-line installer from the author's own website; Frame Tweaks uses the GitHub
  release instead, so what runs is what the checksum covers. One step is added after it: enabling
  the panel's user service with the Steam session's bus, the one thing its installer can't do from
  the desktop-mode terminal Frame Tweaks runs it in (there `systemctl --user` fails quietly, and
  the panel sat installed and never started).
- **Update:** when sasaken1102r publishes a release newer than the one Frame Tweaks tested, its row
  offers it as *not yet tested by Frame Tweaks* (↑ *version* available · **Update**); once
  it's installed, **↩ Back to the tested version** installs the tested one again. Frame
  Tweaks' own updates move it to a newer tested version, never to an untested one.
  `./install.sh link-version perf-overlay tested|newest` does the same.
  The panel's own **Update** button (in its Perf tab) installs its newest too.
- **Uninstall** (untick it): downloads the release again and runs its `install.sh --uninstall`,
  which stops it and removes what it installed. Your settings and profiles in
  `~/.config/frame-perf-overlay` stay; delete that folder too if you want them gone.

## Use

With SteamVR running the panel shows on its own. **Show** on its row in the Frame Tweaks window
shows it, starting it first if it isn't running; while it's shown the button reads **Hide** and
hides it. If an install left its service disabled, Show also enables it so it starts with SteamVR
again (`./install.sh run perf-overlay` does the same; the status says when that's needed). Its
**Perf** tab in the SteamVR
dashboard chooses what it shows, where (wrist, view or a fixed spot) and its profiles, and turns
it off until the next SteamVR start. Its
[README](https://github.com/sasaken1102r/frame-perf-overlay#usage) explains every value and
setting.

- **It looks for updates on GitHub** at start and then at most once a day, and installs one only
  when you confirm. To turn the check off, set `"update_check": false` in
  `~/.config/frame-perf-overlay/config.json`.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** Whatever frame-perf-overlay's own installer sets up (its README lists it): `~/.local/bin/frame-perf-overlay`, an app-menu entry and icons, a user service that starts and stops with SteamVR, and its updater in `~/.local/share/frame-perf-overlay`
- **Unusual access:** A SteamVR overlay; reads the headset's sensors; asks GitHub once a day for a newer release
- **Undo:** Uncheck it, or `./install.sh uninstall perf-overlay`: frame-perf-overlay's own `install.sh --uninstall` (keeps its settings in `~/.config/frame-perf-overlay`)
<!-- /generated:changes -->

## Credits

frame-perf-overlay is by [sasaken1102r](https://github.com/sasaken1102r/frame-perf-overlay)
(MIT). Frame Tweaks only runs its install steps. This tweak's icon, `frame-perf-overlay.png`, is
its own launcher icon (`contrib/icons/frame-perf-overlay-256.png`, MIT), unchanged. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status perf-overlay` · Remove: `./install.sh uninstall perf-overlay`
