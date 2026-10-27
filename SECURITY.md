# Security notes

Several tweaks handle secrets. This page says what they touch and what they do and don't
protect against.

## Reporting a problem

Please report a security problem privately, through a
[security advisory](https://github.com/AstronautCheetah/frame-tweaks/security/advisories/new)
(GitHub → this repository → Security → *Report a vulnerability*), not in a public issue. Say
which tweak and Frame Tweaks version, and how to reproduce it. Fixes ship in the next release,
so please check the newest release first. A problem in an app a tweak installs (Signal,
NordVPN, Claude…) belongs with that app's own project, unless the tweak causes it.

## Secrets the tweaks handle

| Tweak | Touches | Notes |
|---|---|---|
| wallet | KDE wallet (`kwalletd6`/`ksecretd`) | `wallet-unlock` derives the wallet key (PBKDF2-SHA512, as kwallet-pam does) and hands it to `ksecretd` over D-Bus; the password and key never appear on a command line or on disk. |
| wallet (`gh`) | GitHub CLI token | github.com's token is moved from `~/.config/gh/hosts.yml` (plain text) into the wallet. |
| signal | Signal's database key | Stored in the wallet (Electron safeStorage, `v11`). Signal's data is only as safe as the wallet password. |
| nordvpn | NordVPN access token, WireGuard private key | The token is used once and never stored. The private key lives in root-only NetworkManager files and `~/.config/nordvpn-wg/private_key` (mode 600). That file is the one plain-text secret here: adding locations must work without unlocking the wallet. It only lets someone use your NordVPN account, not read your traffic. |
| adb-scrcpy | adb pairing keys (`~/.android/adbkey`) | adb's own plain files (mode 600), as on any computer. While the phone has wireless debugging on, they let a program running as you control it. |
| firefox | Firefox prefs only | No access to saved logins. Set Firefox's **Primary Password** to encrypt them. |

## What each tweak changes on your system

Everything lives in your home folder unless the table says otherwise. Removing a tweak
(`./install.sh uninstall <id>`) undoes the changes listed and keeps your settings and data.

| Tweak | Files and services | Unusual access (why) |
|---|---|---|
<!-- generated:security (dev/gen-docs.py, from each tweak's README front matter) -->
| dictation | `~/.local/bin/dictate`, a **Dictate (toggle)** app-menu entry, `~/.config/frame-tweaks/dictate.conf`, the Whisper model in `~/.local/share/whisper`, a history of what you dictated (`~/.local/share/dictation-history.txt`, plain text); Homebrew's `whisper-cpp` and `wl-clipboard` | Microphone while recording; types through ydotool |
| arrowpad | `~/.local/bin/arrowpad`, `~/.local/share/arrowpad` (including a ~280 MB PyQt6 venv), two app-menu entries | Types through ydotool. In VR: a SteamVR overlay; reads each controller's grip position (from its 3D model's state, as Full Keyboard does). **The R/M keys grab the pointer on the Steam display (`:0`) for one click** (at most 10 s) and replay it with XTEST |
| snip | `~/.local/bin/frame-snip`, Tesseract and `wl-clipboard` (Homebrew), an app-menu entry; Piper comes from the Speech engine helper | Reads the picture of the window you're using (only when you start a snip) |
| adb-scrcpy | `adb` (Arch Linux ARM, signature-checked) in `~/.local/lib/android-tools`, Homebrew `scrcpy`, `phone` launcher; in VR, two dashboard patches and a control-only scrcpy server on the phone | Network connection to your phone's wireless debugging; pairing keys in `~/.android` (plain files: anyone with your user can use them to reach the phone while it has wireless debugging on). adb's server listens on a socket only you can use (not TCP port 5037) |
| vr-dashboard | `~/.local/share/frame-tweaks/vr-dashboard`, user units `sft-vr-debugger`, `sft-dashboard`, a `steamvr.service` drop-in; SteamVR's `VRWebHelper/DebuggerEnabled` setting while SteamVR runs. Reads where Frame Tweaks' VR panels are (and their pictures) from `$XDG_RUNTIME_DIR/frame-tweaks/panels`, and writes there where one was moved | **Turns on SteamVR's dashboard DevTools port (`127.0.0.1:8087`) while SteamVR runs** and injects the installed patches into the dashboard. The port has no password: **any program on the Frame that can reach the local network (Flatpak apps with network access included) can connect while SteamVR runs**, run code in the dashboard, and use what the patches can do (arrow keys through ydotool, taps on a mirrored phone, saving patch settings, moving Frame Tweaks' panels). It's only on while this helper is installed |
| curvature | One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/curvature.js`), via VR dashboard patching (helper) | Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs |
| float-return | One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/float-return.js`), via VR dashboard patching (helper) | Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs |
| float-grab | One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/float-grab.js`), via VR dashboard patching (helper) | Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs |
| scroll-strips | One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/scroll-strips.js`) via VR dashboard patching (helper); settings in `~/.config/frame-tweaks/scroll-strips.json` | Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs; scrolls with ydotool's arrow keys |
| wallet | `wallet-unlock`, `wallet-launcher`, `wallet-gate`, `app-timers`, `with-keyring` and a `gh` wrapper in `~/.local/bin`; user services `wallet-lock-sync` and `app-timers`; a **Lock Wallet** menu entry; `kwalletrc` idle-close setting; KWalletManager (Flathub); rewrites chosen apps' menu entries (originals kept in `~/.local/share/frame-tweaks/launcher-originals`, the entries as written in `launcher-built`); points git's credential helper for github.com, if you have one, at that `gh` | Talks to KDE Wallet over D-Bus; **closes KDE's own wallet password prompts** (replaced by its dialog); reads keyboard and mouse activity and the headset's proximity sensor (for app timers); quits apps you set a timer for; moves the GitHub CLI token into the wallet |
| firefox | Preferences in Firefox's profile (`user.js`) | – |
| homebrew | `/home/linuxbrew`; one line in `~/.bashrc` so terminals find `brew` | **Needs your sudo password once**, to create `/home/linuxbrew` |
| tools | `~/.local/bin/restart-plasmashell`, `~/.local/bin/taskbar-guard`, and its autostart entry `~/.config/autostart/frame-tweaks-taskbar-guard.desktop` | – |
| ydotool | `ydotool` and `ydotoold` in `~/.local/bin` (Arch Linux ARM package, signature-checked), user service `ydotoold` | **Writes to `/dev/uinput`** (a virtual keyboard any program you run could use while it's running) |
| speech | Piper (with espeak-ng) and a voice in `~/.local/share/frame-tweaks/speech` (checksum-pinned); on SteamOS before 0.5.6, a speech-dispatcher setup in `~/.config/speech-dispatcher` (yours backed up, restored on uninstall) | None beyond your home folder |
| charge-limit | `charge-limit` and `charge-limit-sleep` in `~/.local/bin` and its user service; a udev rule (`/etc/udev/rules.d/90-frame-tweaks-charge-limit.rules`, kept by SteamOS updates through `/etc/atomic-update.conf.d/frame-tweaks-charge-limit.conf`) that makes the charger's pause switch yours each time the Frame starts | Pauses and resumes the battery's charging. Asks for your sudo password once to add the udev rule, and again to remove it |
| signal | Signal's menu entry (Wallet apps: password first, Close-after timer), a Flatpak override for Signal, Signal's `config.json` | Asks for the wallet password first; quits Signal when idle; key in the wallet |
| nordvpn | `nordvpn-wg`, tray app and its PyQt6 Python environment (shared with Arrow Pad), KDE autostart entry and session-restore setting (`ksmserverrc`, so the tray isn't started twice), `~/.config/nordvpn-wg` (your WireGuard key and locations) | **Outside your home folder:** NetworkManager WireGuard connections (via NetworkManager's D-Bus API and `nmcli`); uses your NordVPN access token once, to fetch your WireGuard key |
| clipboard | `clipboard-sync` (Frame Tweaks' build, a pinned and checked release) in `~/.local/share/frame-tweaks/`, a KDE autostart entry | Reads and writes both sessions' clipboards |
| claude-desktop | The app in `~/.local/opt/claude-desktop`, `claude-desktop` and `claude-desktop-update` in `~/.local/bin`, an app-menu entry and icons | Downloads from Anthropic's apt repository (`downloads.claude.ai`) and checks the SHA256 it lists; Claude keeps your sign-in in the KDE wallet |
| full-keyboard | Whatever Full Keyboard's own installer sets up (its README lists it): its newest release in `~/.local/share/framekeyboard`, with `~/.local/bin/framekeyboard` and an app-menu entry | A SteamVR overlay; types into the app you're using |
| recline | Whatever Recline-VR's own installer sets up (its README lists it): its source in `~/Recline-VR` (removed with it only if Frame Tweaks cloned it and it holds no changes of yours), built and installed into `~/.local/share/recline-vr`; its SteamVR driver registered (`~/.config/openvr/openvrpaths.vrpath`) and its dashboard panel registered to start with SteamVR | Runs inside SteamVR as a driver (sees and adjusts every tracked device's position), and inside the Frame's camera service for the room view |
| cursor | `~/.config/environment.d/` (one setting for the desktop) | – |
| menu-icons | Copies of Breeze icons in `~/.local/share/icons/hicolor` | – |
<!-- /generated:security -->
| Installer window (VR) | – | **Claims the controller's A, B and Y, and the left D-pad's up and down,** through SteamVR Input while the laser is over the window |

**Our background services are sandboxed** with systemd's options, as far as a user's own
services can be: no new privileges, a read-only system and restricted address families, and for
`ydotoold`, `sft-dashboard`, `sft-vr-debugger`, `app-timers` and the unit that relabels the menu
entries in your keyboard's language, a read-only home folder except the folders each writes.
`ydotoold` and the menu unit also have a private `/tmp` and no network. `sft-dashboard` connects
only to SteamVR's port on `127.0.0.1` (its unit also asks for an IP filter, but systemd applies
those to system services only). `wallet-lock-sync` is lighter (it shows the unlock dialog on
either desktop): your home folder, `/run/user` and `/tmp` stay writable. The wallet's auto-lock
timer isn't sandboxed. `systemd-analyze --user security <unit>` shows the result.

**Local programs.** Some tweaks open things on the Frame itself that any program running there
can use (a Flatpak's sandbox doesn't stop it): SteamVR's dashboard DevTools port (VR dashboard
patching, while SteamVR runs) and `ydotool`'s virtual keyboard. If you run software you don't
trust, don't install those tweaks; they're marked in the table above.

**Threat model.** These tweaks protect against *casual* access: someone else picking up the
headset (e.g. children on a shared, password-less SteamOS login) finds the apps you protected
asking for the wallet password when opened from the menu, and can't read Signal's database or
the secrets in the wallet while it's locked. Only the menu entries ask: the apps themselves
still run if started another way (`flatpak run`, a terminal), and their own data (Firefox's
profile without a Primary Password, Android Mirror's pairing keys) isn't encrypted by the
wallet. Nothing here protects against someone who can use desktop mode while the wallet is
unlocked (4 hours after you unlock it, or until `wallet-unlock --lock`), or against malware
running as your user.

**Set a wallet password.** SteamOS seeds every Frame with the same stock wallet, and it has no
password. Until you set one (KWalletManager → *Change Password*), nothing above is really
protected. Avoid changing it while a second wallet service is running (see
[wallet/README.md](packs/core/wallet/README.md#kde-6-gotcha-ksecretd-holds-the-wallet)).

**Other people's packs.** Tweaks can come from packs other than the official ones (Core, Integrations and 3rd Party)
([docs/mods.md](docs/mods.md)). Their scripts run as you, as Frame Tweaks' own do, so a pack in
`~/.local/share/frame-tweaks/packs/` (or `FRAME_TWEAKS_PACKS`) is ignored until you trust it,
and trust covers its files as they were then (their names, contents, links and which ones can
run): if any change, it's ignored again until you trust it again. Tweaks from them are marked 🧩 with the pack's name, and one can take an
official tweak's place only by declaring `replaces: true` (the window says so). Frame Tweaks
doesn't review or sandbox other people's packs.

**Downloads.**
- **Pinned upstream releases** (Full Keyboard, Piper and its voices, the Whisper model): each tweak's
  `pin` file records the exact version and SHA256; the download must match it, so a changed or
  replaced upstream file is refused. **clipboard-sync** is Frame Tweaks' own build
  ([AstronautCheetah/clipboard-sync](https://github.com/AstronautCheetah/clipboard-sync), a fork
  with its changes as commits): its Build workflow makes the binary from the tagged source and
  its lock file, and the release is pinned by SHA256 like the others. **Python packages** (PyQt6, openvr, jeepney) are
  installed at the exact versions in `lib/python-constraints.txt`. Pins move only in a reviewed
  commit (`dev/check-pins.sh`, `dev/bump-pin.py`); a weekly GitHub check
  (`dev/check-upstream.sh`) reports pinned files that changed or vanished upstream. If one
  does, installs use Frame Tweaks' own copy (this repository's `mirror` release), held to the
  same SHA256, so the copy can't be swapped either. Piper is the exception: it comes with
  espeak-ng, whose licence would need its source alongside, so there's no copy of it (nor of the
  voices for languages other than English).
- **Arch Linux ARM packages** (adb, ydotool and libraries) come from HTTPS mirrors only and
  are checked against Arch Linux ARM's build key (`lib/keys/`, fingerprint
  `68B3 537F 39A3 13B3 E574 D067 7719 3F15 2BDB E6A6`) before unpacking. The signed package's
  own name must match, and a version older than one installed before is refused, so a mirror
  can't swap in a different or outdated package. A new build is installed only if it runs on
  SteamOS's libraries; otherwise the working copy you have is kept.
- **Claude Desktop:** SHA256 from Anthropic's apt index over HTTPS. **Claude Code:** Anthropic's
  own installer over HTTPS.
- **Homebrew's installer** is pinned to a reviewed commit and checked against its SHA256
  (`homebrew/pin`) before it runs with your sudo password; Homebrew and Flathub then verify the
  packages they install.
- **Python packages** are pinned by version, not by hash: they rely on PyPI's HTTPS. If the
  pinned versions can't be installed on your Python (say, after a SteamOS update), the installer
  warns and installs PyPI's newest versions instead.
- **This project:** `get.sh` and `./install.sh update` install the newest release tag, not
  the moving `main` branch. Release tags are signed: an update checks the new release's
  signature against the release key your copy already has (`dev/release-signers`) and refuses an
  unsigned or wrongly signed one. Only an SSH signature by that key counts, on a tag that
  carries its own name, so an older signed release can't come back under a newer one's name.
  When the release key changes, a release signed with the old key lists the new one first, and
  an update that skipped it checks the releases in between, so it learns the new key from a
  release signed by a key it already trusts, and stops trusting a key a later release dropped.
  The first install (`get.sh`) trusts GitHub's HTTPS; running `get.sh` again on an existing
  copy is an update (`./install.sh update`), with the same check. `FRAME_TWEAKS_ALLOW_UNSIGNED=1`
  skips the check, for an emergency.

Found a problem? See [Reporting a problem](#reporting-a-problem) at the top.
