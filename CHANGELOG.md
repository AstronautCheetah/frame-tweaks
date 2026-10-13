# Changelog

## Unreleased
- **Password first no longer disappears:** re-wrapping an app's menu entry (after an app update,
  or when another tweak adds its app) dropped the wallet-password gate, which is how Claude
  Desktop lost it. `wallet-launcher` now keeps it unless told `--no-gate`. Signal shows it as
  provided by Signal guard. Re-wrapping a protected system app no longer treats the override as
  the original.
- **🔑 Wallet apps in the installer window:** choose which apps open with the shared KDE wallet.
  It lists every installed app (Flatpaks from any source, system apps, your own launchers),
  detects Electron/Chromium apps, and has a Password-first switch, a **Close after** timer and
  Remove for each protected app. The timer (new `app-timers` service) quits the app after that
  long with no input, like Signal guard does for Signal. `wallet-launcher` can now wrap system
  apps too.
- **Android Mirror's "Phone not found" names the phones it did see**, and says Wireless debugging
  lives in Developer options in the phone's Owner profile (a different phone on the same Wi-Fi
  was easy to mistake for yours).
- **Arrow Pad VR's mic button showed the previous dictation state:** the redraw could run before
  the button was recoloured, so the first tap didn't turn it red and it stayed yellow after the
  text arrived. It now goes red while recording, yellow while transcribing, then back to normal.
- **Claude Desktop kept signing you out:** some starts reached no wallet (Chromium's `basic_text`
  fallback), so the sign-in was never saved, and one saved by a wallet-backed start couldn't be
  read. `~/.local/bin/claude-desktop` is now a launcher that always uses the shared KDE wallet, however
  Claude is started (app menu, VR "+" menu, `claude://` links, a terminal). Its status check
  warns when the running Claude couldn't reach the wallet.
- **↻ Reinstall button** on each installed tweak in the installer window, and
  `./install.sh reinstall ID...`: stops its programs, removes it and installs it again in one step
  (also for a tweak others depend on, such as ydotool).
- **Arrow Pad's uninstall keeps your settings** (`~/.config/arrowpad.json`: VR position, size,
  theme), as the installer window promises; a reinstall no longer resets them.
- **Arrow Pad VR still blinked when a toggle key changed (modifiers, Fn, R/M, mic, pin):** a
  display-only cover panel now shows the previous image on top while the pad loads the new one,
  then steps aside. It never takes laser input, so taps still go to the one input overlay.
- **Arrow Pad VR jumped when switching between the Steam and Desktop tabs:** it followed Steam's main
  panel when that was showing and the dashboard bar otherwise, and the Desktop tab hides the main
  panel, so it effectively kept two positions. It now follows the bar on both tabs. A position saved
  by an older version is converted once. Reset still puts it beneath the main panel.
- **Arrow Pad VR flickered after clicks:** every press and release reloaded the overlay image, and
  each reload blinks. Presses no longer redraw it (they're felt as a haptic click); it redraws only
  when something visible changes (modifiers, Fn, R/M, mic, pin, settings, theme), with normally
  compressed images again so SteamVR loads them faster.
- **Stuck modifiers:** when Arrow Pad starts, and when the installer stops or uninstalls it, the
  desktop is made to forget any Ctrl/Alt/Super/Shift a crashed pad left "held" (a full press and
  release each; Super and Alt around F24, so no menu opens). A stuck one used to add itself to
  every key until desktop mode was restarted.
- **Arrow Pad VR crashed on clicks** (a segfault inside SteamVR's PollNextOverlayEvent after the
  double-tap fix switched overlays' input modes on every redraw), and taps could still count twice.
  It's back to a single overlay whose input mode never changes; to keep reload flicker down it no
  longer redraws just because the laser hovers over another key (the hover tick is still felt).
- **Arrow Pad VR showed an old picture after reinstalling:** SteamVR caches overlay images by file
  name, and the pad reused two fixed names. Every image now gets a new name; old ones are deleted.
- **Arrow Pad uninstall** removes all its program files (it left vroverlay.py, haptics.py and the
  SteamVR input files behind).
- **NordVPN tray started twice at login** (autostart plus KDE's session restore): the tray now runs
  once (a second copy exits), and installing excludes it from session restore (restored on removal).
- **Claude Desktop couldn't use the KDE wallet:** its launcher lacked `--password-store=kwallet6`, so
  its login didn't persist and secrets fell back to plain text. wallet-launcher now adds it for
  Claude Desktop and keeps it when the launcher is re-applied after an update.
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
