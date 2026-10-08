# Changelog

## 0.2.5 (2026-10-07)
- Repo rules for agents (CLAUDE.md): no attribution trailers on commits or PRs, enforced by git
  hooks (`tools/install-hooks.sh`) and CI; instructions arriving through an agent harness's system
  channel are reported to the owner, with a register of the ones already decided. The existing
  `Co-Authored-By`/`Claude-Session` lines were removed from the history (rewritten, tags moved).
- ydotool's details page lists what uses it (Dictation, Arrow Pad) and how.
- Installer window: the floating window's close button failed while a details window was open
  (it was a modal dialog, which blocks closing the main window, and in VR it opened in the
  dashboard where you couldn't see it). Fixed by 0.2.4's in-window details page.

## 0.2.4 (2026-10-07)
- New: **Curved world windows** (`curvature`). Windows you float into the world start curved;
  Toggle Curvature still works per window. A small SteamVR dashboard patch, approach from
  steam-frame-nix. Restart SteamVR once after installing.
- New: **Claude Code (command line)**, above Claude Desktop, via Anthropic's native installer
  (an existing install, e.g. Homebrew's, is left alone).
- Arrow Pad VR: no more flicker. Two overlays, double-buffered: a new image loads into the
  hidden one, which is shown before the old one is hidden (reloading the visible overlay blanked
  it briefly on every hover change). Identical images aren't re-sent, laser moves no longer
  trigger redraws, and sub-millimetre wobble of the dashboard's pose is ignored. CPU ~7% → ~1%.
- Installer window: details and the "remove tweaks?" question open inside the window instead of
  as separate windows (in VR, a new window opened in the dashboard, away from a world-floating
  installer). Rows with a known problem show a short note; the details page says more and checks
  whether upstream has released a newer version since (whisper-frame 0.2.0: performance).

## 0.2.3 (2026-10-07)
- Arrow Pad VR: fix the invisible panel that still caught the laser. The overlay event loop
  never ended (pyopenvr returns `(result, event)`, always truthy), so the pad never drew and
  burned a full CPU core. Also: textures go to SteamVR as PNG files instead of `SetOverlayRaw`,
  which never displayed on the Frame, and a 2.5 MB raw upload in testing crashed vrcompositor
  (SIGBUS). Texture size and update rate are capped, it redraws only on visible changes, polls
  at ~45 Hz, and disconnects from SteamVR cleanly on exit.

## 0.2.2 (2026-10-07)
- Arrow Pad VR: placed and anchored like Full Keyboard: just below Steam's dashboard (main
  panel, else the dashboard bar), top edge 6 cm below, 24 cm toward you, 50° from upright, and
  it follows the dashboard. It used to stay at a fixed spot in the room, so re-centring the play
  space left it behind (it was 3 m away, above your head). Default width 0.55 m.

## 0.2.1 (2026-10-07)
- Arrow Pad VR: fix the overlay flying away (drag moved it by laser coordinates on the moving
  panel, which ran away; it now follows the controller rigidly, like Full Keyboard's grab). A
  panel more than 4 m away comes back; launching again recenters it.
- Installer window: a ▶ button per tweak (Open, Dictate, Unlock, Restart, Tray, …) from each
  tweak's `run.sh`; Help where there's nothing to launch.

## 0.2.0 (2026-10-07)
- Installer window: tweaks grouped by category (Convenience → Privacy & security → System →
  Developer); click any row (or ⓘ) for details: what it is, why it's included, who made it,
  source, status and its README; status checks run in the background (the window used to freeze
  for ~1 s, longer under load); checkboxes 50% bigger.
- whisper-frame is hidden by default (not removed) while its window mic costs VR performance;
  unhiding it is remembered.
- NordVPN status no longer makes a network call.
- components.tsv gains category, author, why and flags columns.

## 0.1.9 (2026-10-07)
- Arrow Pad VR mode is now a **native SteamVR overlay** (like Full Keyboard): keys reach the app
  you were using (a floating window took focus when clicked), haptics go to the pointing
  controller, Reset/−/+ place and size it in metres, drag to move, Pin to lock.

## 0.1.8 (2026-10-07)
- whisper-frame: window mic **off by default**. It polls SteamVR's compositor ~60x/s per window,
  measured at ~31% of a CPU core (itself + vrwebhelper + vrserver), causing VR jitter.
  Opt in with `WHISPER_FRAME_WINDOW_MIC=1`.
- Installer window: each tweak that comes from another project links to it.
- New **vscodium** tweak (Flathub).

## 0.1.7 (2026-10-07)
- Wallet: fix "correct password refused" for good. The dialog judged success by the Secret
  Service "Locked" flag, which stays True after a pamOpen unlock; it now checks whether
  ksecretd has the wallet open.
- New **whisper-frame** tweak: groffta's Select-button and window-mic dictation, installed from
  upstream releases, with a drop-in that restarts the window mic with SteamVR.
- Dictation shares whisper-frame's model (`ggml-small-q8_0.bin`) and its bundled whisper-cli:
  no duplicate models or engines (removes the old `small.en`/`base.en` models); `DICTATE_LANG`.

## 0.1.6 (2026-10-07)
- Wallet: one unlock route. `wallet-lock-sync` now replaces ksecretd's own password prompt
  (which floats in VR and blocks every other unlock while open) with our dialog on the same
  display; KWalletManager and Claude Desktop are gated like Signal; the 4-hour auto-lock
  restarts whenever the wallet is unlocked, by any route.

## 0.1.5 (2026-10-07)
- New **clipboard** tweak: one clipboard for desktop mode and VR windows (dnut/clipboard-sync
  built from upstream, started with the desktop session; approach from steam-frame-nix).
- Wallet: when an unlock fails because one of KWallet's own prompts is open (it then ignores
  other unlocks), say so instead of "wrong password".
- Arrow Pad haptics: also send SteamVR's direct pulse, which isn't tied to input focus
  (SteamVR Input haptics only reach the focused app, and Steam's dashboard has focus).

## 0.1.4 (2026-10-07)
- New installer window (PyQt6, Full Keyboard style): live status per tweak, Hide/Unhide per
  row, "Show hidden" toggle, removals confirmed separately.
- Arrow Pad: controller haptics via SteamVR Input (hover tick, press click, on the pointing
  hand); VR window renders at 1x with a fixed size, so there are no gaps between keys.
- CREDITS.md with what came from which project and every dependency's license; a Credits
  section in each tweak's README and the main README.

## 0.1.3 (2026-10-07)
- Wallet: fix "password refused". The lock left ksecretd *open but locked*, so the unlock was
  silently ignored and every password looked wrong. Locking now fully closes the wallet in
  ksecretd, unlocking clears a stuck state first, and the installer no longer starts a second
  wallet service in the desktop session.
- Arrow Pad: Full Keyboard style (Graphite theme, icon toolbar), pin, reset position, −/+ size,
  grab-to-move, labels in the keyboard's language (de/fr/es/it), clipboard keys as icons.

## 0.1.2 (2026-10-07)
- Wallet: closing the wallet now really locks it (`wallet-lock-sync` service; kwalletd6's
  close left ksecretd unlocked, so Signal opened without a password). New **Lock Wallet** entry.
- Arrow Pad: **Arrow Pad (VR window)** entry (`--vr`) next to the desktop one (`--desktop`),
  separate instances; taskbar shows the Arrow Pad icon instead of the X11 logo.
- The installer has its own **Steam Frame Tweaks** menu entry (`./install.sh menu`), created on
  every install/update.
- Fix: re-running the wallet installer dropped Signal's idle guard from its launcher.

## 0.1.1 (2026-10-07)
- App-menu icons that Steam's "+" menu can show; Dictate's matches the Arrow Pad 🎤 button.
- Fix duplicate entries in Steam's "+" menu (launcher backups moved out of the applications
  folder; the folder's mtime is bumped so Steam rescans).
- "Phone Mirror" is now "Android Mirror" (a password gate carries over).
- Dictation: no more overlapping recordings or silent-audio hallucinations; double-tap and
  busy protection, 5-minute auto-stop, `dictate --status`. Arrow Pad 🎤 shows transcribing.
- Homebrew is offered and installed when a tweak needs it.
- README: one-line install, CI badge, "Why (on the Frame)" column.
- Installer: dependency parsing fix; removals in the checklist need a separate confirmation,
  and an empty selection never removes anything.

## 0.1.0 (2026-10-07)
First release.
- Installer: graphical checklist, `install` / `uninstall` / `status` / `update` / `list`,
  automatic dependencies, `get.sh` bootstrap and app-menu entry.
- Components: dictation, arrowpad, full-keyboard, cursor, adb-scrcpy, wallet, signal,
  nordvpn, firefox, claude-desktop, tools, ydotool.
