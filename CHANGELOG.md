# Changelog

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
