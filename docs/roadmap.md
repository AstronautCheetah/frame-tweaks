# Roadmap

Ideas from comparing Frame Tweaks with maintained SteamOS projects: Decky Loader, EmuDeck,
ProtonUp-Qt, Jovian-NixOS and denis-g's optimization guide (reviewed 2026-10-07; local clones in
the gitignored `references/` folder). Where we're already ahead: a security page with a
per-tweak change list, pinned checksums for upstream downloads, an install/uninstall test, and
issue forms.

## Reliability
- [ ] **Release tags:** skip pre-release tags (`v1.2.0-rc1`) when picking the newest release;
  today `sort -V` ranks them above `v1.2.0`. Optional opt-in beta channel. *(Decky, EmuDeck)*
- [ ] **One run at a time:** a lock so the installer window and the terminal can't install at
  once. *(EmuDeck)*
- [ ] **Backups:** copy any user file a tweak edits (Firefox `user.js`, Signal `config.json`,
  `kwalletrc`) before changing it, and restore it on uninstall. *(EmuDeck)*
- [ ] **Migrations:** record each tweak's installed version; `update` runs a tweak's `migrate`
  step when it changed. *(EmuDeck)*
- [ ] **Hold and roll back:** freeze a tweak so `update` skips it; `update --to vX.Y.Z`. *(Decky)*
- [ ] **Locked-down services:** systemd sandboxing (`ProtectSystem=strict`, `PrivateTmp`, …) on
  our user services where it doesn't break them. *(Jovian-NixOS)*

## Support and diagnostics
- [ ] **Logs:** keep the last two runs' logs in `~/.local/state/frame-tweaks/`. *(EmuDeck)*
- [ ] **`./install.sh debug-info`** and a "Save diagnostics" button: versions, status, recent
  logs, with user names and paths removed, zipped for a bug report; the bug form asks for it.
  *(Decky, EmuDeck)*
- [ ] **Crash dialog** in the installer window with the error and a "copy for bug report"
  button; single-instance lock. *(ProtonUp-Qt)*
- [ ] **Rate limits:** update hints say "GitHub limit reached, try later" instead of failing
  silently; cache the last answer. *(ProtonUp-Qt)*
- [ ] **README "Common issues"** section; per-tweak callouts: survives updates? how to undo?
  *(Decky, optimization guide)*

## Engineering
- [ ] **Unit tests** (pytest, offscreen Qt) for the installer window's logic: versions, status
  parsing, update checks. *(ProtonUp-Qt)*
- [ ] **Release workflow:** a manual GitHub Action that bumps the version, tags, and drafts
  release notes from the changelog. *(Decky)*
- [ ] **Generated tables:** README and SECURITY tables built from per-tweak metadata so they
  can't drift. *(Jovian-NixOS)*
- [ ] **SteamOS drift check** run on the device after updates: dashboard markers, paths and
  services the tweaks rely on. *(Jovian-NixOS)*
- [ ] **CI actions pinned** to commit SHAs. *(Jovian-NixOS)*

## Packaging and UX
- [ ] **AppStream metainfo,** a reverse-DNS desktop ID and multi-size icons for the installer
  (needed for a Flatpak source later). *(ProtonUp-Qt)*
- [ ] **Controller navigation** in the installer window beyond A/B/Y: D-pad/stick moves focus.
  *(ProtonUp-Qt)*
- [ ] **Translations** of the installer window (Qt `tr()` + a translation platform). *(Decky,
  ProtonUp-Qt)*

## New tweak ideas
- [ ] **Screen reader:** Orca autostarting in the desktop session. *(Jovian-NixOS)*
- [ ] **Memory caps** for heavy apps (Whisper, VSCodium, Android Mirror) with user-level systemd
  limits, so one app can't freeze the headset. *(Jovian-NixOS)*

## Not adopting
- Decky's root service and PR-build "testing" channel, EmuDeck's `git reset --hard` updates,
  the guide's root-only tweaks (SDWEAK, Btrfs, pacman with read-only off).
- Jovian-NixOS doesn't accept contributions written largely with AI help; don't send it ours.
