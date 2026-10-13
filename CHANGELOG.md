# Changelog

## Unreleased
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
