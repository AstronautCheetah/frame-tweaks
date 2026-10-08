# Changelog

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
