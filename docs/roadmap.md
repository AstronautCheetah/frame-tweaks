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
- [x] **`./install.sh debug-info`** and a **🐞 Report a problem** button (`./install.sh report`):
  it saves the report and opens the bug form with the version filled in. The report: versions, status, recent
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
- [ ] **SteamOS kernel 6.18 → 7.2.** Reported: the Steam Frame OS main staging branch (mostly
  used by Valve) moved from Linux 6.18 to 7.2, four kernel releases on (6.19, 7.0, 7.1, 7.2;
  Linux's major number changes by count, not by compatibility). Before it reaches the stable
  channel, review what the tweaks take from the kernel: `/dev/uinput` and its permissions
  (ydotool, and the tweaks that type or click through it), input devices and evdev events, the GPU and
  display paths SteamVR and KWin's software cursor use, Wi-Fi and WireGuard (NordVPN), and adb
  over USB and Wi-Fi. Then on that build: `./install.sh check-system`, `dev/test-tweaks.sh`,
  and each tweak's own checks in the headset.
- [ ] **On 2026-10-20: a newer Ubuntu for CI.** The workflows (`ci.yml`, `release.yml`,
  `upstream.yml`) name `ubuntu-24.04` rather than `ubuntu-latest`, so a new Ubuntu comes in
  when we try it. Move them to the newest image `ubuntu-latest` points to then: change one
  workflow, check its run (shellcheck, Python, Qt offscreen tests, AppStream validation), then
  the others.

## Packaging and UX
- [x] **AppStream metainfo,** a reverse-DNS desktop ID and multi-size icons for the installer
  (needed for a Flatpak source later). *(ProtonUp-Qt)*
- [x] **Controller navigation** in the installer window beyond A/B/Y: D-pad/stick moves focus.
  *(ProtonUp-Qt)*
- [x] **Translations** of the installer window, the installer's messages and the tweaks' programs
  (gettext `.po` files, locale/README.md; Latin American Spanish first). Still to come: a
  translation platform (Weblate) once there are outside translators. *(Decky, ProtonUp-Qt)*
- [ ] **Screen snip: text recognition (OCR) in more languages.** Today it reads English only:
  Homebrew's Tesseract brings just `eng.traineddata`, and frame-snip doesn't pass `-l`. Plan:
  - **Data:** Tesseract's `tessdata_fast` models (a few MB each; Apache-2.0), one file per
    language, from a pinned commit of github.com/tesseract-ocr/tessdata_fast with each file's
    SHA256 in `packs/original/snip/ocr-languages.tsv`, built by a `dev/ocr-languages.py` (as
    `dev/speech-voices.py` builds the voices list), and copied to the mirror release like other
    pinned downloads.
  - **Where:** `~/.local/share/frame-tweaks/tessdata/` (English copied in from Homebrew's), passed
    with `--tessdata-dir`; nothing under Homebrew is changed.
  - **Which:** a "Text recognition" setting on Screen snip + Narrate's ⚙ (window and VR panel):
    English plus the Frame Tweaks language by default (es_419 → `eng+spa`), up to three in all
    (each one more slows recognition and can lower accuracy). A table maps our language codes to
    Tesseract's (`spa`, `por`, `deu`, `fra`, `chi_sim`, `jpn`, …).
  - **Getting them:** Apply downloads the chosen ones (checked), like Narrate's voices; a language
    without its file falls back to English with a message, never fails the snip.
  - **Narrate:** suggest the matching voice when the recognised language isn't the voice's.
  - **Tests:** the list's checksums and URLs, the code table, the `tesseract` command line built.
- [ ] **Arrow Pad: a key's tooltip on a long hover.** When the laser rests on a key or toolbar
  button for 5 seconds or more, show what it does (the tooltip it already has: "Right click: your
  next click becomes a right click", "Pin: stop accidental moves"). Desktop mode shows Qt's
  tooltips on hover already; the VR panel doesn't, since it's a picture of the pad (vroverlay.py),
  so it needs drawing in the panel or as a small overlay beside it, and hiding when the laser moves.

## New tweak ideas
- [ ] **Screen reader** (set aside for now): Orca autostarting in the desktop session. *(Jovian-NixOS)*
- [ ] **Memory caps** (set aside for now) for heavy apps (Whisper, VSCodium, Android Mirror) with user-level systemd
  limits, so one app can't freeze the headset. *(Jovian-NixOS)*

## Community
- [ ] **A code of conduct,** once there are regular outside contributors.

## Not adopting
- A root service, a channel of pull-request builds, updates that reset the checkout
  (`git reset --hard`), and root-only tweaks (SDWEAK, Btrfs, pacman with read-only off): each
  fits other projects, but not a home-folder-only installer.
