# Changelog

## Unreleased

### Security
- **A new install checks the release's signature too:** `get.sh` carries the release key and
  checks the release it downloads before running anything in it, as updates already did; a
  release that fails is removed again. Only `get.sh` itself is now taken on trust.
- **Python packages keep their tested versions:** a failed install of PyQt6, openvr or jeepney is
  tried once more. If PyPI has no build of a tested version for your Python (after a SteamOS
  update, say), only that one is replaced, by the newest that has a build, and the warning names
  it; the others stay as tested. If PyPI can't be reached, a tested version is gone from PyPI, or
  anything else goes wrong, the install stops and says so. Before, any failure (a dropped
  connection, a full disk, a deleted release) dropped every version pin, with a warning that blamed
  your Python.
- **Arch Linux ARM packages (adb, ydotool) are checked more closely:** a package built for another
  kind of processor is refused, even with a valid signature; a first install refuses an adb or
  ydotool older than the version this release was tested with; and the downloads can't be
  redirected to plain HTTP.
- **A new ydotool is used only if it runs:** a build that couldn't load at all (made for another
  processor) counted as working and replaced the ydotool you had, so Dictation and Arrow Pad
  stopped typing. Now it must load and start, or the one you have stays, and the warning says why.
- **Claude Desktop never goes back to an older version by itself:** `claude-desktop-update`
  installs only a version newer than yours, takes Claude Desktop's own entry in Anthropic's list,
  and downloads over HTTPS only, redirects included; the window's update hint offers only what an
  update would install. To go back, run `claude-desktop-update --allow-older`. It used to install
  any version that differed from yours, older ones included, could take another package's entry,
  and followed a redirect to plain HTTP.
- **The bug report removes more, and says exactly what:** it now also replaces GitHub tokens, other
  tokens and keys (64 hex digits, or 44 base64 characters ending in =, such as a NordVPN token or a
  WireGuard key), MAC addresses written with dashes, adb's names for phones, and every phone name
  Android Mirror remembers. Its first line and the 🐞 Report a problem page list exactly what's
  removed. C++ names such as `std::string` no longer come out as `st<ipv6>string`.
- **Android Mirror knows your phone by its adb identity, not just its name:** any device on the
  Wi-Fi can announce your phone's name, and Android Mirror connected to the first one with it. Once
  it has connected to your phone, it now also remembers the phone's adb identity (which stays the
  same when you turn Wireless debugging off and on, or pair the phone again) and the address it
  last connected to. A phone with the same name but another identity isn't taken for yours: Android
  Mirror says so and asks. If more than one device claims to be your phone, it connects to none by
  itself and asks you to choose the address your phone shows (*Developer options → Wireless
  debugging → IP address & Port*). Its README now says what this can't prevent: adb doesn't check
  that the device is the phone you paired, so mirror on a Wi-Fi you trust.
- **Android Mirror's clipboard works both ways:** its README and Shared clipboard's now say that
  with the clipboard shared (the default), the phone can put anything into the Frame's clipboard,
  and Shared clipboard passes it on to the desktop and VR, so a compromised phone could swap what
  you copied for something else. **Share the clipboard with the phone → Not shared** turns it off.
- **Firefox privacy never follows a link in Firefox's own folder:** Firefox's sandbox can write its
  profile, and removing the tweak copied `prefs.js` over `prefs.js.frame-tweaks-bak` even when that
  was a link, so a compromised Firefox could have had it overwrite a file of yours (your `.bashrc`,
  say) outside its sandbox. Now the tweak stops before it changes anything, and says why, when a
  file it reads or writes there is a link or not a plain file, or when the profile `installs.ini`
  names isn't a folder inside Firefox's own. It replaces the files it changes instead of writing
  into them.
- **Your sudo password works only for the step you typed it for:** sudo remembers a password for a
  few minutes, so after Battery charge limit's udev rule or Homebrew's installer, the next tweak in
  the same install (a linked project's installer, another person's pack) could have used it without
  asking. Battery charge limit now adds and removes its rule with one sudo command that doesn't
  remember the password at all, and sudo forgets the password as soon as Homebrew's installer ends,
  and before and after each tweak's script in an install, uninstall, reinstall or update, so each
  one asks for its own.
- **What you dictate is readable only by you:** Dictation's history
  (`~/.local/share/dictation-history.txt`) was created readable by every user of the Frame, and
  only your home folder kept others out. It's now yours alone; an existing one changes at your next
  dictation, or when Dictation is reinstalled or updated. Dictation's log and recordings, Arrow
  Pad's input log and the notes under its VR panel are now yours alone too.
- **Screen snip's narration panel reads only the snips Narrate hands it:** an open panel takes new
  snips over a local socket, and it would read aloud any file it was pointed at, then delete the
  folder that file was in. It now takes only the folders Narrate makes for a snip, never follows a
  link in them, and refuses anything else. The same goes for the picture Copy hands to the
  desktop's clipboard.

### Added
- **Dictation is faster:** Whisper now runs on the Frame's six fast cores, decodes greedily and
  works through only as much of its window as the recording needs: a 3-second clip is text in
  about 0.6 s instead of 1.6, a 10-second one in 1.2 s instead of 3. `DICTATE_BEAM=5` brings the
  beam search back.
- **Dictation: Parakeet engine** (⚙ Settings → Engine, then Apply): NVIDIA's Parakeet TDT 0.6B
  v3 on the CPU, 25 European languages told apart by themselves, about 0.4 s for a 10-second
  sentence when kept loaded. About 800 MB to download, checksum-pinned; Whisper stays the
  default.
- **Dictation: keep the engine loaded** (⚙ Settings, off by default): text sooner, for memory in
  use all the time (Whisper about 600 MB, Parakeet about 1.3 GB). The engine is the first thing
  stopped if memory runs out.
- **Dictation: voice activity detection** (on; ⚙ Settings turns it off): Silero's keeps pauses
  and room noise in a recording from Whisper, so they don't turn into invented words. It reads
  only the recording: the mic is still open only while you dictate. Quiet speech is now
  raised to a normal level first, and recording goes on a quarter of a second after you stop, so
  the last word isn't cut off.
- **Dictation pastes what it can't type:** text with a character your keyboard layout has no
  key for (é on a US keyboard, 漢字 on any) is pasted (Shift+Insert, which terminals take too)
  instead of only copied; `DICTATE_TYPING=paste` always pastes.
- **Performance Overlay** (3rd Party, linked): sasaken1102r's frame-perf-overlay, a panel in VR
  with the frame rate, CPU and GPU load, temperatures, memory and battery. Installed from its
  newest GitHub release, checked against its `SHA256SUMS`, with its own installer.
- **KnockThru** (3rd Party, linked, experimental): VioletTides' KnockThru turns passthrough on or
  off when you knock. It needs CEF Remote Debugging on; its page says what that allows.
- **Wallet apps protects terminal tools from Homebrew too**, such as Claude Code's `claude`: the
  page lists the commands of the formulae you installed and of casks, and **Protect** makes one ask
  for the wallet password first while the wallet is locked, with the wallet as its keyring (where
  a tool that can keeps its sign-in instead of a plain-text file). `wallet-tool` does the same
  from a terminal; **Remove** puts Homebrew's command back.
- **Controller buttons in the installer window are back, in VR:** with the laser on the window,
  B goes back, Y goes to the top of the list, A ticks or unticks the row you point at, and the
  left d-pad moves a highlight through the rows. They're read from the controller's model while
  the laser is on the window; the SteamVR Input version (off since 0.6.2) couldn't work on the
  Frame, where SteamVR gives button presses only to the app in front.
- **Dictation on a controller button, in VR:** hold **Menu** on the right controller (about half
  a second, until it ticks) to start dictating, and again to stop, whatever app is in front.
  `DICTATE_BUTTON` picks Y instead, or turns it off; `DICTATE_BUTTON_HOLD` sets how long to hold.
  It runs while SteamVR does, and reads the button from the controller's model, because SteamVR
  on the Frame gives button presses only to the app in front; the game still gets the press too.
- **VR memory guard (new, System):** Flatpak apps (Firefox and others from Discover) together
  leave 5 GB for SteamVR, Steam and your game (which aren't limited), Firefox has a 5 GB limit of
  its own, and SteamVR is the last thing stopped when memory
  runs out. An app over its limit is stopped instead of stalling the headset. Signing in to
  Firefox installed every synced extension at once and took 10 GB on a Frame, and SteamVR's
  compositor crashed. The limits are in `~/.config/frame-tweaks/vr-memory-guard.conf`.

### Changed
- **⚙ Settings: Apply is always in view.** A settings page's actions (Apply, Forget the phone,
  Charge to 100% once) sit at the top right beside its title, not after the last option, which
  on Dictation's page was several screens down in VR; what each does is its tooltip.
- **PyQt6 6.12** (from 6.11) for the installer window, Arrow Pad, Screen snip and the NordVPN tray,
  tried on a Frame. Full Keyboard 0.14.1 looked at, its Replace native keyboard tried beside Arrow
  Pad and Dictation.
- **Trusting a pack takes one press:** **Trust** on the Packs page, with a tooltip saying what it
  means (its tweaks run as you; it waits again if its files change), instead of Trust… then "Yes:
  it runs as me". **Every tooltip is larger,** with more padding: Qt's own were hard to read in VR.
- **No password yet? The window says so, and sets one.** A new Frame's user has no password, so
  sudo can't work, and the tweaks that ask for it (Homebrew, Battery charge limit, and those that
  need Homebrew while it isn't installed) failed partway. Now the window shows a line above the
  list with **Set a password…** (`passwd` in Konsole, then it looks again), Apply changes names
  those tweaks and offers the same button instead, and `./install.sh` doesn't start them, saying
  how to set one. Only Homebrew's install checked before.
- **Android Mirror offers the other phone in sight** when the remembered one won't connect
  (**Use … instead**), and goes on to pairing it. The first time, Android Mirror takes the only
  phone advertising, which may be another of yours: switching used to take Forget and opening
  it again. It also keeps a log of what it saw, chose and was told, without the pairing code
  (`/run/user/$UID/phone.log`, yours alone, gone at the next restart).
- **Dictation's controller button can be any button:** ⚙ Settings lists Menu, Y and Off as
  recommended, View and d-pad up as alternatives, and every other button as not recommended but
  available, each with what else it does while held (the laser's clicks, Home and Back over
  windows, picking up windows, the dashboard), including the headset's Aux button. The system
  buttons aren't offered: SteamVR keeps them.
- **Apply changes asks first, with the list.** Before anything runs, the confirm page says what
  will be installed, by name (with the tweaks those need that aren't installed yet, and which
  ask for the sudo password), and what will be removed, with the settings note. **Apply** goes
  ahead, **Cancel** goes back to the list with everything still ticked as it was. It used to ask
  only when something was being removed, and listed ids.

### Fixed
- **Buttons' rounded corners** no longer look notched at the bottom.
- **The version shown is the release you have:** between releases a checkout could show an older
  one (0.6.21+34 on 0.6.23), because the number came from whichever release tag git found first.
  It now always starts with the release in `VERSION`, as updates use.
- **Wallet apps says when the wallet has no password yet, instead of an Unlock that can't work.**
  SteamOS's stock wallet opens without a password, so the page's 🔓 Unlock… (and Password first
  on an app) asked for a password nobody could give. `wallet-unlock --info` now says whether the
  wallet has one: found out while the wallet is locked, by trying it without a password the way
  kwalletd6 itself does first, then locking it again, and kept for that wallet file (Change
  Password rewrites it, so the next lock looks again). Without one, the page warns that the wallet
  protects nothing, Unlock becomes Open (no dialog), and 🔑 Set password… opens KWalletManager;
  `wallet-unlock` itself opens the wallet without asking and says to set a password;
  `./install.sh status` warns too.
- **Screen snip works on Steam games:** a game run through Proton (and others drawing with
  Vulkan) draws straight to gamescope, so the snip came out black or didn't open. Then it now
  uses gamescope's own screenshot of what it shows.
- **`gh auth login` in a terminal saves its token in the wallet again, not in plain text.** The
  wallet tweak's `gh` wrapper (in `~/.local/bin`) is what makes gh use the wallet, but the
  Homebrew tweak's `brew shellenv` line in `~/.bashrc` came after the `~/.local/bin` PATH line and
  put Homebrew's bin first, so terminals ran Homebrew's gh directly. Installs now keep the
  `~/.local/bin` line below Homebrew's (only the line Frame Tweaks wrote moves), and
  `./install.sh status` warns while a terminal's gh isn't the wrapper. Re-run
  `./install.sh install wallet` to fix the order and move a plain-text token into the wallet.

- **The Mouse cursor fix goes by itself once SteamOS shows the pointer.** From gamescope 3.16.30
  (SteamOS 0.5.6 and the beta) the fix adds a second pointer, a black X, and switching to the beta
  with it installed left you with that until you removed it by hand (its status said to). Now an
  installed tweak this Frame doesn't need any more is removed by itself when its manifest asks for
  that (`when_not_needed: uninstall`, docs/mods.md): by the Frame Tweaks window as it opens, with
  a notice, and at each login by a user service (`./install.sh tidy`), which installs and updates
  set up. Its settings are kept. The pointer is one again after the reboot that follows.
- **NordVPN says how to get logged in.** Before `nordvpn-wg setup` has run, the tray's menu item
  copies that command for a terminal and says what to do with it, and any other `nordvpn-wg`
  command says to run it first with the command on your clipboard. The setup's token prompt now
  says where an access token is made (Nord Account → NordVPN → Manual setup → Generate new token),
  puts that page's address on your clipboard for the browser, and says how to paste the hidden
  token. It used to say only "Run 'nordvpn-wg setup' first." and "NordVPN access token (input
  hidden):".
### For contributors
- **[docs/compatibility.md](docs/compatibility.md)** shows each tweak's status on the SteamOS and
  SteamVR builds it was checked on, generated from records that `dev/update-check.sh record`
  adds on a Frame.
- **Shorter entry docs:** the full tables of tweaks moved from README.md to
  [docs/tweaks.md](docs/tweaks.md) (generated by `dev/gen-docs.py`, checked by
  `dev/check-docs.py`), leaving one line of names per category in the README; releases 0.5.0 and
  earlier moved from this file to [docs/changelog-0.x.md](docs/changelog-0.x.md).
- **New docs:** [docs/how-it-works.md](docs/how-it-works.md), the code on one page;
  [docs/release-signing.md](docs/release-signing.md), how updates check releases and how the
  release key changes, with the current change's end date; a quick start at the top of
  CONTRIBUTING.md; the status protocol as a table in docs/mods.md; and what release signing
  protects against, and what it doesn't, in SECURITY.md.
- **The installer window is split into modules** (`gui/`), and dependency order moved from
  bash to `lib/installer.py`, the first step of moving the installer's logic to Python
  ([DESIGN.md](docs/DESIGN.md#moving-the-installer-to-python)).
- **`dev/container-check.sh`** runs `dev/check.sh` in a container with CI's environment
  (`dev/Containerfile`, Podman or Docker), so every check runs on a Mac, Windows or any Linux.
- **`steam-frame.yml`:** what Frame Tweaks is, in frame-commons' manifest format, with a test record
  (headset SteamOS, build, SteamVR, channel, result) for each release tried on a Frame, added by
  `dev/record-tested.sh`; the catalog's compatibility table is built from them.
- **`dev/button-test.py`:** a window, in VR on a Frame, showing which buttons Frame Tweaks sees
  pressed (the controllers' through their model, the headset's Aux key through Linux), red once
  a press is long, and what the window gets from SteamVR's laser mouse (CONTRIBUTING.md,
  "Testing controller buttons on a Frame").
- **`dev/update-check.sh`** checks updates on a Frame: snapshots of the install before and after
  an update, compared (version, signatures, each tweak's status, services, installed programs),
  and a release test that updates copies installed at the last releases, in throwaway homes, and
  checks each verifies the new release's signature and moves to it.
- **`dev/fetch-upstream-readmes.py` fetches only over HTTPS from GitHub:** a picture in an upstream
  README at a `file:` address (a file of yours, such as gh's token) or on another host was read and
  saved into `upstream/`, ready to commit. Now it stays a link, with a warning, and redirects away
  from GitHub are refused.
- **`dev/backup.sh`** keeps snapshots of a checkout on another drive (an SD card): everything in the
  folder, `.git` and what git ignores included, but not what can be made again (`__pycache__`,
  `.venv`, `.cache`, `tmp`); each snapshot hardlinked against the one before, the newest 48 kept;
  `--timer` makes one every hour.

## 0.6.23 (2026-10-27)

### Security
- **Updating works again from every version, with one click.** 0.6.22 was signed with the new
  release key only, which copies that hadn't updated to 0.6.21 yet don't know, so their update
  refused it. While the old key is retired, each release is now signed with the old key (so those
  copies accept it) and cosigned with the new one (`cosign-vX.Y.Z`), which is what your copy
  checks from this release on. Your copy trusts only the new key (`dev/release-signers`) and
  never goes back to trusting the old one; the old key's signature, still on releases for copies
  that haven't caught up, doesn't count for it. Copies on 0.6.22 get here through a bridge tag
  (`v0.6.23-bridge`), the only way their check accepts the old key's signature, for that one update.
- **The old key stops signing releases on 2026-12-11.** Releases from then on carry the new
  key's signature only. Update before then (any version, one click) and nothing changes for you;
  a copy still on 0.6.20 or older after that date refuses the update, and needs
  `./install.sh update --to v0.6.23`, then `./install.sh update`, once.

## 0.6.22 (2026-10-27)

### Security
- **The old release signing key is retired.** This release is signed with the new key only
  (SHA256:1/YuVhUNkdDJSId9uNalpS6L0thjsPcIdsq8h8yfSEM), and the old one is dropped from
  `dev/release-signers`, so your install stops trusting it. If you're on 0.6.20 or older and
  `./install.sh update` says this release "isn't signed by Frame Tweaks' release key", your copy
  doesn't know the new key yet: run `./install.sh update --to v0.6.21` (signed with the old key;
  it teaches the new one), then `./install.sh update`.
- **A key change no longer strands copies that skipped a release:** when the release signing key
  changes, `./install.sh update` now checks the releases between yours and the newest, and learns
  the new key from one signed by a key it already trusts. Before, a copy that skipped the release
  introducing a new key refused every release after it.

## 0.6.21 (2026-10-22)

### Security
- **A new release signing key.** The old one was on a Steam Frame that went back to Valve for
  repair, so it's being retired. This release is still signed with the old key, and teaches your
  install the new one (`dev/release-signers`); from the next release on, releases are signed with
  the new key only (SHA256:1/YuVhUNkdDJSId9uNalpS6L0thjsPcIdsq8h8yfSEM), and the old one is
  dropped. Nothing else changes: Frame Tweaks' code is 0.6.19's.

## 0.6.20 (2026-10-18)

### Changed
- **Battery charge limit is withdrawn for new installs, and at your own risk if you have it.**
  A known SteamOS charger bug
  ([SteamOS #2879](https://github.com/ValveSoftware/SteamOS/issues/2879)) stops some Frames
  taking power from USB while plugged in, and a Frame running the tweak hit it on 17 October 2026
  and no longer charges. The window now hides the tweak unless it's installed, and
  `./install.sh install` skips it; if you have it, it stays, and its README and 🧪 note say what
  to watch for. If the battery drops while plugged in and the limit isn't holding it, charge from
  a plain 5 V USB source before it runs out. This release changes nothing else: Frame Tweaks'
  code is 0.6.19's.

## 0.6.19 (2026-10-17)

### Added
- **Linked projects say when they have an update:** Recline's row now shows "↑ 1.4.0 available ·
  Update" when Recline-VR publishes a new release, as Full Keyboard's already did; Update (or ↻)
  installs it, then restart SteamVR. It used to look up to date until you pressed ↻. Any linked
  project can do the same with one line in its manifest, `version:` (docs/mods.md, Linking a
  project), and needs no change when it publishes its next release.
- **Tick or untick a whole category:** two boxes beside each category's name in the installer
  window tick or untick every tweak in it (the ones it shows), as clicking each would; nothing is
  installed or removed until Apply changes.
- **Move Arrow Pad and Screen snip's panel anywhere while Steam's keyboard is open (VR):** with
  the keyboard open, SteamVR hides where your controllers are from other programs, so the panels
  could only slide flat. Now SteamVR's own grab bar, as under a desktop window, shows under each
  of them while the keyboard is open: hold it and the panel moves with your hand as a floating
  window does, turned and tilted with it, nearer or further with the thumbstick, and stays where
  you let go. The panel is only told where that was, never where your controllers are. It comes
  with the VR environment helper.
- **Narration volume:** Screen snip's narration panel has Volume down and Volume up buttons
  (icons), after Next part. The narration's own volume, from 100% down to 10%, remembered, and a
  change is heard at once, mid-sentence. **Show text** moved to the bottom row, beside the left
  Collapse button.

### Fixed
- **Screen snip's narration panel and Steam's keyboard (VR), as on Arrow Pad:** pressing the
  panel while you typed took the keyboard away from your window (what you typed next went
  nowhere) and moved it; now the keyboard goes straight back to the window, where it was. The
  dashboard patch that does it for Arrow Pad now does it for every Frame Tweaks panel, and comes
  with the VR environment helper (any VR environment tweak installs it). And while the keyboard
  is open, the panel couldn't be moved at all (SteamVR hides the controllers then): it now
  slides after the laser, with a note under it saying why.

## 0.6.18 (2026-10-17)

### Added
- **Help check the translations:** ⚙ Preferences now says, under Language, that translations
  are made by machine first and then confirmed by people who speak the language, and how many
  of your language's texts are still unconfirmed. Two links follow: Help make Frame Tweaks
  better, and Check a translation, a new GitHub form (your language and version filled in) for
  saying a translation reads right, or what to fix. A third, Translate it yourself, offers to
  translate: a new language, or a proper pass over one made by machine.

### Changed
- **Preferences' "Show me" (installing in a terminal) speaks your language:** the pretend install
  it plays was always in English. It now prints what a real install would, in the language chosen
  for Frame Tweaks.
- **Diagnostics reports go to your Downloads folder:** `~/Downloads/frame-tweaks-debug-….txt`
  instead of the home folder, which they cluttered, and where Flatpak apps such as Firefox (for
  the bug form) can read them.
- **🐞 Report a problem shows the report in the window:** with a 📋 Copy button, to paste it into
  the bug form (or attach the saved file, as before). It used to open the report in your text
  editor; in VR that started Kate, and SteamOS's own desktop portal crashes when a KDE app from
  Flathub starts there (a SteamOS bug: KWalletManager does it too).

### Fixed
- **"The last update didn't finish" when nothing had failed:** the window decided from the
  versions the tweaks were installed with, so once the Frame Tweaks folder had moved on some
  other way (a `git pull`), it offered ⬇ Finish the update, which ran every tweak's installer
  again. An update now marks itself until every tweak is installed again, and only an update
  really cut short (its terminal closed, Ctrl+C) or with a tweak that failed is offered to finish.

## 0.6.17 (2026-10-17)

### Changed
- **Arrow Pad's ✕ Close needs a short hold:** a press aimed past the pad, at the dashboard's menu
  behind it, closed it. ✕ now turns red while held and closes after 0.8 seconds; let go sooner
  and a note says to hold it.
- **The charge limit's status starts with the battery level:** "Battery 76%; charging stops at
  78%" (it was "Stops charging at 78% (battery 76%)", easy to read as the battery at 78%). Its
  settings and README also say why Steam's dashboard shows more for the same charge: Steam
  converts the battery's reading its own way, about 8 points higher around 80%.

### Fixed
- **Menu entries stuck in another language:** after you tried a language in ⚙ Preferences and
  switched back, Arrow Pad, Android Mirror and the other Frame Tweaks entries in Steam's "+" menu
  could stay in that language. An entry installed before a language was added didn't know that
  language's name for itself, took it for one you had typed, and left it. They now recognise
  every language's name, and a reinstall no longer keeps such a name as one of yours. The
  window's Wallet apps page, which showed those names, now names Frame Tweaks' own apps in the
  window's language whatever the menus say, and other apps in it too where they have the name.

## 0.6.16 (2026-10-17)

### Added
- **French and Flemish Dutch:** Frame Tweaks now speaks French and Flemish Dutch (Dutch from the
  Netherlands uses the Flemish), alongside Latin American Spanish: choose them in ⚙ Preferences,
  or they follow your keyboard. A native speaker hasn't checked them yet; corrections are
  welcome (locale/README.md).

### Fixed
- **Frame Tweaks spoke English on a Frame set up in another language:** SteamOS keeps the system
  language at English whatever language you chose, so unless your keyboard layout said otherwise,
  everything was in English. Frame Tweaks now also follows the language Steam is set to (after
  your keyboard and any language you chose for the desktop), and so do the menu entries. The
  first lines the install command prints, before Frame Tweaks is downloaded, are in your language
  too.

## 0.6.15 (2026-10-17)

### Added
- **Android Mirror disconnects by itself:** a mirror left on overnight kept the phone streaming
  until its battery was empty. After an hour (or the time you choose in Android Mirror's
  settings, or with the gear in VR: 15 minutes to 8 hours, or never), a small window asks
  whether to keep it on; with no answer within a minute, the mirror closes, the Frame
  disconnects from the phone, and Android Mirror's programs stop. *Restart stream* starts the
  time again.
- **Arrow Pad warns when desktop mode has taken all input:** after a Right Ctrl, desktop mode
  keeps everything you type in VR, so typing in a floating window went into the desktop instead.
  A note under the pad now says so, and to tap Unstick (under Tools) to give it back. It shares
  its spot with the note about sliding while Steam's keyboard is open; with both, one note shows
  both messages.

### Fixed
- **Dictation with Ctrl on:** a Ctrl latched or locked on Arrow Pad (or Alt or Super) was still
  down when Dictation typed, so each letter went out as a shortcut: Ctrl+W closed the tab, Ctrl+Q
  quit the app. 0.6.13 fixed this for Arrow Pad's 🎤 only; Dictation started with its shortcut or
  from the menu still typed that way. Dictation now lets go of the modifiers held down on the
  virtual keyboard before it types (only those that are down, so no stray Shift or Alt taps), and
  Arrow Pad turns its own off when it sees Dictation start or finish, so it doesn't show a Ctrl
  that isn't on.
- **Arrow Pad couldn't be moved while Steam's keyboard was showing:** SteamVR hides where the
  controllers are from other programs while its keyboard is open (keyboard privacy), so grabbing
  the pad did nothing. It now slides flat along its own surface after the laser instead, and a
  small note under the pad says why it can only slide until the keyboard closes.
- **Pressing Arrow Pad took Steam's keyboard away from your window:** Steam's keyboard follows
  the laser, so a press on the pad handed the keyboard to the pad: what you typed next went
  nowhere, and the keyboard jumped to another spot (far, once you'd moved the dashboard). With a
  VR environment tweak installed, the keyboard now goes straight back to the window you were
  typing in, so typing carries on there and the keyboard stays where it was.

## 0.6.14 (2026-10-17)

### Changed
- **The pop-up after clicking a link is bigger and stays longer:** what it did ("Opening in
  Firefox in desktop mode", "Link copied"), by the pointer, now in twice the text size and for
  twice as long (20 seconds, more for long ones). Open folder on the Packs page shows the same.
- **The wallet's auto-lock counts from the unlock:** each app opening the already-unlocked wallet
  moved the auto-lock later, so it could keep the wallet unlocked well past the time the Wallet
  apps page showed. Only an unlock or **Extend timer** sets it now.

## 0.6.13 (2026-10-17)

### Changed
- **Quitting an app doesn't lock the wallet:** when the last app using KDE's wallet service
  (Signal, say) quit, the service said the wallet closed, and that locked it for every app,
  Firefox and `gh` included, but only sometimes (it depended on timing). Now it never does: the
  wallet locks at its auto-lock time, with **Lock now**, or after its idle time unused.

### Fixed
- **Battery charge limit overnight, again:** the check every 30 seconds could lift the pause made
  for sleep in the seconds before the Frame fell asleep (logind waits for SteamVR's and others'
  sleep locks), so it charged to 100%. The pause now holds until the Frame wakes; waking, the
  sleep lock is taken again first, and a sleep straight after waking isn't missed.
- **Packs' git can't run commands:** checking or updating a pack (`./install.sh mods updates`,
  `mods update`, the Packs page's Update) ran git in packs you hadn't trusted, and git acts on a
  repository's own settings, which can run commands. Only trusted packs are checked or updated, and
  git runs in one only if its `.git` settings are the ones adding it made.
- **Arrow Pad:** 🎤 started Dictation with a latched Ctrl/Alt/Super still down, so every letter
  typed became Ctrl+letter; Snip and Launcher let a latched modifier go too. A crash no longer
  leaves modifiers down, one failing SteamVR call no longer ends the VR panel, and Reset with no
  headset pose no longer crashes it.
- **Wallet:** ↻ on the wallet left an unlocked wallet with no auto-lock; updates turned Password
  first back on for KWalletManager, Signal and Claude Desktop; with no wallet made yet, every
  protected app (KWalletManager too) refused to open; Frame Tweaks' own menu entry, protected,
  lost its password gate when rewritten. Also: a slow unlock no longer looks like a wrong password,
  and the Wallet apps page no longer says "open for 9 h" right after unlocking.
- **Desktop Recovery's taskbar watch** carries on when KWin restarts after a crash (it stopped),
  doesn't spin on a taskbar that ended but wasn't collected yet, and says when it couldn't start
  the taskbar again.
- **Menus in your keyboard's language:** Steam saving its settings several times in a few
  seconds stopped the watcher that relabels them, until something restarted it.
- **The splash:** commands run under it no longer ignore SIGPIPE (Python's setting leaked into
  every install), piped input stays the command's, Ctrl+C during the splash reaches the command,
  and a command ending during it shows ✔/✖ and keeps its exit status; several terminal-state fixes.
- **The window** offers **⬇ Finish the update** after an update cut short (it said "up to date"),
  and opens with every pack turned off (it stayed shut). `./install.sh update` refuses an option it
  doesn't know (it updated anyway), and git's background maintenance no longer holds the install
  lock. A window that died is no longer followed for its language until the Frame restarts.
- **Uninstalling Frame Tweaks** lets go of tweaks no pack has any more (it asked for a pack that
  doesn't exist and kept everything shared), and keeps a copy without git (it deleted your edits).
- **Recline** keeps a `~/Recline-VR` clone of yours on uninstall; **Claude Desktop's updater**
  can't hang on a stalled connection or leave Claude Desktop deleted; the **dashboard service**
  rides out a reply cut short as SteamVR starts or stops.

### For contributors
- `dev/run-tests.py`: Ctrl+C stops the run (queued parts used to start one after another); with
  the headset on, every thread of a test is pinned, every second, and a failed sensor read keeps
  the last state; a part that ends without its results fails. `dev/check.sh` stops on a
  `FRAME_TWEAKS_CHECKS` it doesn't know. `dev/fresh-install.sh`'s sandbox: read-only control
  groups, its own `/dev/shm` and `/var/tmp`, no X11 with Wayland there, and `--from checkout` works
  on a test release's VERSION. The release workflow numbers a test release after the highest.

## 0.6.12 (2026-10-16)

### Added
- **A new look for installs in a terminal:** Frame Tweaks' logo, its two sliders gliding, and its
  name in pixel letters, first as a short splash (any key skips it), then in the top half of the
  terminal while the install, removal or update runs in the bottom half, with a bar saying what's
  being done and for how long. When it's over, the terminal is as it was, with the whole output in
  it (and its scrollback) under a small banner. Questions, sudo's password prompt, progress bars
  and Ctrl+C work as before. It's drawn in "▀" characters, two pixels to a cell, and nothing
  sweeps across the whole screen, which is uncomfortable in the headset. **⚙ Preferences →
  Installing in a terminal** chooses animated, still or the output only, and **Show me** shows
  it (`FRAME_TWEAKS_SPLASH=on|still|off` goes first); KDE's animation speed set to instant keeps
  it still too. Or see it with `python3 lib/splash.py --demo`.

### Changed
- **The installer window sets itself up without asking:** the first time, PyQt6 (what the window
  is drawn with, about 280 MB) is set up at once, under the new splash, instead of after a
  question whose other answer was the simple checklist. The checklist is still there if the
  setup fails. Started from the app menu, the setup shows in a terminal window of its own. Its
  messages no longer say how long it takes ("usually a minute or two"): that depends on your
  Internet connection.

### For pack authors
- **`dev/fresh-install.sh --beta`** runs the testers' one-liner (`… | FRAME_TWEAKS_CHANNEL=beta
  bash`), which takes the newest test release. Its window's PyQt6 setup now shows the splash too:
  without a controlling terminal (the sandbox is a session of its own) and with the script coming
  from curl, the splash reads keys from the terminal its output goes to.

## 0.6.11 (2026-10-16)

### Added
- **Desktop Recovery brings the taskbar back by itself:** a small watch starts with desktop mode
  and, when the taskbar closes while desktop mode runs, starts it again a few seconds later (at
  most 3 times in 10 minutes; then it stops and says so, and **Restart taskbar** is still there).
  The taskbar disappears because SteamOS's graphics layer for desktop apps (Gamescope WSI) sends
  KWin a request about a window that's no longer there, and KWin disconnects the app: a SteamOS
  bug, not Frame Tweaks'. Reinstall Desktop Recovery (↻) to get the watch.

### For pack authors
- **`dev/fresh-install.sh`: a fresh install without touching yours.** It runs the one-liner (from
  GitHub, a chosen release, or your clone as it is) in a throwaway home inside a sandbox, and
  opens the window on your desktop: a dry run unless you pass `--real`. Your home, wallet, user
  services, Homebrew, Flatpaks, other processes and the Frame's own network services are out of
  its reach (CONTRIBUTING.md, "Trying a change").
- **`dev/test-tweaks.sh` stands in for `pgrep` and `pkill`:** nothing runs in its throwaway home.
  The real ones saw this machine's desktop, so a tweak starting something in desktop mode as it
  installs started it in the real one.

## 0.6.10 (2026-10-16)

### Changed
- **Claude Code is set aside** (not offered any more): Homebrew has it (`brew install --cask
  claude-code`), and Frame Tweaks offers only what you can't get from Discover or Homebrew. An
  installed Claude Code stays, with your sign-in and history in `~/.claude`.

### Fixed
- **Hidden and folded groups stay so in another language:** the window kept them by their
  translated names, so when its language followed the keyboard to another, they came back. They're
  kept by their English names now, and ones saved in another language are still recognised.
- **Pack safety:** looking for a community pack's updates ran git in its folder before you trusted
  it, and git reads a repository's own settings, which can run commands: only trusted packs are
  looked at now. `./install.sh mods` shows packs' own text without control characters, which
  could make an untrusted pack's line look like an official one. A settings option without a
  `default:` (or a shell settings file whose keys aren't variable names) leaves its tweak out,
  as a mistake, instead of making every command fail, `mods untrust` included.
- **`./install.sh mods check` and the pack check action** treat a pack with its own README.md and
  no pack.md as a pack, checking its tweaks, as Frame Tweaks loads it.
- **Battery charge limit holds overnight:** asleep, nothing could check the battery, so a Frame
  that went to sleep during one of the few minutes of charging charged on to 100% (here: 77% at
  00:59, 99% at 06:33). Now, as the Frame goes to sleep, charging pauses if the battery is within
  10% of the limit or over it (a logind delay lock gives it the moment), and it checks again as
  it wakes; a lower battery still charges while asleep. Its status also says "Not charging until
  the battery is below 78% (now 98%)" rather than "Holding at 78%" when it's well over the limit,
  and warns if the watch on sleep isn't running.
- **A tweak whose status check fails no longer reads as not installed:** a check that stopped
  partway (a command in it failing) made an installed tweak look uninstalled, so updates skipped
  it, and deleting the settings uninstalled tweaks left would have deleted its settings. It now
  shows "status check failed", with the error, and counts as installed. Shared clipboard's check
  did this while a build from an older version ran: it now says what that build lacks. Firefox's
  says there's no profile when Firefox has no default one.
- **Updates:** a tweak removed by hand no longer has every update after it run every installer
  again, as if one hadn't finished; an update ends in failure when a tweak's installer fails (it
  said all was well); going from a test release to its release runs the tweaks' migrations (the
  test release ranked as the newer one); and in a copy without git, `./install.sh update`
  leaves held tweaks as they are.
- **↻ Reinstall keeps a tweak this Frame doesn't need:** reinstalling one that is installed (the
  Mouse cursor fix on SteamOS 0.5.6, say) removed it, then skipped it as not needed.
- **A tweak another one needs isn't removed while that one is installed with a warning:** only a
  tweak whose status was all fine counted as installed there.
- **Uninstalling Frame Tweaks keeps a folder with commits of yours:** a commit made in a release
  checkout is on no branch, so it wasn't counted, and the folder was deleted with it.
- **With every pack turned off, Frame Tweaks' own commands still run:** `./install.sh mods on core`
  (the way back), `update`, `help`, `--version`, `debug-info` and `report` stopped with "No
  tweaks found".
- **`frame-tweaks/install.sh` runs from the folder above:** run by a relative path with a folder
  in it, the installer stopped at once ("No such file or directory"), and `get.sh` with a
  relative `FRAME_TWEAKS_DIR` did the same.
- **A new install takes test releases if you chose them before:** `get.sh` read the channel only
  from `FRAME_TWEAKS_CHANNEL`, not from `~/.config/frame-tweaks/channel`, where it keeps it.
- **🐞 Report a problem keeps SteamOS's own names:** your user name (steamos, on the Frame) was
  removed everywhere, so steamos-manager and /usr/lib/steamos read `<user>-manager` and
  `/usr/lib/<user>`. It's now removed where it names you: a home folder, name@host, `user=`,
  "for name" and `uid=1000(name)`.
- **Setting up the full window:** it checks for the parts the window needs (PyQt6's widgets, not
  just PyQt6), so a setup cut short is offered again rather than a window that can't open; the
  copy of Python the window runs on is replaced whenever it differs from the original (it could
  stay an old one); and the app-menu entry is never left empty (translating it failed, and it
  was empty: it's in English then).
- **A `~/.bashrc` whose last line has no newline:** the line tweaks add (Homebrew, and
  `~/.local/bin` on PATH) was glued onto that last line, breaking both.
- **The wallet locks when the Wallet apps page says it will:** its auto-lock was a countdown, which
  started again at every `systemctl daemon-reload` (Frame Tweaks' installers run one) and stood
  still while the Frame slept, so the wallet stayed unlocked hours past the time shown. It's now
  set for a time on the clock: a reload doesn't move it, and if the time goes by while the Frame
  sleeps, the wallet locks as it wakes. An unlock and the wallet's watcher setting it at the same
  moment no longer end in "Wallet unlocked for ? hours", and a wallet unlocked again while the
  watcher was still locking it gets its auto-lock too.
- **Close after counts the time asleep, and wearing the headset:** the time the Frame spends
  asleep now counts, and the key or the headset that wakes it no longer resets the idle time
  first, so an app left open overnight closes as the Frame wakes, before whoever picks it up gets
  to it. The VR controllers aren't input it can see, so an app used only with them was closed
  mid-use: now wearing the headset (its proximity sensor) counts as activity too, and the Wallet
  apps page says what counts: the headset not worn, and no keyboard or mouse input. **Headset
  off** also closes its apps when the headset came off just before the Frame went to sleep.
- **Reinstalling a tweak (↻) keeps Password first on its menu entry:** Dictation, Arrow Pad,
  Screen snip, the NordVPN tray, Android Mirror and Claude Desktop lost it (and the shared wallet)
  at every reinstall, and reinstalling the wallet tweak itself took it off every app but its own
  three.
- **`gh` from the installer window:** installing the wallet from the window set up no `gh` wrapper
  (its Konsole has no Homebrew on the PATH), and removing it from there left git's credential
  helper naming the deleted wrapper, so git couldn't sign in to GitHub. The install now looks in
  Homebrew too, and the removal puts back the `gh` the wrapper ran (or, if that's gone, takes the
  wrapper's helper line out). The `gh` helper is no longer added beside a github.com credential
  helper of your own, and a `gh` of your own in `~/.local/bin` is no longer deleted.
- **Signal's Close after: Never stays Never:** reinstalling Signal, or updating Frame Tweaks, set
  it back to 15 minutes. (If an update already did, set Never once more: it's kept from then on.)
- **Wallet apps page:** a Close after timer on an app whose id has spaces (a menu entry of your
  own, "My App") now holds; unticking **Password first** on an entry with nothing else on now
  removes its protection, instead of leaving it marked "password only" with no password; and a
  link to a menu entry that's gone no longer makes the wallet read as not installed.
- **The wallet's watcher uses less CPU:** it looked for KDE's own password prompt (a few programs
  each time) every 1.5 s, about 2.6% of a core all day, and now does only while the wallet is
  locked. The unlock dialog's check for an open KDE prompt now leaves out a 1-pixel ksecretd
  window, as the watcher's always did.
- **The wallet's install message** no longer says the wallet's password is empty when you've set
  one.
- **The installer window follows packs that change under it:** a pack edited or turned off
  outside the window, then the Packs page or Check for updates (or a pack's Update still running
  when you went Back), left the list with tweaks it no longer had. Checking them again showed the
  error page and left their rows "checking…" for good, and Run on one did the same. The list now
  follows the packs whenever they're read again, the Packs page reads them as it opens rather than
  at every click, and a pack's update that ends after you went Back is finished by the window. A
  row whose tweak went (its folder moved by an update, say) says "not available any more".
- **Web links open with a broken app entry around:** a desktop entry linking to an app since
  removed stopped every web link (READMEs, a tweak's page, Packs, the bug form) from opening when
  the default browser couldn't be used. Such entries are left out, and a link the browser helper
  can't open opens the usual way.
- **"↑ X available · Update" goes when it's no longer so:** it stayed after the tweak was updated
  or uninstalled, and its Update then installed it again. It goes when nothing newer is found,
  when the tweak isn't installed, and once ↻ or Apply changes has run.
- **Every row's buttons fit the window:** it could be made narrower than its rows, which cut off
  Hide, ↻, ⓘ and then Run (below about 930 pixels wide; 970 in Spanish). It's never narrower than
  its widest row now, and a long Run button (⟳ Restart SteamVR) isn't squeezed below its text.
- **The installer window's pages:** a tweak's page shows its status as the check comes in (it
  said "checking…" until opened again); Ctrl+wheel makes a README's text larger or smaller (it
  did nothing); a settings action opened again while it runs (Charge to 100% once, the Speech
  engine's Apply) says how it goes, where it said "Working…" for good; removing a pack takes it
  out of the "N pack updates" notice; a command in a list item (Android Mirror's
  `adb pair <ip>:<pairing-port> <code>`) shows `<ip>`, not `&lt;ip&gt;`; and the error page's Back
  closes the page that was open, which kept the window from following the keyboard's language.
- **Status checks:** one that ends some other way (127: a command missing) says "status check
  failed (exit 127)", a warning, where it said "not installed" for a row counted as installed.
  Refresh drops the last round's checks that haven't started (three refreshes ran 75 status
  scripts), closing the window while it checks no longer fills window.log with errors, and a
  check that fails in the window is said on its row instead of the error page.
- **Smaller fixes:** why a tweak isn't needed follows the window's language; a known issue of a
  tweak a pack brings later is looked up too (its page said "Checking for a newer release…" for
  good); and a second launch that finds the window stuck stops only the window, not an editor
  that has its file open.
- **Arrow Pad's shortcuts and Dictation's typing on a French, German or other keyboard layout:**
  both sent a US keyboard's keys, which the desktop reads with its own layout. On a French one,
  Select all was Ctrl+Q (the app quit) and Undo Ctrl+W (the tab closed); on a German or Swiss one,
  Undo and Redo were Ctrl+Y; and dictated text came out with the wrong letters and punctuation.
  The keys now come from KDE's layout, worked out with libxkbcommon as KWin does: a shortcut's
  letter is where that layout has it, and Dictation types each character with the key that types
  it there (with Shift or AltGr, or a dead key first: ´ then e). Text with a character the layout
  has no key for isn't typed at all; it's in the clipboard, and a notification says so. On a US
  keyboard nothing changes.
- **Arrow Pad's keys act once per press:** a laser wavering at a key's edge slides off the key and
  back, and each slide counted. One Paste sent Ctrl+V three times, 🎤 started, stopped and
  restarted dictation, Snip opened three times, and a tap on Ctrl left it locked. Buttons now act
  once, when you let go on them (let go off the key to cancel); a modifier stays down until you
  let go, and keys you hold (arrows, Bksp…) still go up as the pointer leaves them. In VR, a
  laser's press whose release never arrived ends when that laser presses again, rather than
  keeping a modifier down.
- **Arrow Pad lets go of its keys when it goes away:** when desktop mode ended, the desktop pad
  ended with it before letting go, and a Ctrl it had latched stayed down for the whole Frame
  (every click a Ctrl+click). It now lets go first, and when it's stopped (an update, an
  uninstall, which now gives it 2 seconds to close before stopping it); in VR, when the dashboard
  closes, before anything is asked of SteamVR.
- **Arrow Pad's Unstick gives desktop mode's input back in other languages:** it looked for the
  English window title ("Press right control to ungrab input"), which KWin translates, so on a
  German, French or Spanish desktop the grab was never given back. It now reads KWin's own
  translations for desktop mode's language, and still sends Right Ctrl only when the title says
  the grab is on. Another window's title that isn't UTF-8 no longer crashes the pad on Unstick.
- **Scroll strips scroll again after the dashboard reloads,** and Android Mirror's touch layer
  works again: a reloaded page got the bindings they call only with DevTools' Runtime domain on,
  so the strips showed but didn't scroll, and the gear said to reinstall.
- **Scroll strips stop when their release goes missing:** a release the page never saw left a
  strip scrolling until the next click, each move of the laser elsewhere putting off the
  3-second stop. Only moves on the strip itself keep it going now.
- **Dashboard patches are checked against the dashboard page's own code:** the check searched
  every bundle in SteamVR's dashboard folder, some of them other pages', so a piece found only
  there counted as present. Installing a patch says "Active now." only once it is, and otherwise
  what the patches service says. While a patch's panel isn't showing, the shared helpers no
  longer wrap the dashboard's drawing again every 2 seconds, a layer deeper each time.
- **Battery charge limit:** removing it on a SteamOS without the charger's pause switch stopped
  with an error, right after taking out its udev rule; it now finishes. Its status no longer says
  "then stopping at off% again" when Charge to 100% once is pending with the limit turned off.
- **Removing Firefox privacy keeps the settings you had before it:** it took all of its settings
  out of `prefs.js`, yours too, so an HTTPS-only mode or strict tracking protection you had set
  yourself went back to Firefox's defaults. Installing now records those of yours, and removing
  puts them back as they were. (Installed by an earlier version, it can't tell yours from its
  own: removing resets them all, as before.)
- **Narrate stops, and says why, when the Speech engine fails:** if Piper ended without making a
  part's sound, Narrate started it again and again (143 times in 3 seconds) without a word; if
  it couldn't start at all, the panel said "Preparing…" for ever, and Read it again read nothing.
  Now a part is tried once more, then Narrate stops there and says the Speech engine failed (or
  didn't start); Read it again tries again.
- **Narrate finishes when you pause just as the last part ends:** it stayed "Paused." at the
  end, and Stop then read it all again.
- **Narrate's VR panel closes cleanly when SteamVR fails under it:** an error from SteamVR in one
  of its timers (SteamVR restarting, say) aborted the program, leaving the narration's files
  behind. Now the narration stops and the panel closes, as with Close; a new snip opens a new one.
- **Android Mirror's Restart stream after Reset to defaults** went on with the old picture size,
  bit rate, frame rate and clipboard setting; it now restarts at the defaults.
- **Android Mirror's removal stops adb in both sessions:** pairing from a terminal in desktop
  mode starts a second adb server, in desktop mode's runtime folder, and removing the tweak
  stopped only the one in its own session.
- **Android Mirror's pairing instructions** (its README, and the message after installing) put
  the pairing code on adb's command line, and so in your shell's history: they now say to run
  `adb pair <ip>:<pairing-port>` and type the code when adb asks for it, as Pair it again does.
- **Dictation transcribes a recording that stopped by itself** (the microphone gone, say) at your
  next press, or at the auto-stop, as it does one still running. The next press started a new
  recording instead, and the first one's file stayed in memory until the Frame restarted.
- **Dictation's install removes the older Whisper models** that earlier versions downloaded, as
  it meant to: every `dictate.conf` has the example's commented-out line naming one, and that
  kept `ggml-base.en-q5_1.bin` for good. Only a `DICTATE_MODEL` setting in use keeps one now.
- **Dictation's auto-stop timer goes with its recording:** a recording stopped by a press left its
  timer sleeping out the auto-stop time (5 minutes) as a process of its own.
- **A tweak's menu entry is written whole:** if translating it failed, its entry was left empty
  and the tweak's install stopped; it's written in English then.
- **Your changes to an app the wallet protects stay:** its menu entry is written again whenever
  the protection is put on again (the wallet's install does it at every update), and that went
  back to the app's original, so a new name or icon from KDE's menu editor, or an option you'd
  added to its command, was lost. A copy of the entry as written is kept now: what yours says
  differently goes into the new one, and stays when the protection is removed. A Frame Tweaks
  menu entry you renamed also keeps its name when the keyboard's language changes.
- **Your changes to Frame Tweaks' own menu entries stay too:** a tweak's update wrote its entry
  whole (Arrow Pad, Dictation, Screen snip, Frame Tweaks itself; Claude Desktop's at each of its
  updates), so a name or icon you'd given it went back. They're kept the same way now. If an
  update changes an entry's command and you'd changed it too, the update's is used: yours may
  not run any more.
- **Recline with Recline-VR 1.3:** Recline-VR 1.3 (out 2026-10-16) moved its programs into
  `bin/linuxarm64/` and removed the file Frame Tweaks checked, so after an install or ↻ Recline
  showed as not installed. Either place counts now, and its page gives the new `reclinectl` path.
- **KWalletManager shows the wallet open while it is:** it asks `kwalletd6`, which counts only
  what was opened through it. Started after the wallet was unlocked (KWalletManager starts it),
  it said "closed" while Firefox and Signal used it. The wallet's watcher opens it there too now.
  And after a SteamVR restart, the Wallet apps page counted "open for" from the unlock before it.
- **⟳ Restart SteamVR works from desktop mode:** SteamOS's restart goes through the VR session's
  service manager, which the window in desktop mode couldn't reach ("Failed to connect to user
  scope bus"), and nothing happened, without a word. The uninstall of a SteamVR add-on no longer
  suggests typing `steamvr restart`, which fails in a desktop-mode terminal the same way.
- **Full Keyboard's page says when it shows:** only while the SteamVR dashboard is open,
  whichever menu started it (it said "for the dashboard and desktop"), and how to move it.
- **Recline keeps up with Recline-VR's releases:** its status checks the uninstaller every
  release puts in the same place, not one of its programs (1.3 moved them all), and "restart
  SteamVR to load it" goes by when Frame Tweaks installed it, not by the dates the installer
  gives its files. Its page no longer copies the shortcuts and paths that change between
  releases (1.3 changed both): it links to Recline-VR's README for them, and says that
  SteamVR's own recenter now reclines you.

### For pack authors
- **A link's `installed:`** names a file the project documents and keeps (its uninstaller, a
  launcher it tells you to run), not one inside its install that a release can move; a pattern
  is refused (nothing is matched against it). With `restart: steamvr`, Frame Tweaks' own install
  after SteamVR started counts, whatever date the installer gave the file
  ([docs/mods.md](docs/mods.md)).
- **`status.sh` exits 1 for "not installed" through `status_missing` (or `status_unload`):** a
  check that stops at a failing command (`set -e`) now shows "status check failed" for a tweak
  Frame Tweaks installed, which stays installed. Add `|| true` where a command may fail
  ([docs/mods.md](docs/mods.md)).

### For contributors
- **Faster checks:** the unit tests run several at a time (`dev/run-tests.py`: a process per
  test file, a slow file in parts, the slowest first), about 45 s instead of 150 on a Frame, and
  `dev/check.sh` leaves out the tweak check when nothing it installs changed since origin/main.
  On a Frame, VR comes first: the checks run at the lowest priority, and while the headset is
  worn, one test at a time on the core VR needs least (on every core, VR stuttered enough to
  make its wearer sick); `FRAME_TWEAKS_CHECKS=vr` or `all` decides instead. CI runs the unit
  tests and the other checks as two jobs side by side.
  Tests that waited a fixed time for something (a window starting its checks, a timer, a program
  writing its first file) wait until it happens: on a busy machine they failed. A test class
  that watches the whole machine sets `run_alone = True` and runs by itself.
- **Ruff** (`dev/check.sh lint`, `ruff.toml`): names that don't exist and unused imports, in
  every Python file (13 unused imports went). Mistakes only, no style.
- **A daily look at the linked projects** (`dev/check-links.py`, `.github/workflows/linked.yml`,
  an issue labelled `linked-check`): a release newer than the one last looked at
  (`lib/tested-versions`), or a README that no longer names the file a link's status checks.
- **Release workflow:** a pre-release takes its notes from `## Unreleased` and leaves the
  section as it is, so the release after it has every change since the last release (the test
  release dated the section, and the release then found none, or only what came after the test
  release). The commit and the tag are pushed together or not at all (`git push --atomic`): a
  tag could be published while main refused its commit.
- **Traffic workflow:** with more than 30 releases it stopped (each page of releases came as a
  list of its own); a failed download of the saved `traffic.csv` went unnoticed, and the upload
  then replaced the history with the last 14 days (it now stops, and never saves fewer days than
  it had); and a failed look for its draft release made a second one.
- **Translations:** a `%` is a placeholder only in a text that's formatted (one with `%s`, `%d` or
  `%%`): `dev/i18n.py import` no longer refuses "1% del" in a tweak's manifest text, and the tests
  now catch "100 % de" (a printf conversion) in a formatted one. Plural forms given for a text
  without a plural are reported instead of stopping the import.
- **`tests/test_gui_window.py`** builds the installer window as it opens, with nothing of the
  machine's run (statuses from a stand-in, no update checks, its settings and packs in a throwaway
  folder), for what only the real window shows: its list as packs change, its narrowest width,
  its error page, closing it.

## 0.6.9 (2026-10-16)

### Added
- **Tweaks are offered only where they're needed:** a tweak's optional `needed.sh` checks what
  the Frame has (a package's version, a file) and says why when it doesn't need the tweak, say
  because SteamOS now does it itself. Such a tweak is hidden in the list (**Show hidden** lists
  it with the reason, its box disabled), and `./install.sh install` skips it, so a fix for one
  SteamOS version doesn't break another. An installed one stays listed for you to remove
  ([docs/mods.md](docs/mods.md)).
- **Screen snip narration: Previous part and Next part,** icons either side of Pause / Resume.
  Narrate reads a part (about a sentence) at a time, and these move a part back or on, from
  its start. While paused, it stays paused on the new part, and Resume reads it from there.
- **NordVPN: Connect at startup:** tick it in the tray's menu, and the location it names (the one
  you're connected to, or else the one used last) connects by itself whenever the Frame starts,
  in VR too, before desktop mode. It's NetworkManager's own autoconnect, kept to that one
  location; ticking it doesn't connect now, and **Pick least-loaded servers** keeps it. In a
  terminal, `nordvpn-wg autoconnect CA` (or `off`); `nordvpn-wg list` and `status`, and the
  tweak's status, say which location connects at startup.

### Changed
- **Mouse cursor fix isn't offered from SteamOS 0.5.6:** its gamescope (3.16.30) has SteamVR draw
  desktop mode's pointer itself, and with the fix you got two, its large one and a black X. On
  those versions it's hidden (Show hidden says why) and, if installed, its status asks you to
  uninstall it; older versions still get it. A tweak's `needed.sh` that fails without saying
  why no longer counts as "not needed".
- **Help make Frame Tweaks better** starts with the quickest help: a star on GitHub, with a
  link to the page and where its Star button is.
- **Battery charge limit swings by 1%, and can stop at 74%, 76% or 78% too:** charging starts
  again 1% below the limit instead of 5%, so at 80% the battery stays between 79% and 80%.
  Paused, the battery still gives a little power (the Frame's charger has no switch that holds
  it still), so the band only sets the size of the swings; research on micro-cycles finds small
  ones add little wear, and a lower limit lowers the average charge. The README has the details.
- **Battery charge limit's README explains desktop mode's battery icon:** while the limit holds,
  KDE says the power supply "is not powerful enough to charge the battery". It's the tweak
  pausing the charging, not the charger. It also says the battery drains slowly while paused.

### For contributors
- **Research notes:** [docs/research/battery-charge-limit.md](docs/research/battery-charge-limit.md)
  records the measurements on a Frame and the studies behind Battery charge limit's decisions
  (the pause as the only working control, the 1% swing, the 74 to 78% limits), and when to look
  again; `sudo bash dev/charge-hold-test.sh` repeats the charger test after a SteamOS update.
  The design notes link it, and now cover `needed.sh` too.
- **The manifest tests no longer overwrite your hidden tweaks:** they wrote their own hidden list
  over the real one (`~/.config/frame-tweaks/installer/hidden`) each time they ran.
- **`dev/test-tweaks.sh` passes on a Frame in use:** what programs already running write to /tmp
  meanwhile (Android Mirror's adb log, a Narrate's sound files) no longer counts as written by
  a tweak outside its test home. Where user namespaces allow, the tweaks' scripts get a /tmp
  and /var/tmp of their own; elsewhere, files that running programs have open are left out.
- **The translation files change only when a text does:** their references name the file a text is
  in, not its line, so editing code no longer makes `dev/i18n.py check` (and CI) ask for the
  template to be extracted again.

### Fixed
- **One wallet password dialog at a time:** Firefox started twice, a link opening it while you
  start it, or a git push beside a `gh` call each opened their own "Unlock wallet" dialog while
  the wallet was locked. Now the later ones wait for the dialog that's open and take its answer
  (unlocked, or cancelled without asking again). The wallet's README also explains why
  KWalletManager can show the wallet closed while it's open.
- **Speech engine installs on SteamOS 0.5.6:** 0.5.6 removed speech-dispatcher (and Orca), and
  installing Speech, or Screen snip + Narrate with it, failed copying its settings. Speech now
  installs as Narrate's voice alone there, and takes out the speech-dispatcher setup it made
  under an earlier SteamOS. Its status no longer says speech-dispatcher uses espeak-ng.
- **📖 README shows all of the README:** after the first paragraph it showed blank lines with only
  bits of code in them. A picture with a caption confused the window's Markdown reader, which then
  dropped the text that came after; pictures with captions are now turned into ones it reads.
  The same happened on tweak pages: NordVPN's showed half its README, cut off at a "<country>" in
  its text (GitHub hid that word too). Every page now gets the same clean-up, a placeholder like
  that shows as written, and a test renders every page to check all of it shows.
- **A tweak's page scrolls as one:** below Back and the title, its facts and its README scroll
  together, so a long table of facts no longer leaves the README a narrow strip to scroll in.
- **Running the install command again over an install opens the window at once:** it updates, as
  `./install.sh update` does, and that re-ran every installed tweak's installer (minutes) even
  when it was on the newest release already. Now an update that changes nothing reinstalls
  nothing, except the tweaks an earlier update didn't finish (one whose installer failed, or
  that was stopped partway); `./install.sh update --reinstall` runs the installers again when
  you want that.
- **⚙ Preferences scrolls to its questions:** **Uninstall Frame Tweaks…** (and deleting leftover
  settings, or going back to the stable release) opens its question below the button, at the
  page's bottom, where it was easy to miss; the page now scrolls to show all of it.

## 0.6.8 (2026-10-16)

### Fixed
- **Setting up the full installer window shows its progress:** PyQt6 (about 280 MB) downloaded
  without a word for a minute or more, which looked like nothing happening, and started from the
  app menu there was nothing on screen at all. Now its progress shows in the terminal, or, from
  the app menu, in a terminal window of its own; the window opens when it's done.
- **The installer never ends with nothing on screen:** if the full window can't open, it says so
  and the simple checklist opens instead. What happened goes to a log that 🐞 Report a problem
  includes.
- **Opening Frame Tweaks when it's already open elsewhere:** open in the other session (VR or
  desktop mode), a notification says so, since that's where it came to the front; a window that
  doesn't answer (stuck) is closed, and a new one opens instead of nothing. (A window still open
  from before this update can't answer yet: the first launch after updating replaces it.)

## 0.6.7 (2026-10-16)

### Fixed
- **Setting up the full installer window no longer reads as if it installed NordVPN's tray:** it
  needs PyQt6, the toolkit the window is drawn with, which Arrow Pad and NordVPN's tray also use
  when they're installed. The question now says that nothing else is installed, and what the
  simple checklist leaves out if you'd rather not set it up.

### For pack authors
- **`formerly:`** in a tweak's manifest lists its earlier ids after a rename: what Frame Tweaks
  keeps under one moves to the new id once, `depends:` on one still finds it, and `./install.sh`
  says what it's called now. In an official pack's `pack.md`, it lists the folder's earlier
  names (Core's `original`).

## 0.6.6 (2026-10-16)

### Fixed
- **The Packs page's tweak lists no longer tag Dictation, Screen snip and Android Mirror sudo
  when Homebrew is installed:** they ask for your password only while it isn't (its installer
  does), as the main list already said.
- **A row's status is checked again after Restart (or any ▶ button), and when you come back to
  the window:** Shared clipboard kept saying "not running" after Restart had started it, because
  the window checked only as it opened (before desktop mode had started it). Its status now also
  tells apart "starts with desktop mode" (desktop mode isn't running: as it should be) from "not
  running, though desktop mode is" (Restart starts it).

### Changed
- **"Original" is now "Core"** (`packs/core/`): Frame Tweaks' own tweaks, and the helpers many
  of them need, other projects' tools credited to their makers (Homebrew, ydotool, Piper); its
  description on the Packs page says so. If you had turned it off, it stays off.
- **Mouse cursor fix and Menu icons move to 3rd Party:** they're fixes others found
  (curiousjtuber's steam-frame-utils, from ThrillSeeker via Cas and Chary XR; lhns's
  steam-frame-nix), which Frame Tweaks applies. 3rd Party's description now covers such fixes as
  well as linked projects.
- **The Packs page says "tweak pack provided by …"** after a pack's name, not just "by …".
- **Wallet apps** lists Frame Tweaks' own apps (Arrow Pad, Dictation, Screen snip, Android Mirror,
  the NordVPN tray, the Frame Tweaks window) as **Frame Tweaks app**, not "Your app".

## 0.6.5 (2026-10-15)

### Changed
- **The Frame Tweaks window:** scroll bars twice as wide (easier to grab with a laser), with a
  rounded handle that lights up as you use it; **Privacy & security** comes just above
  **Developer**; and **Help make Frame Tweaks better** is the list's last row, under every
  group, with a **Get involved** button.
- **Shared clipboard installs in seconds:** it now downloads Frame Tweaks' own build of
  clipboard-sync (about 1 MB, checked against its pinned SHA256) instead of building it on the
  Frame, which took a few minutes and about 600 MB of temporary space. The build is
  [AstronautCheetah/clipboard-sync](https://github.com/AstronautCheetah/clipboard-sync), a fork
  of dnut/clipboard-sync with Frame Tweaks' changes as commits, tested and built by its CI. It
  moves to **Integrations** (3rd Party is now the linked projects). This update switches it, and
  removes the old build's leftovers.

### Added
- **What's in a pack:** on the Packs page, click a pack to see its tweaks, each with its tags,
  summary and whether it's installed; a tweak's name opens its page, and Back returns to Packs.

### Fixed
- **Arrow Pad's Unstick also lets go of keys a keyboard still holds:** a Bluetooth keyboard that
  lost a key's release kept it down for every app (Ctrl stuck), and Unstick's own presses couldn't
  release another device's key. And when desktop mode has taken all input (typing and clicks go
  to the desktop instead of your window), which no key release undoes, it gives it back with a
  Right Ctrl tap and checks; what it found goes to a log that 🐞 Report a problem includes.
- **Check for updates no longer says "up to date" when Frame Tweaks was updated under an open
  window** (in a terminal, say) while the window still runs the older version: it offers ↻ Restart.
  The version in the title is the one the window runs.
- **The Packs page describes 3rd Party as it is now:** linked projects, which update their own
  way; the Original pack's text mentions Battery charge limit's udev rule.

## 0.6.4 (2026-10-15)

### Added
- **Battery charge limit** (new, in a new **Hardware** category, 🧪): charging stops at 80% (or
  85 or 90%; ⚙ on its row) while the Frame is on, and starts again 5% below, so a Frame that's
  often plugged in (to a power bank while you play, say) doesn't sit at 100%. **Charge to 100%
  once**, in its settings, lifts it until the next full charge. Its install asks for your sudo password once, for
  a udev rule that lets you pause charging. Valve Support says leaving the Frame plugged in at
  100% is fine for daily use; this is for a battery that wears more slowly, until SteamOS offers
  its own limit on the Frame, as it does on the Steam Deck.
- **Tweaks that ask for your sudo password are tagged sudo** in the Frame Tweaks window, with why
  on their page (Battery charge limit, and Dictation, Screen snip, Android Mirror and Homebrew
  while Homebrew isn't installed yet), *(sudo)* in the README's tables, and in
  `./install.sh list` and `info`.
- **Test releases for people who try things first:** ⚙ Preferences → **Get test releases too**
  (or `./install.sh channel beta`) makes updates take test releases (`vX.Y.Z-rc.N`) as well.
  Unticked again, you stay on the test release until the next stable release is out, or go back
  to the newest stable one at once (`./install.sh update --to stable`). The install command
  with `FRAME_TWEAKS_CHANNEL=beta` now keeps that choice for later updates; before, the first
  update took a tester back to the stable release.
- **Shared clipboard: files, pictures and the middle-click selection too.** A file copied in a
  file manager pastes as a file in the other session (as a copy, even after a cut), a picture
  (PNG, JPEG, BMP, GIF or WebP, up to 32 MB) as a picture, and text you select pastes with a
  middle-click on the other side (Arrow Pad's **M** key in VR). It now notices copies as they
  happen instead of reading every clipboard five times a second, so a picture copied over
  another is shared too, and it uses next to no processor time in between.
- **Android Mirror: Share the clipboard with the phone** (⚙ Settings, or the gear in VR). On by
  default, as before: what you paste in the mirror goes to the phone, and what the phone copies
  comes to the Frame. Off, each keeps its own.
- **Try someone's pack from its link:** 🧩 Packs → **Add a pack from a link** (or
  `./install.sh mods add LINK`) downloads a pack shared as a git repository into your packs
  folder. As any pack, it isn't used until you trust it. **Update** (`mods update`) brings its
  newer version, which waits until you trust it again; **Remove…** (`mods remove`) deletes it once
  its tweaks are uninstalled.
- **Check for updates looks at packs added from a link too:** it asks where each came from
  (nothing is downloaded) and says how many have a newer version, linking to the Packs page,
  which marks them; Update gets one, as before (`./install.sh mods updates` lists them).
- **Community packs** ([docs/community-packs.md](docs/community-packs.md), and **Packs others
  share ↗** on the Packs page): packs people shared, to add from their links. A
  [Share a pack](https://github.com/AstronautCheetah/frame-tweaks/issues/new?template=share_a_pack.yml)
  issue asks for one to be listed, after a maintainer has read it.

### Fixed
- **Links opened from VR reach Firefox in desktop mode again** (a tweak's README, Its README ↗,
  help links). Firefox said it was "already running, but is not responding": desktop mode has
  its own runtime folder and session bus, where the running Firefox is found, and the link was
  handed over without them.
- **Shared clipboard: cutting or copying a file in desktop mode pastes the file again**, not just
  its address ("Paste Clipboard Contents"). clipboard-sync wrote the text it shares back into the
  clipboard it came from (directly, or through the desktop's own X11 clipboard, which KWin links
  to the Wayland one), replacing what the app had put there. The same happened to formatted
  text, to images that also carry text, and to a password manager's "don't keep this in the
  clipboard history" mark, in desktop mode and in VR. The text now goes only to the other
  session. Reinstall Shared clipboard (↻) to get it; its status says when you need to.
- **Shared clipboard: a copied password no longer stays in the other session.** One its password
  manager marks secret (KeePassXC does) is shared with the mark, so desktop mode's clipboard
  history leaves it out, and when the password manager clears it, the copies are cleared too.
- **Shared clipboard no longer overwrites the clipboard every 10 minutes.** It restarts its worker
  that often, and each start wrote test values, then the first text it found, into every
  clipboard: a file or picture copied but not yet pasted was replaced. Now a start replaces
  nothing; only a clipboard with nothing on it gets the text the others hold.

### Changed
- **Recline is linked** (🔗): Frame Tweaks runs Recline-VR's own installer, as its README gives
  it (cloned into `~/Recline-VR`, then its `install.sh`), instead of building a pinned copy;
  ↻ pulls its latest version. Its row offers ⟳ Restart SteamVR after an install, and now after
  an uninstall too, until SteamVR has restarted (SteamVR runs its driver until then). Its
  setting is gone: Recline-VR always keeps the room view aligned. An installed Recline keeps
  working as it is.
- **Full Keyboard is linked** (🔗): Frame Tweaks runs its own install steps, as its README gives
  them (its newest release and `SHA256SUMS` from GitHub, checked with `sha256sum -c`, then its
  `install.sh`), instead of a release Frame Tweaks pinned. Its row says when TaiKeid publishes a
  newer release, and ↻ installs it; you no longer wait for a Frame Tweaks update. An installed
  Full Keyboard keeps working as it is.
- **VSCodium is set aside** (not offered any more): it's in Flathub, so Discover installs it as well,
  and Frame Tweaks offers only what you can't get there or from Homebrew. An installed VSCodium
  stays, with your settings and extensions (Discover can remove it).
- **An update never moves to an older release unless you ask** (`--to`): with test releases
  turned off, `./install.sh update` keeps the test release you're on instead of going back.

### For pack authors
- **Link a project instead of integrating it:** a manifest's `link:` (install and uninstall
  commands, a path that exists once it's installed, an optional run command and README) makes a
  tweak without scripts: Frame Tweaks runs the project's own commands, as its README gives them,
  and pins, checks and copies nothing. The window marks it 🔗 and links its README; ↻ runs its
  installer again, and Frame Tweaks' updates leave it alone. `restart: steamvr` makes its row
  offer ⟳ Restart SteamVR after an install or an uninstall, until SteamVR has restarted (a status
  script can do the same: `status_restart`, or `status_unload` once uninstalled).
  [docs/mods.md, Linking a project](docs/mods.md#linking-a-project).
- **`sudo:` in a manifest** says when and why installing the tweak asks for the sudo password
  (`homebrew`: only while Homebrew isn't installed); the window tags its row.
- **A pack check for your own repository:** the `check-pack` GitHub Action reads your pack as
  Frame Tweaks does and checks its scripts with ShellCheck. Copy the example pack's
  `.github/workflows/pack-check.yml`; [docs/mods.md, Sharing a pack](docs/mods.md#sharing-a-pack).

## 0.6.3 (2026-10-15)

### Added
- **Recline is back** in 3rd Party (VR environment, 🧪): use VR lying down or reclined
  ([new-waifu/Recline-VR](https://github.com/new-waifu/Recline-VR) v1.2.0, built from its pinned
  source). Set aside in 0.6.2 while it was tested. Its status now says when SteamVR has yet to
  load it, a SteamVR that ran it before included, and offers ⟳ Restart SteamVR.
- **⟳ Restart SteamVR on a tweak's row** while SteamVR has yet to load it (the VR dashboard
  tweaks, installed while SteamVR runs): its status says it waits for a SteamVR restart, and
  the row's Run or Settings button becomes **⟳ Restart SteamVR**, which asks first (every open
  app closes) and then restarts SteamVR with SteamOS's `steamvr restart`.

### Security
- **NordVPN's WireGuard key after uninstalling:** since 0.6.2, uninstalling NordVPN keeps
  `~/.config/nordvpn-wg` (your key and locations) unless ⚙ Preferences say to remove settings,
  but its page and the README still said the key was deleted. They now say what happens. To
  delete one left behind: ⚙ Preferences → **Delete settings left by uninstalled tweaks…**, or
  `./install.sh forget-settings`.

### Fixed
- **Typing into Android Mirror:** a click on the mirror now gives it the keyboard focus, so your
  keyboard and Steam's keyboard type on the phone. The keys went to the window you'd clicked
  before (often the desktop): the see-through layer that takes the mirror's clicks kept the
  focus from moving. It now hands the focus to the mirror, as SteamVR's own grab handle does.
- **Less load on SteamVR from Arrow Pad and Screen snip's narration panel:** they read the
  controllers' grip only while a laser is on them (each read waits on SteamVR's shared property
  lock, which SteamVR and Steam use too), and the narration panel checks for events 10 times a
  second until a laser is on it.
- **Android Mirror coming back after the phone slept** (it reconnects by itself): the new window
  showed in the dashboard, was put back where the mirror floated, and left the dashboard showing
  nothing. The dashboard now goes back to the window it showed before, and the mirror's trip
  through it is shorter.

### For contributors
- `status_restart` in `lib/common.sh`: a status line for something SteamVR loads only as it
  starts, which the window turns into ⟳ Restart SteamVR; `vr_started_before FILE` tells whether
  the running SteamVR started before FILE changed (docs/mods.md).
- Each test file passes when run on its own (`python3 -m unittest discover -s tests -p
  test_i18n.py`), as in the full run: `tests/helpers.py` starts it the way `test_00_english.py`
  starts the suite. Run alone, `test_i18n.py` read the language the installer window had
  announced in this session, and two others couldn't import `lib/`.
- `dev/i18n.py export LANG DIR --review` for a language with no `.po` file yet says so, instead
  of stopping with a traceback.

## 0.6.2 (2026-10-15)

### Added
- **Help make Frame Tweaks better,** the last row of the Developer group: not a tweak, but the
  ways to help (ideas for new tweaks and third-party apps, bug and test reports, translations,
  code, docs), on a page of its own.
- **Uninstalling Frame Tweaks leaves third-party apps installed** (Homebrew, VSCodium, Claude
  Desktop, Claude Code, Full Keyboard, clipboard-sync) unless you choose otherwise in ⚙
  Preferences (`--remove-apps`). Tweaks name such an app in a new manifest field, `app:`.
- **Installing Frame Tweaks again finds the tweaks it left installed**, at the versions recorded
  (now tested).
- **Uninstall Frame Tweaks** from ⚙ Preferences (or `./install.sh uninstall-self`): every tweak
  first, or leave them installed; delete the settings too, or keep them. It removes the menu
  entry, the files the tweaks shared, and its own folder, unless that holds work of yours.
- **Delete settings left by uninstalled tweaks…** in ⚙ Preferences (`./install.sh
  forget-settings`): what tweaks kept when they were uninstalled; installed tweaks' are left alone.
- **Uninstalling: keep a tweak's settings, or remove them too,** a choice in ⚙ Preferences (kept
  by default, as before). The uninstall names what it kept; `./install.sh uninstall
  --remove-settings ID` (or `--keep-settings`) decides for one run. A reinstall (↻) always keeps
  them. Tweaks list where they keep their settings in a new manifest field, `config:`.
- **🐞 Report a problem** (was Diagnostics): saves the diagnostics report, says where, and opens
  the bug form with your version filled in, to attach it to; `./install.sh report` in a terminal.
  The crash page has it too.
- **Haptic ticks on Android Mirror's ⚙ and its settings' buttons,** and on the scroll strips' ⚙
  panel.
- **`arrowpad --fold`** collapses or expands a running pad (for a controller shortcut).
- **Arrow Pad: Collapse / Expand,** a chevron left of Close, as on Screen snip's panel: the pad
  folds to just the chevron, which stays under the pointer (or the laser, in VR), and it
  remembers being folded.
- **⚙ Preferences** in the window, left of Show hidden: the language (follow the keyboard, or
  choose one for every Frame Tweaks program), haptic ticks on the window's buttons, and whether it
  looks for a new release when it opens.
- **Arrow Pad and Screen snip switch language with the window:** it announces a change, and they
  follow (they no longer check the keyboard themselves).
- **Arrow Pad's key legends are translated:** what each language's keyboards print (RePág,
  Inicio, Supr in Spanish); the mouse keys show the initial of "Right" and "Middle" in your
  language (D and C in Spanish).

### Changed
- **A feature whose tweak isn't installed says so where you'll see it:** Arrow Pad's 🎤 and Snip
  buttons, and Screen snip's Narrate and Copy text, show a dialog (in VR too, where a
  notification goes unseen) saying what's missing, with **Open Frame Tweaks**, which opens on that
  tweak's page to install it. `./install.sh gui --show ID` does the same.
- **⚙ Preferences reads more clearly:** the uninstall options come last, below a line; what
  happens to the tweaks when Frame Tweaks is uninstalled is one choice of three (keep
  third-party apps, remove everything, or leave the tweaks); explanations no longer show
  "&#x27;" for an apostrophe.
- **Uninstalling NordVPN keeps your key and locations** (`~/.config/nordvpn-wg`) unless ⚙
  Preferences say to remove settings: it used to remove them, so setting it up again took a new
  access token.
- **Screen snip's VR panel has rounded corners,** like Arrow Pad's.
- **Spanish: a second pass.** Frame Tweaks' own tools and tweaks have Spanish names (Teclado de
  flechas, Teclado completo, Espejo de Android, …), and what the text names in SteamVR, KDE,
  Android or Claude uses their own Spanish wording ("Flotar en el mundo", "Preferencias del
  sistema", "Depuración inalámbrica").

- **Packs you trusted need trusting once more** (**🧩 Packs → Trust…**): trust now also covers a
  pack's links and which of its files can run, and two different packs can no longer share a
  fingerprint.
- **A failed removal says so:** a tweak whose uninstall fails is reported like a failed install
  ("!! … failed"), keeps its version record, and stops the window's Apply before it installs
  anything else.
- **NordVPN's ↻ Reinstall keeps your setup:** its connections, key and locations stay, and the VPN
  stays connected (removing it still deletes them).
- **Two more services are sandboxed:** app timers can't write your home folder any more, and the
  unit that relabels the menu entries in your keyboard's language can write only Frame Tweaks'
  menu folders (no network, a private `/tmp`).

### Removed
- **Controller buttons in the installer window** (VR: B back, Y to the top, A ticks a row, the
  left D-pad through the rows), and their ⚙ Preferences option: they don't work reliably yet. The
  window no longer claims those buttons while the laser is on it; its haptic ticks stay.
- **Recline** is set aside for now (not offered while it's tested). Installed, it stays until
  you remove it.

### Security
- **An update takes only a release signed with Frame Tweaks' SSH release key, on a tag that
  carries its own name.** A PGP-signed tag was checked against your own GPG keyring instead,
  and an older signed release could have come back under a newer one's name.
- **A pack can't stop your whole session:** a manifest's `processes:` written as text instead of
  a list made the installer stop every program matching each of its letters. Settings files are
  written quoted (a value with a space in it ran a command when the file was read), a pack's
  settings file has to stay under `~/.config`, and `mods trust NAME` refuses a name two packs share.
- **Android Mirror's pairing code** no longer goes on adb's command line, where any program could
  read it.
- **The diagnostics report** removes the whole phone name, also one with `( ) + ?` in it.
- **VR dashboard patching** can't reach a running SteamVR from outside your own setup any more (a
  test's throwaway home stopped the live dashboard's patches).
- **Running the install command again** on a Frame that has Frame Tweaks updates it as
  `./install.sh update` does, signature check included: it used to move to the newest release
  without the check, and without running the installed tweaks' installers again.

### Fixed
- **Links with "Install Chromium" as the default browser:** SteamOS's placeholder (it only opens
  the software store) was taken for a browser. Frame Tweaks now checks that the default browser
  is one (any: Firefox, Chromium, Brave, …) and installed; if not, it opens links in an installed
  browser, a running one first, and says how to set a default. A shell-wrapped launcher no
  longer counts as running whenever any shell is.
- **A floating Android Mirror stays where you put it** after Restart stream, or after it
  reconnects by itself: the new window goes back to the old one's place (it came back elsewhere
  when the new window came up floating rather than docked).
- **Android Mirror's ⚙ on an upright mirror docked in the dashboard** sat on the dashboard's own
  Show Keyboard button (their row under a docked window is wider than so narrow a window): it's
  now beside the window's lower left corner there, with its settings to the left of it.
- **Android Mirror after "Restart stream":** its "Connecting…" window could stay open, taken for
  the mirror and floated over it, so the mirror's handle couldn't be grabbed. Android Mirror's
  own windows now have a title of their own ("Android Mirror setup"), and that window is always
  closed (stopped, if it doesn't answer).
- **Less CPU while idle:** Arrow Pad's VR panel checks 5 times a second instead of 45 while the
  dashboard is closed; the window checks for background jobs' results once a second when none
  is running.
- **Uninstalling a tweak whose menu entry the wallet guards** (Arrow Pad, Screen snip, NordVPN,
  Dictation, the wallet, Full Keyboard) no longer leaves the entry's kept copy behind, and
  uninstalling Screen snip stops a running Screen snip.
- **A damaged settings file** (Arrow Pad's or Screen snip's, not a JSON object) no longer stops
  them from starting; settings files are written whole, so a crash can't leave half of one.
- **The window's haptic ticks in VR** no longer stop for good after an error; **Arrow Pad's
  haptics log** no longer grows without end.
- **"Update available" for an app** no longer takes a release candidate (1.2.0-rc1) for newer
  than its release.
- **The window's wallet page** shows the auto-lock settings the wallet really uses.
- **Arrow Pad's Collapse didn't keep the chevron under the laser** when pressed (the button's
  click handed a "False" to the setting that keeps it in place).
- **A link the browser in desktop mode doesn't take** (Firefox: "already running, but is not
  responding", while desktop mode isn't shown) no longer leaves that message up: after a few
  seconds the window stops it and puts the link on the clipboard. Links opened are logged for
  the diagnostics report.
- **The scroll strips had no haptics:** SteamVR's dashboard kept an older copy of the shared
  helpers, without the haptic call (a version number hadn't been raised). The dashboard now gets
  each new copy of them by its content.
- **Screen snip's panel mixed languages** after a switch: its buttons, labels and state line
  follow now, not only the tooltips.
- **A program opened while the window was open could start in another language** (the one it
  was handed when started): it now takes the window's.
- **Arrow Pad in VR crashed when closed** with its ✕ (it read SteamVR's events after
  disconnecting).
- **Arrow Pad in VR closed at once** after the language change above (its VR panel asked for a
  setting that had moved).
- **Pasting a snip's image gave its HTML as text** (`<img src="data:…`) wherever the Shared
  clipboard had carried it: clipboard-sync took the image's HTML form for text. It now shares only
  plain text, so the image stays an image (an update rebuilds Shared clipboard with the fix).
- **The window mixed English and Spanish** when it was started by something that passed on
  another language: the tweaks' titles and descriptions were read before the window chose its own.
- **Status lines stayed in English** when the window was in Spanish: the window passed on the
  language the installer found when it opened it. It now passes on its own, and checks the
  statuses again when the language changes.

- **Unticking Arrow Pad, Screen snip or NordVPN deleted the installer window's own Python** while
  it ran, and its next start offered the 280 MB download again.
- **Closing the installer window stopped an install** running in its Konsole. Offline, ⟳ Check
  for updates said "up to date"; beta users weren't offered betas (the channel was read from the
  wrong folder); ▶ ran for real in a dry run.
- **App timers could quit the wrong programs,** the desktop session's own among them: an app
  started through a shell or Python was found by that program.
- **Wallet apps:** protecting an app replaced your own edit of its menu entry; reinstalling a
  tweak whose app you'd protected failed; Password first could be skipped for an app started
  over D-Bus; some Electron apps didn't start; the gh token's move could stop the install.
- **Arrow Pad kept a key held down** after a grab, the dashboard closing or Close (it went on
  repeating in your app), and crashed after ydotoold restarted, on 🎤 without Dictation and
  after a language change. Its VR panel was mirrored without a dashboard, and the German, French
  and Italian key legends didn't show.
- **Dictation could start recording by itself** when a recording had ended on its own, and type
  what it heard into your window five minutes later.
- **Screen snip:** "Read it again" took two presses; a speed change while paused went silent; a
  clipboard that didn't answer crashed the panel.
- **Android Mirror** took "Pixel 9 Pro" for a saved "Pixel 9", could wait for ever looking for
  phones, kept its splash up after a reconnect, and used much of a processor core for joystick
  scrolling.
- **Firefox privacy** couldn't be removed after a `user.js` without a final newline, and half a
  marked block could delete your own prefs.
- **Shared clipboard** left about 350 MB of build files behind; **Desktop Recovery** didn't
  restart a frozen taskbar.
- **VR environment tweaks:** "Gap 0 cm" gave 1.5 cm; installing in VR said the patches were active
  when SteamVR needed a restart; an unreadable note could leave SteamVR's DevTools port on after
  uninstalling; one malformed call stopped scrolling and VR settings until SteamVR restarted.
- **Speech engine** downloaded the English voice again (without its fallback) when only the
  engine had been chosen.
- **`./install.sh install all`** skipped migrations; **get.sh** stopped without a word when it
  found no release; `FRAME_TWEAKS_LANGUAGE=en_US` didn't mean English.

### For contributors
- **dev/i18n-terms.py** collects the official wording of other software (SteamVR, Steam, Android,
  Claude Desktop, KDE) for a language's glossary, and checks a translation against it.
- **dev/check.sh** runs every check CI runs, on any Linux PC (CI now calls it, step by step); a
  check whose tool is missing is skipped with a hint. CONTRIBUTING.md starts with what needs a
  Frame and what doesn't, the setup, a glossary and the environment variables. A pull-request
  template, a **Works on my Frame** issue form and `.editorconfig`.
- **CI checks what it missed:** the sourced shell libraries, every pin, each pack's manifests one
  by one. `dev/test-tweaks.sh` runs without network and catches writes into its copy of the repo.
  The tests clean up after themselves and no longer touch a running session (a mirror's pid
  file, the language the window announces, the user's systemd).
- **Manifests are read more strictly:** what YAML readers read differently (keys like `on:`,
  `? `, `:` or `#` inside `[...]`, tabs) is refused with its line number (docs/mods.md, "The YAML").
- **Licences, in full:** `dev/draw-icons.py` draws the Breeze-based menu icons (their source, as
  Breeze's licence asks: it reproduces them exactly), and icons/README.md says which glyph and
  colour each is; the Breeze icons' licence is LGPL-3.0-or-later (LICENSES/ renamed to match);
  Arrow Pad's icons ported from Full Keyboard carry its whole MIT notice; the upstream READMEs
  reproduced on Full Keyboard's and Shared clipboard's pages say whose they are and their
  licence. CI runs on Ubuntu 24.04 by name, not whatever "latest" is.

## 0.6.1 (2026-10-14)

### Added
- **Español (Latinoamérica):** the first translation: the window, the installer's messages, and
  the tweaks' own programs (Arrow Pad, Screen snip + Narrate, Android Mirror, the wallet tools).
- **Spanish menu entries and VR panels:** the tweaks' menu entries (desktop menu and Steam's
  "+" menu) open in the keyboard's language, as chosen before the menu opened; the scroll strips'
  and Android Mirror's ⚙ panels in SteamVR's dashboard follow it like the window.
- **The language follows your keyboard:** Steam's VR keyboard in VR, KDE's layout in desktop
  mode. Switch to a Spanish layout and the window follows within 5 seconds (once you're on its
  list); programs pick it up when they start. A QWERTY or English layout keeps the system's
  language. `FRAME_TWEAKS_LANGUAGE` still chooses one outright.
- **Screen snip + Narrate settings:** a ⚙ on Narrate's panel (engine and language, with Apply),
  and a ⚙ beside its Snip button in the window (reading speed, engine, language).
- **Speech engine settings:** Narrate with Piper or eSpeak NG, in one of 18 languages (each
  voice pinned and checked), from the ⚙ Settings button on its row.
- **Android Mirror: Pair it again.** When it can't connect because the phone forgot the Frame, it
  offers to pair again: it finds the phone's pairing dialog on the Wi-Fi and asks only for the code.
  Or it can forget the phone.
- **Android Mirror shows what it's doing:** a small window while it finds and connects to the
  phone (with Cancel), and a message saying why when it can't, such as no phone on the Wi-Fi,
  a phone not paired yet, or scrcpy failing to start, instead of failing silently.
- **Scroll strips: haptics** from the dashboard's own effects: a tick when the laser reaches a
  strip, a firmer one on press and on a page, and light ticks while it scrolls. A **Haptics** tick
  box in its settings turns them off.
- **Scroll strips' colours as circles** in the window's settings, the same colours as its ⚙ panel
  in VR.
- **Haptic ticks** on the Frame Tweaks window's buttons and on Screen snip's narration panel, as
  on Arrow Pad: a light one when the laser moves onto a button, a firmer one on a click.
- **Signed releases:** release tags are signed, and `./install.sh update` refuses a release that
  isn't signed by the key your copy already trusts.
- **⟳ Check for updates** in the window, next to README: it becomes **⬇ Update to …**, then
  **↻ Restart** once the new version is in place.
- **📖 README** next to Diagnostics shows Frame Tweaks' own README in the window.
- **Screen snip's narration panel: grip to carry it,** as on Arrow Pad and Full Keyboard: squeeze
  while pointing at it, let go to put it down.
- **Android Mirror: Forget phone** in its settings: it stops connecting to the remembered phone
  by default (`phone --forget`). Its README now lists what to turn on in the phone, and what
  Wireless debugging allows.
- **Wallet apps: Auto-lock** can be turned off: the wallet then stays unlocked until you lock it.
- **Each pack shows a short description** on the Packs page and in `./install.sh mods`.
- **Every row shows a tick box**, empty when the tweak isn't installed, so it's clear where to
  click.
- **Tweaks that install another project show its own README** below ours, after a separator,
  on GitHub and in the installer window (Full Keyboard, Recline, the shared
  clipboard).
- **Screenshots on details pages:** pictures in a tweak's README now show in the installer
  window too. Arrow Pad's shows its main and Tools layers.

### Removed
- **whisper-frame, Screen reader, Memory caps and Grab guard** are no longer offered.

### Changed
- **Three official packs: Original, Integrations and 3rd Party.** Frame Tweaks' own tweaks are
  in **Original**; other projects' apps that Frame Tweaks fits to the Frame (Signal, NordVPN,
  VSCodium, Claude Code, Claude Desktop) are in **Integrations**; the ones installed as they are
  (Full Keyboard, Shared clipboard, Recline) are in **3rd Party**. All are on; each can be turned
  off on the Packs page or with `./install.sh mods off NAME` (`on` to use it again). In the
  repo, `packs/official/` became `packs/core/`, `packs/integrations/` and `packs/third-party/`.
- **Screen snip's narration panel:** a **Snip** button (Arrow Pad's icon) starts a new snip that's
  read in the same panel; Stop / Again, Pause / Resume, Paste and Close are icons (named in their
  tooltips); the "drag here to move" bar is gone (move it with the grip, or drag an empty edge).
- **Tools is now Desktop Recovery**, described as what it is: an as-needed fix for a desktop
  whose taskbar has gone missing.
- **Install, update and removal terminals in VR** also say you can close them with the X button
  floating below the window, for when there's no keyboard.
- **"Frame Tweaks is up to date"** shows in green.
- **The main README lists the tweaks by category**, as the window does.
- **Screen snip's narration panel:** Collapse shows a down chevron, Expand an up one.
- **The Shared KDE wallet and Firefox privacy rows lead with what they're for:** password-protect
  the apps you choose; make Firefox harder to track.
- **Every tweak's README reads the same way:** what it is and why on a Steam Frame, how to
  install and use it, then what it changes on your system (this was the "At a glance" box), and
  credits. Each was checked against the code; the main README now opens with what Frame Tweaks
  is and why.
- **Wallet apps: ⏱ Extend timer** (next to Lock now) restarts the auto-lock countdown, and
  **Auto-lock after unlocking** sets its length (1–24 h; default 4 h).
- **Wallet apps is the Shared KDE wallet row's button** (🔑 Wallet apps) instead of a button at
  the top; its page still locks and unlocks the wallet. **Diagnostics** moved next to Apply
  changes.

### Fixed
- **The NordVPN tray icon could vanish:** started from VR (the window's Tray button, the "+"
  menu), the tray ran where there's no system tray, and kept desktop mode's own copy from
  starting. It now always runs in desktop mode, or says to open desktop mode.
- **Arrow Pad's haptics stopped:** SteamVR refused its SteamVR Input vibration
  (InputError_InvalidHandle), which aborted the direct pulse that actually reaches the controller,
  and then switched haptics off for good. The direct pulse now goes first; errors are noted in
  `/run/user/<uid>/arrowpad-haptics.log` and retried.
- **Screen snip's narration panel came back in the wrong place** after collapsing it with the
  other end's Collapse button than the last one used.
- **Mouse cursor fix said "active after the next reboot"** when it was already active (the check
  looked at the installer window's session, not desktop mode's).
- **Uninstalling Arrow Pad or the NordVPN tray broke Screen snip** (they share a Python setup);
  now the last one removes it. Screen snip installs `wl-clipboard`, which its Copy text and
  Paste need.
- **The installer's log cleanup deleted Grab guard's log.**
- **Open packs folder** opened Kate when the installer window was floating in VR: folders and
  files now open in their default app as desktop mode sets it (Dolphin), wherever it's running.
- **A tweak's README on its details page** showed in a smaller font than the rest of the window.
- **Arrow Pad's README** showed an old layout; it now shows the three layers, and Dictation's
  README points to **Tools → 🎤**.

## 0.6.0 (2026-10-14)

### Added
- **Packs: add your own tweaks without changing Frame Tweaks.** Every tweak is now a folder in a
  pack, described by the YAML front matter of its README.md; Frame Tweaks' own tweaks are the
  official pack (`packs/official/`, moved from the top folder) and load the same way. Put other
  packs in `~/.local/share/frame-tweaks/packs/` and trust them (the window's **🧩 Packs** page,
  or `./install.sh mods`); a changed pack needs trusting again, and a pack's tweak replaces an
  official one only if it says `replaces: true`. Guide: `docs/mods.md`; example:
  `examples/hello-pack/`.
- **Recline** (new, VR environment, 🧪): use VR lying down or reclined. One button (or a
  controller shortcut) makes your view level and forward; it undoes itself when you get up.
  Builds [new-waifu/Recline-VR](https://github.com/new-waifu/Recline-VR) v1.2.0 from its pinned
  source; restart SteamVR after installing. A setting leaves out its room-view fix, which adds a
  library to the Frame's camera service.
- **📋 next to every link** in the installer window (sources, documentation, known issues and
  each tweak's README) copies the link instead of opening it.
- **Android Mirror asks which phone:** with several advertising, a list to choose from (it's
  remembered); when the remembered one isn't in sight, wait for it or use one that is. **Choose
  phone…** on its menu entry (or `phone --pick`) chooses again.
- **Frame Tweaks keeps its own copies of the pinned downloads** (Full Keyboard, whisper-frame,
  the Whisper model, the voice, rustup, Homebrew's installer, clipboard-sync's source, Recline-VR's
  source) on a `mirror` release, each with its licence texts. If upstream deletes or changes a
  file, installs use the copy, checked against the same SHA256. Piper isn't copied: it bundles
  espeak-ng (GPL-3.0), whose source would have to be hosted with it. New README section: **If
  updates stop**.
- **Weekly upstream check** (a GitHub workflow): one issue lists what changed or vanished
  upstream (pinned downloads, Arch Linux ARM packages, Homebrew's scrcpy) and newer versions to
  take; `dev/bump-pin.py` moves a pin (version, URL, checksum) in one command.
- **🧪 Experimental** marks the tweaks that rely on SteamVR's internals (the VR environment
  tweaks and Android Mirror's VR extras), in the README, the installer window and
  `./install.sh list`.
- **`./install.sh menu --remove`** takes out Frame Tweaks' own menu entry and icons (README,
  *Remove everything*).
- **[docs/DESIGN.md](docs/DESIGN.md):** how Frame Tweaks works and why.

### Changed
- **Web links open in your default browser where it's already running** (desktop mode or VR);
  if it isn't running, it opens in VR, and a tip says where it went (`lib/browser.py`;
  `python3 lib/browser.py --where URL` shows the choice without opening anything).
- **The "VR windows" group is now "VR environment".** If you had folded or hidden it, it stays
  that way. The details page shows the same "what" and "why" as each tweak's README.
- **The version shows the exact build** between releases (e.g. `0.5.0+15.bca47ad`, `-dirty` with
  local changes): `./install.sh --version`, the window title, logs and debug-info. A release
  shows just its number.
- **Updates replace programs instead of writing into them**, so a wrapper that's running while
  you update (adb, arrowpad, gh, the speech module, the Python tools) can't run half old, half
  new; Android Mirror's adb is swapped in only once the new copy is complete.
- **Updates are sturdier:** `./install.sh update` and `get.sh` take GitHub's release tags as
  they are, and a checkout of `main` that can't fast-forward says how to catch up.
- **Fewer surprises when upstream moves on:**
  - **Android Mirror with an untested scrcpy** (a new major version from Homebrew): its VR
    extras switch themselves off, with a one-time notice, and the window stays a plain 16:9
    one where laser clicks land right. Its status says so.
  - **adb and ydotool:** a new Arch Linux ARM build that needs newer system libraries than
    SteamOS has is no longer installed over a working one.
  - **Python packages:** if the pinned versions can't be installed (say, SteamOS moved to a
    newer Python), the newest ones are installed instead, with a warning.
- **debug-info includes the tweaks' services' recent log lines** and which release installed
  each tweak; the README says where every log is.
- **All settings under `~/.config/frame-tweaks/`:** Android Mirror's `phone.conf` and
  Dictation's `dictate.conf` move there from `~/.config` (on the next `./install.sh` run, or
  the next time `phone` / `dictate` runs).
- **The shared clipboard no longer needs Homebrew's Rust (3.4 GB with its LLVM):** it's built
  with a pinned Rust toolchain in a temporary folder that's deleted afterwards. Homebrew's Rust
  from older versions stays; the installer says how to remove it (`brew uninstall rust && brew
  autoremove`).
- **Dashboard patches share one helper file** (`vr-dashboard/lib.js`, injected first). Scroll
  strips, Android Mirror's two patches and Pick up when floating use it instead of their own
  copies.

### Fixed
- **Links in the installer window failed with "Firefox is already running, but is not
  responding"** when the window was floating in VR and the browser was open in desktop mode.
- **Links in a tweak's README on its details page** pointed nowhere when they were relative,
  and Markdown links in its "What it is" and "Why" showed as raw text.
- **Installing the Firefox settings reported a failure** whenever Firefox wasn't running, and
  its status said "not applied" for profiles in Firefox's older folder (`~/.mozilla`).
- **Migrations ran when going back to an older release;** they now run only on the way up.

### For contributors
- **Translations can be contributed:** gettext `.po` files in `locale/` (template
  `locale/frame-tweaks.pot`, made by `dev/i18n.py`; guide in `locale/README.md`). The window's
  buttons and labels and the official tweaks' names, descriptions and settings are ready to
  translate; untranslated text stays English.
- A settings page can include another tweak's settings (`include:`), and a row with both a Run
  action and settings shows a ⚙ beside Run.
- Settings can have tick boxes (`checkbox: true` on a two-choice option) and buttons that run one
  of the tweak's scripts (`actions:`); see docs/mods.md.
- Attribution lines in commits are up to each contributor; the hooks refuse tool attribution
  only for those who opt in (`git config frame-tweaks.refuseToolTrailers true`).
- Commit messages follow Conventional Commits, checked by commitizen in the commit-msg hook and
  CI (`.cz.toml`, `dev/check-commit-msg.sh`).
- `components.tsv`, the `meta` and `processes` files and the `# label:` lines are gone (all in
  each README's front matter); scripts use `$TWEAK_DIR`, `tweak_dir ID` and `$FRAME_TWEAKS_LIB`.
- `write_file` in `lib/common.sh` replaces a file by rename; CI refuses writing into programs.
- A git-commit pin can follow upstream's releases (`latest=` a releases URL); pins with a copy
  list their licence texts (`license_file=`).
- Tests: Arch Linux ARM package checks with real signatures, migrations, holds and the install
  lock, the version string, Firefox's settings and NordVPN's status; quiet test output.
- The installer window's Wallet apps page moved into `gui/wallet_page.py`.

---

Older releases (0.5.0 and earlier): [docs/changelog-0.x.md](docs/changelog-0.x.md).
