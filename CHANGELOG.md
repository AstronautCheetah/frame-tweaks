# Changelog

## Unreleased
- **Uninstalling or reinstalling a tweak stops its running programs first** (listed in
  `<tweak>/processes`: Arrow Pad, NordVPN tray, clipboard-sync, Full Keyboard), so an old copy
  can't keep running after a reinstall; Arrow Pad's held keys are released.
- Arrow Pad keeps a crash traceback in `/run/user/$UID/arrowpad-<target>-crash.log`.
- **Arrow Pad, more Full Keyboard:** keys drawn its way (a side, a face that travels down when
  pressed, hover gradient); Graphite and Midnight themes and haptic strength in a ⚙ settings
  page; the Steam Frame logo on Super and a SteamOS key (opens the app menu) on the Fn layer; in VR,
  grip-to-grab anywhere on the pad and two-handed modifiers (hold Ctrl with one laser, press with
  the other). Redraws are quicker (lighter PNG compression, up to ~7 a second).
- **Claude Desktop** updated to 2.31226.1.
- **Arrow Pad VR: a tap could count twice.** Both of the pad's double-buffered overlays took laser
  input, so for ~50 ms per redraw a click reached both: one tap locked a modifier (a locked Super
  turns every click into Super+click) or toggled R/M on and off. Only the front overlay takes input
  now, and a repeat within 60 ms is dropped. Closing the dashboard also releases held modifiers.
- **Arrow Pad uninstall:** `--quit` no longer needs a display (it crashed when run from the
  installer), and any pad still running is stopped, so a reinstall really runs the new version.
- **Arrow Pad right/middle-click toggles:** a scroll while one was armed was swallowed and turned
  into a right/middle click (the controller's scroll is mouse "buttons" 4/5); scrolling now passes
  through. Toggles also cancel when the dashboard closes and after 10 s (was 20), a press whose
  release never arrives is replayed after 1.5 s, and every step is logged
  (`/run/user/$UID/arrowpad-clicks.log`). Tested on a private X display (`tests/test_clickswap.py`).
- **Arrow Pad looks:** Full Keyboard's own toolbar and copy/paste icons (ported, MIT), including
  its pin on/off icons; a slight sideways lean eases level after a grab, as in Full Keyboard.
- **Installer window in VR:** A/B/Y and the D-pad are claimed only while the laser is really on
  the window (pointer inside it and moving), not just while Qt thinks it's hovered.
- **Pinned:** clipboard-sync builds a pinned commit; the Whisper model is fetched from a pinned
  Hugging Face revision and checked against its SHA256 (it was the moving `main` branch,
  unchecked); Python packages install at exact versions (`lib/python-constraints.txt`).
  `dev/check-pins.sh` reports newer versions of all of them.
- **Claude Desktop updater:** refuses while Claude Desktop is open (it used to close it without
  asking); `claude-desktop-update --restart` to do it anyway; downloads retry.

## 0.4.0 (2026-10-08)
- **Release channels:** updates and `get.sh` take stable `vX.Y.Z` releases only (pre-releases
  used to win over their final version); `beta` in `~/.config/steam-frame-tweaks/channel` opts
  into pre-releases.
- **Installer:** one install/update/removal at a time; every run logged; `debug-info` (redacted
  report; also a **Diagnostics** button); `hold`/`unhold`; `update --to vX.Y.Z`; per-tweak
  versions with `migrate.sh`; `check-system` (also after every update).
- **Installer window:** crash page with copyable details, single instance, D-pad row navigation
  in VR (left D-pad up/down, A ticks).
- **Backups:** `backup_file`/`restore_file` and per-key KDE settings restore; the wallet puts its
  `kwalletrc` settings back on removal.
- **Wallet:** fixed the 4-hour auto-lock never being scheduled again after one failed lock
  (a leftover unit name blocked it, silently); status warns when unlocked without an auto-lock.
- **Sandboxing** for ydotoold, wallet-lock-sync and the curvature services.
- **New tweaks:** Memory caps (Whisper, scrcpy, VSCodium) and Screen reader (Orca).
- **Packaging:** AppStream metainfo, desktop ID `io.github.AstronautCheetah.FrameTweaks`, icons in
  three sizes; CI validates them.
- **Docs:** README/SECURITY tables and per-tweak "At a glance" boxes generated from each tweak's
  `meta`; Common issues; roadmap.
- **Engineering:** unit tests, release workflow, actions pinned to commits.
- Uninstalling Dictation, Wallet, Arrow Pad, NordVPN or Android Mirror now also removes its
  menu icon (found by the install test).
- ydotool: a service that fails to start is reported as a warning instead of failing the
  install silently.
- Install test covers ydotool, Dictation and Wallet too, with a fake network (fixtures for the
  Whisper model and the Arch package).
- CI runs once per commit on main (not again for each release tag) and cancels superseded runs.

## 0.3.1 (2026-10-07)
- Menu icons: no longer fails on a fresh home folder that has no icon theme folder yet
  (found by the new install test in CI).

## 0.3.0 (2026-10-07): first release candidate

Frame Tweaks (formerly "Steam Frame Tweaks") is a checklist installer of home-folder-only
tweaks for the Valve Steam Frame.

**Core: fixes for the Frame**
- **Arrow Pad:** the keys the Steam keyboard lacks (arrows, Home/End, PgUp/PgDn, Esc, Tab,
  F-keys, one-shot Ctrl/Alt/Super), right/middle-click toggles, clipboard keys and a dictation
  button. In desktop mode it never takes focus; in VR it's a native SteamVR overlay below the
  dashboard with Full Keyboard's look, placement, grab and haptics.
- **Full Keyboard** (TaiKeid) and **whisper-frame** (groffta), installed from pinned releases.
- **Dictation:** local Whisper speech-to-text on the Frame's GPU, typed into the focused app.
- **Curved world windows:** windows floated into the world start curved.
- **Cursor fix, shared clipboard, shared KDE wallet** (one wallet for both sessions, unlock
  dialog, auto-lock, password-gated apps), **menu icons** for Steam's "+" menu, **tools**.

**Extras:** Android Mirror, Signal and Firefox hardening, NordVPN over WireGuard, VSCodium,
Claude Code and Claude Desktop. **Helpers:** Homebrew, ydotool.

**Installer window:** categories that fold and hide, per-row ▶ actions, details pages with
each tweak's README, update hints, known-issue notes, and controller buttons in VR
(B back, Y home, A tick).

**Trust and safety**
- Upstream releases pinned to recorded SHA256s; Arch Linux ARM packages signature-checked;
  `get.sh` and `update` install release tags, not `main`.
- SECURITY.md lists what every tweak changes on your system, including ports, pointer grabs and
  controller buttons.
- Curvature checks SteamVR's dashboard code and disables itself if an update changed it.
- CI: ShellCheck, Python syntax, docs consistency, pinned-download checks, and an install →
  status → uninstall test in a throwaway home.

Tested on SteamOS 0.4.5 (build 20261006.6173745), SteamVR build 1791331621, one headset.

## 0.1–0.2.9 (2026-10-07): development

Built up on one Frame; the commit history has the details.
