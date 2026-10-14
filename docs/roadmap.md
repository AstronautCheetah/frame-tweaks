# Roadmap

Ideas from comparing Frame Tweaks with maintained SteamOS projects: Decky Loader, EmuDeck,
ProtonUp-Qt, Jovian-NixOS and denis-g's optimization guide (reviewed 2026-10-07), each credited
next to the idea it inspired.

## Reliability
- [x] **Release tags:** skip pre-release tags (`v1.2.0-rc1`) when picking the newest release
  (`sort -V` alone ranks them above `v1.2.0`). Optional opt-in beta channel. *(Decky, EmuDeck)*
- [x] **One run at a time:** a lock so the installer window and the terminal can't install at
  once. *(EmuDeck)*
- [x] **Backups:** copy any user file a tweak edits (Firefox `user.js`, Signal `config.json`,
  `kwalletrc`) before changing it, and restore it on uninstall. *(EmuDeck)*
- [x] **Migrations:** record each tweak's installed version; `update` runs a tweak's `migrate`
  step when it changed. *(EmuDeck)*
- [x] **Hold and roll back:** freeze a tweak so `update` skips it; `update --to vX.Y.Z`. *(Decky)*
- [x] **Locked-down services:** systemd sandboxing (`ProtectSystem=strict`, `PrivateTmp`, …) on
  our user services where it doesn't break them. *(Jovian-NixOS)*

## Support and diagnostics
- [x] **Logs:** keep the last five runs' logs in `~/.local/state/frame-tweaks/`. *(EmuDeck)*
- [x] **`./install.sh debug-info`** and a **Diagnostics** button: versions, status, recent
  logs and services' log lines, with user names and paths removed, in one text file for a bug
  report; the bug form asks for it.
  *(Decky, EmuDeck)*
- [x] **Crash dialog** in the installer window with the error and a "copy for bug report"
  button; single-instance lock. *(ProtonUp-Qt)*
- [ ] **Rate limits:** update hints say "GitHub limit reached, try later" instead of failing
  silently; cache the last answer. *(ProtonUp-Qt)*
- [x] **README "Common issues"** section; per-tweak callouts: survives updates? how to undo?
  *(Decky, optimization guide)*

## Engineering
- [x] **Unit tests** (unittest, offscreen Qt) for the installer window's logic: versions, status
  parsing, update checks. *(ProtonUp-Qt)*
- [x] **Release workflow:** a manual GitHub Action that bumps the version, tags, and drafts
  release notes from the changelog. *(Decky)*
- [x] **Generated tables:** README and SECURITY tables built from per-tweak metadata so they
  can't drift. *(Jovian-NixOS)*
- [x] **SteamOS drift check** run on the device after updates: dashboard markers, paths and
  services the tweaks rely on. *(Jovian-NixOS)*
- [x] **CI actions pinned** to commit SHAs. *(Jovian-NixOS)*

## Packaging and UX
- [x] **AppStream metainfo,** a reverse-DNS desktop ID and multi-size icons for the installer
  (needed for a Flatpak source later). *(ProtonUp-Qt)*
- [x] **Controller navigation** in the installer window beyond A/B/Y: D-pad/stick moves focus.
  *(ProtonUp-Qt)*
- [x] **Translations** of the installer window, the installer's messages and the tweaks' programs
  (gettext `.po` files, locale/README.md; Latin American Spanish first). Still to come: a
  translation platform (Weblate) once there are outside translators. *(Decky, ProtonUp-Qt)*
- [ ] **Arrow Pad: a key's tooltip on a long hover.** When the laser rests on a key or toolbar
  button for 5 seconds or more, show what it does (the tooltip it already has: "Right click: your
  next click becomes a right click", "Pin: stop accidental moves"). Desktop mode shows Qt's
  tooltips on hover already; the VR panel doesn't, since it's a picture of the pad (vroverlay.py),
  so it needs drawing in the panel or as a small overlay beside it, and hiding when the laser moves.

## New tweak ideas
- [ ] **Screen reader** (set aside for now): Orca autostarting in the desktop session. *(Jovian-NixOS)*
- [ ] **Memory caps** (set aside for now) for heavy apps (Whisper, VSCodium, Android Mirror) with user-level systemd
  limits, so one app can't freeze the headset. *(Jovian-NixOS)*

## Not adopting
- A root service, a channel of pull-request builds, updates that reset the checkout
  (`git reset --hard`), and root-only tweaks (SDWEAK, Btrfs, pacman with read-only off): each
  fits other projects, but not a home-folder-only installer.
