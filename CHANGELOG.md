# Changelog

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
