# Changelog

## Unreleased
- **Every installer-window function has a command:** `./install.sh info`, `run`, `settings`
  (show, change, `--reset`), `hide`/`unhide`, `hide-group`/`unhide-group`, `wallet`,
  `wallet-apps` and `timers`. The window now uses the same code (`lib/sft.py`) for hidden rows,
  details and settings, so the two can't drift apart; tests check the VR gear panels offer the
  same choices.
- **Android Mirror has a settings page in the installer window** too (same choices as its gear).
- **Scroll strips' settings page** offers all the choices the gear in VR does (sizes, colour).
- **Fixed: scroll strips, gears and settings panels jittering, and the bottom of a settings panel
  missing.** They're drawn from the dashboard's one shared page, placed after its own content, so
  they moved whenever that changed size (its buttons grow under the laser), and a tall panel ran
  off the page. They now sit in fixed corners of the page, and the settings panels are drawn
  smaller there (same size in VR).
- **Fixed: reinstalling VR windows removed other tweaks' dashboard patches** (Android Mirror's
  size and touch layer, so it came up huge with no gear): a reinstall now keeps them.
- **Scroll strips: the gear and its settings sit as far back as the strips.**
- **Scroll strips settings in VR:** a gear where the two strips meet opens their settings beside
  the window: sides, thickness, gap, set-back and colour (the passthrough tint, or a hue of your
  own). The VR windows helper's service saves them (new `sftConfig` call; reinstall VR windows).
- **Android Mirror: Restart stream keeps a floating mirror where it was** (the new window used to
  open docked in the dashboard), with its settings panel still open.
- **Fixed: scroll strips and the Android Mirror's gear and settings jittering** while the laser
  crossed SteamVR's buttons below a window: each dashboard redraw handed SteamVR fresh copies of
  them. They're now reused while nothing they show has changed.
- **Android Mirror settings in VR:** a gear below the mirror's lower-left corner opens the real
  settings: picture size, bit rate, frame rate (30, 60 and the Steam Frame's refresh rates, 72 to
  144) and joystick speed; *Restart stream* applies them without closing the mirror, and *Reset to
  defaults* goes back to 1024 px, 2 Mbit/s, 60 fps.
- **Scroll strips scroll the Android Mirror's phone** (their arrow keys went to the dashboard's
  window: clicks on the mirror go to its touch layer, so the Steam session never saw it clicked).
- **Fixed: joystick scrolling on the mirror stopping** after a click whose release went missing.
- **Android Mirror keeps up with the phone better:** it streams 1024 pixels at 2 Mbit/s (was 1920
  at 8), still sharp in VR; settable in `~/.config/phone.conf`.
- **Android Mirror: the joystick scrolls the phone** while the laser rests on it. SteamVR
  doesn't hand the joystick to the click layer, so it's read from the controller model's
  thumbstick, the way Arrow Pad reads the grips.
- **An upright window docked in the dashboard has a standard window's height** (the upright
  mirror came out over 2 m tall unless you floated it).
- **Fixed: laser clicks on the upright Android Mirror landed at its left edge.** The Steam session
  maps the laser wrongly on a window narrower than its screen. Now a see-through layer over the
  mirror (a dashboard patch) takes the laser, and `phone-touch` sends your presses, drags and
  long-presses to the phone as touches through a second, control-only scrcpy server, so they land
  where you aim, upright or sideways, curved or flat. The mirror window is now titled
  "Android Mirror" (the patches recognise it by that).
- **Turning the phone resizes the mirror at once** (was about a second later): phone-fit and the
  dashboard patch check 20 times a second, and the patch no longer waits for the shape to settle.
- **Android Mirror starts upright at a sensible size** (0.8 m tall), and turning the phone just
  turns the window (0.8 m long side either way): SteamVR starts every floating window as wide as a
  standard one and keeps that width, so the upright phone came up over 2 m tall. The dashboard
  patch now sets the panel height through the dashboard's own override (scaling the window was
  ignored).
- **Fixed: scroll strips the wrong length after a window changed shape** (the phone mirror turned):
  they now read the window's current size from its overlay, not the dashboard's stale copy.
- **Grab guard also hears keys that skip the input devices** (faked by an X program, or typed
  through libei like Full Keyboard), so its log can name where a stray Right Ctrl came from.
- **Grab guard** (new, System): desktop mode takes every key and click after a Right Ctrl press,
  and other windows (this installer too) just stop responding. Grab guard notices, shows a
  notification saying to tap Right Ctrl once, and logs which device sent it.
- **Screen snip from Steam's "+" menu works:** Steam starts it as a game, and the selection window
  then took no laser input; it now starts itself again as a plain program, like Arrow Pad's key.
- **The installer window records a freeze:** if it stops responding for 10 s, where it was stuck
  goes to `~/.local/state/frame-tweaks/logs/gui-hang-*.log`. A status check can no longer hang
  for good (1 minute limit), and Lock now no longer waits on the wallet.
- **New Accessibility group** in the installer window: Dictation, whisper-frame, Arrow Pad, Screen
  snip and Screen reader moved there from Convenience.
- **Android Mirror: no more black bars beside an upright phone.** The window has to fit inside
  the 1920×1080 screen (485×1080 upright), or the Steam session shows it as 1920×1080 anyway;
  upright and sideways now come out about the same size in VR.
- **Android Mirror reconnects by itself** when the wireless connection dies (e.g. after the phone
  switches profile or address), instead of showing a frozen picture: it checks the phone answers
  every 5 s and reconnects at its current address.
- **Scroll strips sit a little behind the window** (3 cm), so SteamVR's own buttons at the
  window's edge, like Enter Gamepad Mode above it, draw in front instead of through the top strip.
- **Fixed: Copy image didn't paste** (e.g. into OnlyOffice). The Shared clipboard tweak's
  clipboard-sync shares text only and put the last text back over a copied image a moment later;
  it's now built with a small patch that leaves a clipboard without text alone, and starting it
  stops any copy left over from a restarted desktop (two were running). Copy image now also
  offers PNG, BMP and HTML, so more apps accept it.
- **Narration panel: Collapse on both sides.** An icon-only Collapse at the bottom left, besides
  the one at the right; Expand comes back with the icon you used in place, so it can tuck away
  toward either side. Copy image, Copy text and Paste are centred.
- **Fixed: a static-like flicker over Collapse** while the panel changed size (the old picture
  was briefly stretched to the new size).
- **Fixed: the narration panel's image disappeared** after Show text (and for a later snip).
- **No Steam flash after a snip:** when the shown window closes, Back to the previous window now
  makes the dashboard's own choice of what to show next, so it goes straight back to the desktop
  (or wherever the snip came from).
- **Collapse keeps its icon in place:** the icon is on the right of the button, and collapsing or
  expanding keeps it exactly where it was.
- **Screen snip narration: Show text / Show image and Copy image.** The panel shows the snip's
  image or the text read from it; Copy image sits beside Copy text; Close and Collapse swapped,
  Collapse has a large icon, and the collapsed panel is just an Expand icon.
- **Screen snip narration: Copy text and Paste.** Copy puts the text being read on the clipboard;
  Paste reads the clipboard's text instead (shown in place of the snip). The panel's buttons are on
  two rows, so they no longer overlap on narrow panels.
- **Screen snip narration: one panel, and Collapse / Expand.** Narrating another snip while the
  panel is open reads it there, in place; Collapse shrinks the panel to an Expand button (reading
  carries on), keeping its top edge where it was.
- **Screen snip narration: Pause / Resume**, and the panel sits relative to the dashboard (it
  starts beside Arrow Pad, under the dashboard bar, follows the dashboard, and remembers where you
  drag it).
- **Screen snip: the narration panel is its own VR panel** (drawn like Arrow Pad and Full Keyboard)
  instead of a window: a compact size, no place in the dashboard (no more flicker with Back to the
  previous window), movable by its top bar.
- **Scroll strips follow SteamVR's Camera Color Tint** (their border, knob and pressed colour use its
  hue, and change when you change it).
- **Screen snip: Narrate pops out and has a speed control.** Narrate opens a small window with the
  snip and its controls (Stop / Again, speed, Close) and gives VR back; the speed (0.75x to 2x,
  under the Narrate button) is remembered and applies at once.
- **Scroll strips work like joysticks:** press, drag away from that point to scroll (farther =
  faster, back past it reverses), let go to stop; the strip shows where you pressed. They scroll
  with arrow keys everywhere, the desktop included (its Remote Desktop portal accepted wheel steps
  but nothing scrolled, so it's no longer used and its saved permission is removed).
- **Scroll strips scroll (for real this time).** In VR the Steam session takes pointer input only
  from the lasers, so injected mouse wheels never arrived. The desktop now scrolls with real wheel
  steps through its own Remote Desktop portal (KDE asks once), other windows with arrow keys /
  PgUp-PgDn. The top strip bends with curved windows.
- **Scroll strips for the window docked in the dashboard** (the desktop): strips now hang from each
  window panel's edge anchors, drawn by a component of their own, so docked and floating windows
  both get them.
- **Scroll strips scroll now.** ydotool's virtual wheel never reached app windows; the strips now
  send wheel clicks through XTest on the Steam session's display. A drag also ends if the laser's
  release goes missing.
- **Arrow Pad:** Save and Redo swapped places on the Tools layer.
- **Scroll strips: fixed size, place and the Steam bar.** They were sized from the window's scaled
  measurements (about 2.7x too big and far out) and used large page elements, which made the
  dashboard draw the Steam bar too big. Now real-world sizes (thickness 2.5 / 4 / 6 cm) and small
  page elements.
- **Arrow Pad: keys keep their places across layers.** Tools is top-left and Esc at the end of the
  second row; Tools, Esc, Fn, the modifiers, R/M and the clipboard keys sit in the same spot on
  the main, Fn and Tools layers (the Tools-only keys take the arrow and navigation keys' places).
- **Scroll strips** (new, VR windows): big strips beside each floating window (right and top by
  default) to drag-scroll with the laser, or tap near an end to page. They scroll the window you
  last clicked. Side and thickness in the row's ⚙ Settings. VR dashboard patching gained patch
  settings (`~/.config/frame-tweaks/NAME.json`) and page-to-service calls (`sftScroll`).
- **Fixed: Arrow Pad and the installer could switch the desktop into input-grab mode.** Their
  stuck-key cleanup pressed Right Ctrl, which in the nested desktop toggles KWin's input grab
  ("Press right control to ungrab input"), so windows and clicks behaved oddly after Arrow Pad
  started or was reinstalled. Right Ctrl is no longer pressed.
- **Arrow Pad: Unstick key** (Tools layer, replaces PrtSc there): when the desktop acts as if
  Shift, Ctrl, Alt or Super is held, it presses and releases each.
- **Speech engine (helper, new): the Screen reader's Orca can speak.** SteamOS has speech-dispatcher
  and its espeak-ng module but not espeak-ng, so Orca was silent. The espeak-ng inside Piper's
  download is now wired into speech-dispatcher (a user `speechd.conf`, restored on uninstall).
  Piper and its voice moved here from Screen snip; Screen snip and Screen reader depend on it.
- **Back to the previous window** also covers closing: when the window the dashboard shows is
  closed (a cancelled Screen snip, say), it goes back to the window before it instead of Steam.
- **Screen snip: crop handles.** Adjust the rectangle by its corners and edges, or drag it to move
  it, before choosing Copy, Save, Copy text or Narrate.
- **Screen snip** (new): select a rectangle of the window you're using, then Copy, Save, Copy
  text (Tesseract OCR) or Narrate (reads it aloud with Piper, offline). Works on the desktop and
  on floated VR windows.
- **Arrow Pad: Tools layer.** A Tools key (where Dictation was) opens a layer with Snip,
  Dictation, Launcher, Undo/Redo, Find, Save, Cut/Copy/Paste/All and more; tap it again to go back.
- **Apply changes is dimmed when there's nothing to change** (its tooltip lists what it would
  install or remove). Only real changes count: a ticked tweak that's installed with a warning is
  no longer reinstalled by Apply; use its ↻ button.
- **Pick up when floating:** the click that puts the window down could land on Return to
  Dashboard (the laser stays on that button) and dock it again; that's now ignored while you hold
  the window and for 1.5 s after. Light clicks put it down reliably (smaller trigger movement
  counts, checked more often, and any click on the dashboard page counts).
- **Pick up when floating** (new, VR windows): "Float in World" also picks the window up for
  placing, as grabbing its bar does; your next click, or letting go of the trigger you're still
  holding, puts it down. One click instead of two.
- **Android Mirror in VR takes the phone's shape and follows its rotation** (`phone-fit`): no
  more wide black bars beside a phone held upright. The Steam session makes app windows
  1920×1080, but keeps a window that declares a fixed size, so the mirror window is sized to the
  phone screen's shape that scrcpy reports, and resized when the phone rotates.
- **Back to the previous window** waits 2.5 s (was 1 s), and installing a VR windows tweak waits
  for its patch to be active before showing its status (it showed "not patched yet").
- **Signal hardening is now "Signal: key in the wallet"**, which is what's left of it: Password
  first and Close after are set in Wallet apps.
- **New VR windows group** in the installer window, with **Back to the previous window** (new):
  after you float the window the dashboard is showing out into the world, the dashboard goes
  back to the window it showed before (after 1 s) instead of an empty space. Tick or untick it
  to switch it on or off. **Curved world windows** moved into the group. Both are small patches
  run by a shared helper, **VR dashboard patching** (it took over `sft-curvature`'s DevTools-port
  setup; installing either tweak moves an existing setup over). Each patch is switched off
  by itself if a SteamVR update changes the dashboard code it relies on.
- **Wallet apps explains why** (a headset without a password can still keep sensitive apps
  behind the wallet's) and **shows the wallet's state** at the top: open or locked, for how long,
  when it locks by itself, with a Lock now / Unlock button. `wallet-unlock --info` reports it.
- **Signal uses the standard Wallet apps protections; Signal guard is retired.** Its two jobs
  are now Password first and a Close-after timer, like any app's (15 minutes, or your Signal
  guard setting, carried over). Its headset-off option is now **Headset off**, for any app with
  a timer. Reinstall the Signal tweak (↻) to switch over.
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
