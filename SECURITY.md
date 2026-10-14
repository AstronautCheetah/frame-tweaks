# Security notes

Several tweaks handle secrets. This page says what they touch and what they do and don't
protect against.

| Tweak | Touches | Notes |
|---|---|---|
| wallet | KDE wallet (`kwalletd6`/`ksecretd`) | `wallet-unlock` derives the wallet key (PBKDF2-SHA512, as kwallet-pam does) and hands it to `ksecretd` over D-Bus; the password and key never appear on a command line or on disk. |
| wallet (`gh`) | GitHub CLI token | Moved from `~/.config/gh/hosts.yml` (plain text) into the wallet. |
| signal | Signal's database key | Stored in the wallet (Electron safeStorage, `v11`). Signal's data is only as safe as the wallet password. |
| nordvpn | NordVPN access token, WireGuard private key | The token is used once and never stored. The private key lives in root-only NetworkManager files and `~/.config/nordvpn-wg/private_key` (mode 600). That file is the one plain-text secret here: adding locations must work without unlocking the wallet. It only lets someone use your NordVPN account, not read your traffic. |
| adb-scrcpy | adb pairing keys (`~/.android/adbkey`) | adb's own plain files (mode 600), as on any computer. While the phone has wireless debugging on, they let a program running as you control it. |
| firefox | Firefox prefs only | No access to saved logins. Set Firefox's **Primary Password** to encrypt them. |

## What each tweak changes on your system

Everything lives in your home folder unless the table says otherwise. Removing a tweak
(`./install.sh uninstall <id>`) undoes the changes listed and keeps your settings and data.

| Tweak | Files and services | Unusual access (why) |
|---|---|---|
<!-- generated:security (dev/gen-docs.py, from each tweak's meta) -->
| dictation | `~/.local/bin/dictate`, `~/.config/frame-tweaks/dictate.conf`, Whisper model in `~/.local/share/whisper`; Homebrew `wl-clipboard` | Microphone while recording; types through ydotool |
| whisper-frame | Upstream's own installer (user services `whisper-ptt`, `whisper-panel`), pinned release | Microphone; listens for the headset's Select button |
| arrowpad | `~/.local/bin/arrowpad`, `~/.local/share/arrowpad` (incl. a ~280 MB PyQt6 venv) | Types through ydotool. In VR: a SteamVR overlay; reads each controller's grip position (from its 3D model's state, as Full Keyboard does). **R/M keys grab the pointer on the Steam display (`:0`) for one click** (max 20 s) and replay it with XTEST |
| snip | `frame-snip`, Tesseract (Homebrew), an app-menu entry; Piper comes from the Speech engine helper | Reads the picture of the window you're using (only when you start a snip) |
| screen-reader | One setting in `~/.config/kaccessrc` (its previous value is restored on removal) | Reads what's on screen (accessibility interface) and speaks it |
| full-keyboard | Upstream's own installer into `~/.local/share/framekeyboard`, pinned release | A SteamVR overlay; types through its own input path |
| clipboard | `clipboard-sync` built from source (with a temporary, pinned Rust toolchain), KDE autostart entry | Reads and writes both sessions' clipboards |
| adb-scrcpy | `adb` (Arch Linux ARM, signature-checked) in `~/.local/lib/android-tools`, Homebrew `scrcpy`, `phone` launcher; in VR, two dashboard patches and a control-only scrcpy server on the phone | Network connection to your phone's wireless debugging; pairing keys in `~/.android` (plain files: anyone with your user can use them to reach the phone while it has wireless debugging on). adb's server listens on a socket only you can use (not TCP port 5037) |
| cursor | `~/.config/environment.d/` (one variable for KWin) | – |
| vr-dashboard | `~/.local/share/frame-tweaks/vr-dashboard`, user units `sft-vr-debugger`, `sft-dashboard`, a `steamvr.service` drop-in | **Turns on SteamVR's dashboard DevTools port (`127.0.0.1:8087`) while SteamVR runs** and injects the installed patches into the dashboard. The port has no password: **any program on the Frame (sandboxed Flatpak apps included) can connect while SteamVR runs**, run code in the dashboard, and use what the patches can do (arrow keys through ydotool, taps on a mirrored phone, saving patch settings). It's only on while this helper is installed |
| curvature | One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/curvature.js`), via VR dashboard patching (helper) | Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs |
| float-return | One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/float-return.js`), via VR dashboard patching (helper) | Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs |
| float-grab | One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/float-grab.js`), via VR dashboard patching (helper) | Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs |
| scroll-strips | One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/scroll-strips.js`) via VR dashboard patching (helper); settings in `~/.config/frame-tweaks/scroll-strips.json` | Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs; scrolls with ydotool's arrow keys |
| wallet | `wallet-unlock`, `wallet-launcher`, `wallet-gate`, user service `wallet-lock-sync`, `kwalletrc` setting; rewrites chosen apps' menu entries (originals kept in `~/.local/share/frame-tweaks/launcher-originals`) | Talks to KDE Wallet over D-Bus; **closes KDE's own wallet password prompts** (replaced by its dialog); moves the GitHub CLI token into the wallet |
| signal | Signal's menu entry (Wallet apps: password first, Close-after timer), a Flatpak override for Signal, Signal's `config.json` | Asks for the wallet password first; quits Signal when idle; key in the wallet |
| firefox | Preferences in Firefox's profile (`user.js`) | – |
| nordvpn | `nordvpn-wg`, tray app, KDE autostart entry | **Outside your home folder:** NetworkManager WireGuard connections (via `nmcli`) |
| homebrew | `/home/linuxbrew` | **Needs sudo once** to create that folder |
| memcap | `~/.local/bin/capped`, `~/.config/frame-tweaks/memcap.conf`, a systemd drop-in for VSCodium's Flatpak scope | Starts capped apps in their own systemd scope |
| tools | `~/.local/bin/restart-plasmashell` | – |
| menu-icons | Copies of Breeze icons in `~/.local/share/icons/hicolor` | – |
| ydotool | `ydotool`/`ydotoold` (Arch Linux ARM, signature-checked), user service `ydotoold` | **Writes to `/dev/uinput`** (a virtual keyboard any program you run could use while it's running) |
| speech | Piper and a voice in `~/.local/share/frame-tweaks/speech` (checksum-pinned), `~/.config/speech-dispatcher/speechd.conf` (backed up, restored on uninstall) | None beyond your home folder |
| grab-guard | `grab-guard`, user service `grab-guard`, a log in `~/.local/state/frame-tweaks/logs` | **Reads every keyboard's key presses**, and the Steam session's display's (only to notice Right Ctrl; nothing else is kept) |
| vscodium | Flathub app (`com.vscodium.codium`) | – |
| claude-code | `~/.local/bin/claude` and `~/.local/share/claude` (Anthropic's installer) | Downloads Anthropic's installer over HTTPS |
| claude-desktop | `~/.local/opt/claude-desktop`, `claude-desktop-update`, menu entry | Checks against the SHA256 in Anthropic's apt index |
<!-- /generated:security -->
| Installer window (VR) | – | **Claims the controller's A, B and Y** through SteamVR Input while the laser is over the window |

**Our background services are sandboxed** with systemd's options: no new privileges, a
read-only system and home folder except the folders each one writes, and restricted address
families. `ydotoold` also has a private `/tmp` and no network; `sft-dashboard` may only reach
`localhost`. `wallet-lock-sync` is lighter (it shows the unlock dialog on either desktop): your
home folder, `/run/user` and `/tmp` stay writable. `systemd-analyze --user security <unit>`
shows the result. Upstream services (whisper-frame's) are left as their authors ship them.

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
[wallet/README.md](packs/official/wallet/README.md#kde-6-gotcha-ksecretd-holds-the-wallet)).

**Other people's packs.** Tweaks can come from packs other than the official one
([docs/mods.md](docs/mods.md)). Their scripts run as you, as Frame Tweaks' own do, so a pack in
`~/.local/share/frame-tweaks/packs/` (or `FRAME_TWEAKS_PACKS`) is ignored until you trust it,
and trust covers its files as they were then: if any change, it's ignored again until you
trust it again. Tweaks from them are marked 🧩 with the pack's name, and one can take an
official tweak's place only by declaring `replaces: true` (the window says so). Frame Tweaks
doesn't review or sandbox other people's packs.

**Downloads.**
- **Pinned upstream releases** (Full Keyboard, whisper-frame, the Whisper model): each tweak's
  `pin` file records the exact version and SHA256; the download must match it, so a changed or
  replaced upstream file is refused. **clipboard-sync** is built from a pinned commit with its
  own lock file, using a pinned `rustup-init` (checked against its SHA256) that installs a
  pinned Rust toolchain for the build only. **Python packages** (PyQt6, openvr, jeepney) are
  installed at the exact versions in `lib/python-constraints.txt`. Pins move only in a reviewed
  commit (`dev/check-pins.sh`, `dev/bump-pin.py`); a weekly GitHub check
  (`dev/check-upstream.sh`) reports pinned files that changed or vanished upstream. If one
  does, installs use Frame Tweaks' own copy (this repository's `mirror` release), held to the
  same SHA256, so the copy can't be swapped either.
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
  the moving `main` branch. Tags
  aren't signed yet: `get.sh` trusts GitHub's HTTPS.

Found a problem? Please open a private security advisory on GitHub rather than a public issue.
