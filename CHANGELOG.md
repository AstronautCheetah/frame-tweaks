# Changelog

## Unreleased

### Changed
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
  repo, `packs/official/` became `packs/original/`, `packs/integrations/` and `packs/third-party/`.
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
## 0.5.0 (2026-10-14)
- **README:** what some tweaks can do on your Frame (the DevTools port, the virtual keyboard, key
  monitoring), Requirements, and Remove everything (new `./install.sh uninstall all`); the
  "home folder only" claim names its two exceptions (Homebrew, NordVPN).
- **SECURITY.md** now matches the code: any local program (Flatpaks included) can use the
  dashboard's DevTools port; the wallet gates menu entries, not the apps themselves; the actual
  sandboxing of each service; NordVPN's key file and adb's pairing keys as the plain-text
  exceptions; how downloads, Python packages and tags are (and aren't) verified.
- Tweak READMEs use `./install.sh install <id>` (`./install.sh wallet` is now the wallet command).
- **Fixed: `./install.sh update` (and the installer window's Update) stopped halfway** with
  "Another Frame Tweaks install… is running": its own log writer kept the install lock when it
  restarted itself for the second stage.
- **adb's server is private:** it listens on a socket file in your runtime folder instead of
  TCP 127.0.0.1:5037, which any local program (sandboxed Flatpak apps too) could use to get a
  shell on a connected phone. phone-touch's tunnel to the phone is a socket file too.
- **Android Mirror remembers your phone:** with no `PHONE_NAME` set it connects only when one
  phone is advertising, and then remembers it; with several, it asks which.
- **Arch Linux ARM downloads:** HTTPS mirrors only, the signed package's own name is checked,
  and a version older than one installed before is refused (`ALARM_ALLOW_DOWNGRADE=1` overrides).
- **Homebrew's installer is pinned** to a reviewed commit and checked against its hash
  (`homebrew/pin`) before it runs.
- **One name: Frame Tweaks / `frame-tweaks`.** The installer window's settings move from
  `~/.config/steam-frame-tweaks` to `~/.config/frame-tweaks/installer` (the update channel to
  `~/.config/frame-tweaks/channel`), and `~/.local/state/steam-frame-tweaks` into
  `~/.local/state/frame-tweaks`, on the next run of `./install.sh`. Firefox's `user.js` block
  is marked `frame-tweaks` (the old block is removed).
- Fixed: NordVPN's status said "not installed" with no locations set up; `wallet-unlock --lock`
  reported success when locking failed; uninstalling Firefox's settings left them in `prefs.js`
  (now reset there too, while Firefox is closed); `debug-info` now also removes MAC and IPv6
  addresses and your phone's name.
- Dashboard patches check SteamVR's code with stable names (not minified ones that change with
  every SteamVR build), and the test finds every patch by itself.
- **Contributing from outside:** fork and open a pull request (CONTRIBUTING.md, "Sending a
  change"). The commit check (`dev/check-trailers.sh`, used by the hooks and CI) now refuses only
  AI attribution, so human `Co-authored-by` lines, including GitHub's on squash merges, are fine.
  CONTRIBUTING also lists every check CI runs, what the tests need, and an example `meta`.
- **Fixed: settings changed with the scroll strips' gear in VR weren't saved** (the dashboard
  service wasn't allowed to write `~/.config/frame-tweaks`).
- **Every installer-window function has a command:** `./install.sh info`, `run`, `settings`
  (show, change, `--reset`), `hide`/`unhide`, `hide-group`/`unhide-group`, `wallet`,
  `wallet-apps` and `timers`. The window now uses the same code (`lib/sft.py`) for hidden rows,
  details and settings, so the two can't drift apart; tests check the VR gear panels offer the
  same choices.
- **Android Mirror has a settings page in the installer window** too (same choices as its gear).
- **Scroll strips' settings page** offers all the choices the gear in VR does (sizes, colour).
- **Fixed: scroll strips, gears and settings panels jittering, and the bottom of a settings panel
  missing.** They're drawn from the dashboard's one shared page, placed after its own content, so
  they moved whenever that changed size (its buttons grow under the laser), and a tall panel ran
  off the page. They now sit in fixed corners of the page, and the settings panels are drawn
  smaller there (same size in VR).
- **Fixed: reinstalling VR windows removed other tweaks' dashboard patches** (Android Mirror's
  size and touch layer, so it came up huge with no gear): a reinstall now keeps them.
- **Scroll strips: the gear and its settings sit as far back as the strips.**
- **Scroll strips settings in VR:** a gear where the two strips meet opens their settings beside
  the window: sides, thickness, gap, set-back and colour (the passthrough tint, or a hue of your
  own). The VR windows helper's service saves them (new `sftConfig` call; reinstall VR windows).
- **Android Mirror: Restart stream keeps a floating mirror where it was** (the new window used to
  open docked in the dashboard), with its settings panel still open.
- **Fixed: scroll strips and the Android Mirror's gear and settings jittering** while the laser
  crossed SteamVR's buttons below a window: each dashboard redraw handed SteamVR fresh copies of
  them. They're now reused while nothing they show has changed.
- **Android Mirror settings in VR:** a gear below the mirror's lower-left corner opens the real
  settings: picture size, bit rate, frame rate (30, 60 and the Steam Frame's refresh rates, 72 to
  144) and joystick speed; *Restart stream* applies them without closing the mirror, and *Reset to
  defaults* goes back to 1024 px, 2 Mbit/s, 60 fps.
- **Scroll strips scroll the Android Mirror's phone** (their arrow keys went to the dashboard's
  window: clicks on the mirror go to its touch layer, so the Steam session never saw it clicked).
- **Fixed: joystick scrolling on the mirror stopping** after a click whose release went missing.
- **Android Mirror keeps up with the phone better:** it streams 1024 pixels at 2 Mbit/s (was 1920
  at 8), still sharp in VR; settable in `~/.config/phone.conf`.
- **Android Mirror: the joystick scrolls the phone** while the laser rests on it. SteamVR
  doesn't hand the joystick to the click layer, so it's read from the controller model's
  thumbstick, the way Arrow Pad reads the grips.
- **An upright window docked in the dashboard has a standard window's height** (the upright
  mirror came out over 2 m tall unless you floated it).
- **Fixed: laser clicks on the upright Android Mirror landed at its left edge.** The Steam session
  maps the laser wrongly on a window narrower than its screen. Now a see-through layer over the
  mirror (a dashboard patch) takes the laser, and `phone-touch` sends your presses, drags and
  long-presses to the phone as touches through a second, control-only scrcpy server, so they land
  where you aim, upright or sideways, curved or flat. The mirror window is now titled
  "Android Mirror" (the patches recognise it by that).
- **Turning the phone resizes the mirror at once** (was about a second later): phone-fit and the
  dashboard patch check 20 times a second, and the patch no longer waits for the shape to settle.
- **Android Mirror starts upright at a sensible size** (0.8 m tall), and turning the phone just
  turns the window (0.8 m long side either way): SteamVR starts every floating window as wide as a
  standard one and keeps that width, so the upright phone came up over 2 m tall. The dashboard
  patch now sets the panel height through the dashboard's own override (scaling the window was
  ignored).
- **Fixed: scroll strips the wrong length after a window changed shape** (the phone mirror turned):
  they now read the window's current size from its overlay, not the dashboard's stale copy.
- **Grab guard also hears keys that skip the input devices** (faked by an X program, or typed
  through libei like Full Keyboard), so its log can name where a stray Right Ctrl came from.
- **Grab guard** (new, System): desktop mode takes every key and click after a Right Ctrl press,
  and other windows (this installer too) just stop responding. Grab guard notices, shows a
  notification saying to tap Right Ctrl once, and logs which device sent it.
- **Screen snip from Steam's "+" menu works:** Steam starts it as a game, and the selection window
  then took no laser input; it now starts itself again as a plain program, like Arrow Pad's key.
- **The installer window records a freeze:** if it stops responding for 10 s, where it was stuck
  goes to `~/.local/state/frame-tweaks/logs/gui-hang-*.log`. A status check can no longer hang
  for good (1 minute limit), and Lock now no longer waits on the wallet.
- **New Accessibility group** in the installer window: Dictation, whisper-frame, Arrow Pad, Screen
  snip and Screen reader moved there from Convenience.
- **Android Mirror: no more black bars beside an upright phone.** The window has to fit inside
  the 1920×1080 screen (485×1080 upright), or the Steam session shows it as 1920×1080 anyway;
  upright and sideways now come out about the same size in VR.
- **Android Mirror reconnects by itself** when the wireless connection dies (e.g. after the phone
  switches profile or address), instead of showing a frozen picture: it checks the phone answers
  every 5 s and reconnects at its current address.
- **Scroll strips sit a little behind the window** (3 cm), so SteamVR's own buttons at the
  window's edge, like Enter Gamepad Mode above it, draw in front instead of through the top strip.
- **Fixed: Copy image didn't paste** (e.g. into OnlyOffice). The Shared clipboard tweak's
  clipboard-sync shares text only and put the last text back over a copied image a moment later;
  it's now built with a small patch that leaves a clipboard without text alone, and starting it
  stops any copy left over from a restarted desktop (two were running). Copy image now also
  offers PNG, BMP and HTML, so more apps accept it.
- **Narration panel: Collapse on both sides.** An icon-only Collapse at the bottom left, besides
  the one at the right; Expand comes back with the icon you used in place, so it can tuck away
  toward either side. Copy image, Copy text and Paste are centred.
- **Fixed: a static-like flicker over Collapse** while the panel changed size (the old picture
  was briefly stretched to the new size).
- **Fixed: the narration panel's image disappeared** after Show text (and for a later snip).
- **No Steam flash after a snip:** when the shown window closes, Back to the previous window now
  makes the dashboard's own choice of what to show next, so it goes straight back to the desktop
  (or wherever the snip came from).
- **Collapse keeps its icon in place:** the icon is on the right of the button, and collapsing or
  expanding keeps it exactly where it was.
- **Screen snip narration: Show text / Show image and Copy image.** The panel shows the snip's
  image or the text read from it; Copy image sits beside Copy text; Close and Collapse swapped,
  Collapse has a large icon, and the collapsed panel is just an Expand icon.
- **Screen snip narration: Copy text and Paste.** Copy puts the text being read on the clipboard;
  Paste reads the clipboard's text instead (shown in place of the snip). The panel's buttons are on
  two rows, so they no longer overlap on narrow panels.
- **Screen snip narration: one panel, and Collapse / Expand.** Narrating another snip while the
  panel is open reads it there, in place; Collapse shrinks the panel to an Expand button (reading
  carries on), keeping its top edge where it was.
- **Screen snip narration: Pause / Resume**, and the panel sits relative to the dashboard (it
  starts beside Arrow Pad, under the dashboard bar, follows the dashboard, and remembers where you
  drag it).
- **Screen snip: the narration panel is its own VR panel** (drawn like Arrow Pad and Full Keyboard)
  instead of a window: a compact size, no place in the dashboard (no more flicker with Back to the
  previous window), movable by its top bar.
- **Scroll strips follow SteamVR's Camera Color Tint** (their border, knob and pressed colour use its
  hue, and change when you change it).
- **Screen snip: Narrate pops out and has a speed control.** Narrate opens a small window with the
  snip and its controls (Stop / Again, speed, Close) and gives VR back; the speed (0.75x to 2x,
  under the Narrate button) is remembered and applies at once.
- **Scroll strips work like joysticks:** press, drag away from that point to scroll (farther =
  faster, back past it reverses), let go to stop; the strip shows where you pressed. They scroll
  with arrow keys everywhere, the desktop included (its Remote Desktop portal accepted wheel steps
  but nothing scrolled, so it's no longer used and its saved permission is removed).
- **Scroll strips scroll (for real this time).** In VR the Steam session takes pointer input only
  from the lasers, so injected mouse wheels never arrived. The desktop now scrolls with real wheel
  steps through its own Remote Desktop portal (KDE asks once), other windows with arrow keys /
  PgUp-PgDn. The top strip bends with curved windows.
- **Scroll strips for the window docked in the dashboard** (the desktop): strips now hang from each
  window panel's edge anchors, drawn by a component of their own, so docked and floating windows
  both get them.
- **Scroll strips scroll now.** ydotool's virtual wheel never reached app windows; the strips now
  send wheel clicks through XTest on the Steam session's display. A drag also ends if the laser's
  release goes missing.
- **Arrow Pad:** Save and Redo swapped places on the Tools layer.
- **Scroll strips: fixed size, place and the Steam bar.** They were sized from the window's scaled
  measurements (about 2.7x too big and far out) and used large page elements, which made the
  dashboard draw the Steam bar too big. Now real-world sizes (thickness 2.5 / 4 / 6 cm) and small
  page elements.
- **Arrow Pad: keys keep their places across layers.** Tools is top-left and Esc at the end of the
  second row; Tools, Esc, Fn, the modifiers, R/M and the clipboard keys sit in the same spot on
  the main, Fn and Tools layers (the Tools-only keys take the arrow and navigation keys' places).
- **Scroll strips** (new, VR windows): big strips beside each floating window (right and top by
  default) to drag-scroll with the laser, or tap near an end to page. They scroll the window you
  last clicked. Side and thickness in the row's ⚙ Settings. VR dashboard patching gained patch
  settings (`~/.config/frame-tweaks/NAME.json`) and page-to-service calls (`sftScroll`).
- **Fixed: Arrow Pad and the installer could switch the desktop into input-grab mode.** Their
  stuck-key cleanup pressed Right Ctrl, which in the nested desktop toggles KWin's input grab
  ("Press right control to ungrab input"), so windows and clicks behaved oddly after Arrow Pad
  started or was reinstalled. Right Ctrl is no longer pressed.
- **Arrow Pad: Unstick key** (Tools layer, replaces PrtSc there): when the desktop acts as if
  Shift, Ctrl, Alt or Super is held, it presses and releases each.
- **Speech engine (helper, new): the Screen reader's Orca can speak.** SteamOS has speech-dispatcher
  and its espeak-ng module but not espeak-ng, so Orca was silent. The espeak-ng inside Piper's
  download is now wired into speech-dispatcher (a user `speechd.conf`, restored on uninstall).
  Piper and its voice moved here from Screen snip; Screen snip and Screen reader depend on it.
- **Back to the previous window** also covers closing: when the window the dashboard shows is
  closed (a cancelled Screen snip, say), it goes back to the window before it instead of Steam.
- **Screen snip: crop handles.** Adjust the rectangle by its corners and edges, or drag it to move
  it, before choosing Copy, Save, Copy text or Narrate.
- **Screen snip** (new): select a rectangle of the window you're using, then Copy, Save, Copy
  text (Tesseract OCR) or Narrate (reads it aloud with Piper, offline). Works on the desktop and
  on floated VR windows.
- **Arrow Pad: Tools layer.** A Tools key (where Dictation was) opens a layer with Snip,
  Dictation, Launcher, Undo/Redo, Find, Save, Cut/Copy/Paste/All and more; tap it again to go back.
- **Apply changes is dimmed when there's nothing to change** (its tooltip lists what it would
  install or remove). Only real changes count: a ticked tweak that's installed with a warning is
  no longer reinstalled by Apply; use its ↻ button.
- **Pick up when floating:** the click that puts the window down could land on Return to
  Dashboard (the laser stays on that button) and dock it again; that's now ignored while you hold
  the window and for 1.5 s after. Light clicks put it down reliably (smaller trigger movement
  counts, checked more often, and any click on the dashboard page counts).
- **Pick up when floating** (new, VR windows): "Float in World" also picks the window up for
  placing, as grabbing its bar does; your next click, or letting go of the trigger you're still
  holding, puts it down. One click instead of two.
- **Android Mirror in VR takes the phone's shape and follows its rotation** (`phone-fit`): no
  more wide black bars beside a phone held upright. The Steam session makes app windows
  1920×1080, but keeps a window that declares a fixed size, so the mirror window is sized to the
  phone screen's shape that scrcpy reports, and resized when the phone rotates.
- **Back to the previous window** waits 2.5 s (was 1 s), and installing a VR windows tweak waits
  for its patch to be active before showing its status (it showed "not patched yet").
- **Signal hardening is now "Signal: key in the wallet"**, which is what's left of it: Password
  first and Close after are set in Wallet apps.
- **New VR windows group** in the installer window, with **Back to the previous window** (new):
  after you float the window the dashboard is showing out into the world, the dashboard goes
  back to the window it showed before (after 1 s) instead of an empty space. Tick or untick it
  to switch it on or off. **Curved world windows** moved into the group. Both are small patches
  run by a shared helper, **VR dashboard patching** (it took over `sft-curvature`'s DevTools-port
  setup; installing either tweak moves an existing setup over). Each patch is switched off
  by itself if a SteamVR update changes the dashboard code it relies on.
- **Wallet apps explains why** (a headset without a password can still keep sensitive apps
  behind the wallet's) and **shows the wallet's state** at the top: open or locked, for how long,
  when it locks by itself, with a Lock now / Unlock button. `wallet-unlock --info` reports it.
- **Signal uses the standard Wallet apps protections; Signal guard is retired.** Its two jobs
  are now Password first and a Close-after timer, like any app's (15 minutes, or your Signal
  guard setting, carried over). Its headset-off option is now **Headset off**, for any app with
  a timer. Reinstall the Signal tweak (↻) to switch over.
- **Password first no longer disappears:** re-wrapping an app's menu entry (after an app update,
  or when another tweak adds its app) dropped the wallet-password gate, which is how Claude
  Desktop lost it. `wallet-launcher` now keeps it unless told `--no-gate`. Signal shows it as
  provided by Signal guard. Re-wrapping a protected system app no longer treats the override as
  the original.
- **🔑 Wallet apps in the installer window:** choose which apps open with the shared KDE wallet.
  It lists every installed app (Flatpaks from any source, system apps, your own launchers),
  detects Electron/Chromium apps, and has a Password-first switch, a **Close after** timer and
  Remove for each protected app. The timer (new `app-timers` service) quits the app after that
  long with no input, like Signal guard does for Signal. `wallet-launcher` can now wrap system
  apps too.
- **Android Mirror's "Phone not found" names the phones it did see**, and says Wireless debugging
  lives in Developer options in the phone's Owner profile (a different phone on the same Wi-Fi
  was easy to mistake for yours).
- **Arrow Pad VR's mic button showed the previous dictation state:** the redraw could run before
  the button was recoloured, so the first tap didn't turn it red and it stayed yellow after the
  text arrived. It now goes red while recording, yellow while transcribing, then back to normal.
- **Claude Desktop kept signing you out:** some starts reached no wallet (Chromium's `basic_text`
  fallback), so the sign-in was never saved, and one saved by a wallet-backed start couldn't be
  read. `~/.local/bin/claude-desktop` is now a launcher that always uses the shared KDE wallet, however
  Claude is started (app menu, VR "+" menu, `claude://` links, a terminal). Its status check
  warns when the running Claude couldn't reach the wallet.
- **↻ Reinstall button** on each installed tweak in the installer window, and
  `./install.sh reinstall ID...`: stops its programs, removes it and installs it again in one step
  (also for a tweak others depend on, such as ydotool).
- **Arrow Pad's uninstall keeps your settings** (`~/.config/arrowpad.json`: VR position, size,
  theme), as the installer window promises; a reinstall no longer resets them.
- **Arrow Pad VR still blinked when a toggle key changed (modifiers, Fn, R/M, mic, pin):** a
  display-only cover panel now shows the previous image on top while the pad loads the new one,
  then steps aside. It never takes laser input, so taps still go to the one input overlay.
- **Arrow Pad VR jumped when switching between the Steam and Desktop tabs:** it followed Steam's main
  panel when that was showing and the dashboard bar otherwise, and the Desktop tab hides the main
  panel, so it effectively kept two positions. It now follows the bar on both tabs. A position saved
  by an older version is converted once. Reset still puts it beneath the main panel.
- **Arrow Pad VR flickered after clicks:** every press and release reloaded the overlay image, and
  each reload blinks. Presses no longer redraw it (they're felt as a haptic click); it redraws only
  when something visible changes (modifiers, Fn, R/M, mic, pin, settings, theme), with normally
  compressed images again so SteamVR loads them faster.
- **Stuck modifiers:** when Arrow Pad starts, and when the installer stops or uninstalls it, the
  desktop is made to forget any Ctrl/Alt/Super/Shift a crashed pad left "held" (a full press and
  release each; Super and Alt around F24, so no menu opens). A stuck one used to add itself to
  every key until desktop mode was restarted.
- **Arrow Pad VR crashed on clicks** (a segfault inside SteamVR's PollNextOverlayEvent after the
  double-tap fix switched overlays' input modes on every redraw), and taps could still count twice.
  It's back to a single overlay whose input mode never changes; to keep reload flicker down it no
  longer redraws just because the laser hovers over another key (the hover tick is still felt).
- **Arrow Pad VR showed an old picture after reinstalling:** SteamVR caches overlay images by file
  name, and the pad reused two fixed names. Every image now gets a new name; old ones are deleted.
- **Arrow Pad uninstall** removes all its program files (it left vroverlay.py, haptics.py and the
  SteamVR input files behind).
- **NordVPN tray started twice at login** (autostart plus KDE's session restore): the tray now runs
  once (a second copy exits), and installing excludes it from session restore (restored on removal).
- **Claude Desktop couldn't use the KDE wallet:** its launcher lacked `--password-store=kwallet6`, so
  its login didn't persist and secrets fell back to plain text. wallet-launcher now adds it for
  Claude Desktop and keeps it when the launcher is re-applied after an update.
- **Uninstalling or reinstalling a tweak stops its running programs first** (listed in
  `<tweak>/processes`: Arrow Pad, NordVPN tray, clipboard-sync, Full Keyboard), so an old copy
  can't keep running after a reinstall; Arrow Pad's held keys are released.
- Arrow Pad keeps a crash traceback in `/run/user/$UID/arrowpad-<target>-crash.log`.
- **Arrow Pad, more Full Keyboard:** keys drawn its way (a side, a face that travels down when
  pressed, hover gradient); Graphite and Midnight themes and haptic strength in a ⚙ settings
  page; the Steam Frame logo on Super and a SteamOS key (opens the app menu) on the Fn layer; in VR,
  grip-to-grab anywhere on the pad and two-handed modifiers (hold Ctrl with one laser, press with
  the other). Redraws are quicker (lighter PNG compression, up to ~7 a second).
- **Claude Desktop** updated to 2.31226.1.
- **Arrow Pad VR: a tap could count twice.** Both of the pad's double-buffered overlays took laser
  input, so for ~50 ms per redraw a click reached both: one tap locked a modifier (a locked Super
  turns every click into Super+click) or toggled R/M on and off. Only the front overlay takes input
  now, and a repeat within 60 ms is dropped. Closing the dashboard also releases held modifiers.
- **Arrow Pad uninstall:** `--quit` no longer needs a display (it crashed when run from the
  installer), and any pad still running is stopped, so a reinstall really runs the new version.
- **Arrow Pad right/middle-click toggles:** a scroll while one was armed was swallowed and turned
  into a right/middle click (the controller's scroll is mouse "buttons" 4/5); scrolling now passes
  through. Toggles also cancel when the dashboard closes and after 10 s (was 20), a press whose
  release never arrives is replayed after 1.5 s, and every step is logged
  (`/run/user/$UID/arrowpad-clicks.log`). Tested on a private X display (`tests/test_clickswap.py`).
- **Arrow Pad looks:** Full Keyboard's own toolbar and copy/paste icons (ported, MIT), including
  its pin on/off icons; a slight sideways lean eases level after a grab, as in Full Keyboard.
- **Installer window in VR:** A/B/Y and the D-pad are claimed only while the laser is really on
  the window (pointer inside it and moving), not just while Qt thinks it's hovered.
- **Pinned:** clipboard-sync builds a pinned commit; the Whisper model is fetched from a pinned
  Hugging Face revision and checked against its SHA256 (it was the moving `main` branch,
  unchecked); Python packages install at exact versions (`lib/python-constraints.txt`).
  `dev/check-pins.sh` reports newer versions of all of them.
- **Claude Desktop updater:** refuses while Claude Desktop is open (it used to close it without
  asking); `claude-desktop-update --restart` to do it anyway; downloads retry.

## 0.4.0 (2026-10-08)
- **Release channels:** updates and `get.sh` take stable `vX.Y.Z` releases only (pre-releases
  used to win over their final version); `beta` in `~/.config/steam-frame-tweaks/channel` opts
  into pre-releases.
- **Installer:** one install/update/removal at a time; every run logged; `debug-info` (redacted
  report; also a **Diagnostics** button); `hold`/`unhold`; `update --to vX.Y.Z`; per-tweak
  versions with `migrate.sh`; `check-system` (also after every update).
- **Installer window:** crash page with copyable details, single instance, D-pad row navigation
  in VR (left D-pad up/down, A ticks).
- **Backups:** `backup_file`/`restore_file` and per-key KDE settings restore; the wallet puts its
  `kwalletrc` settings back on removal.
- **Wallet:** fixed the 4-hour auto-lock never being scheduled again after one failed lock
  (a leftover unit name blocked it, silently); status warns when unlocked without an auto-lock.
- **Sandboxing** for ydotoold, wallet-lock-sync and the curvature services.
- **New tweaks:** Memory caps (Whisper, scrcpy, VSCodium) and Screen reader (Orca).
- **Packaging:** AppStream metainfo, desktop ID `io.github.AstronautCheetah.FrameTweaks`, icons in
  three sizes; CI validates them.
- **Docs:** README/SECURITY tables and per-tweak "At a glance" boxes generated from each tweak's
  `meta`; Common issues; roadmap.
- **Engineering:** unit tests, release workflow, actions pinned to commits.
- Uninstalling Dictation, Wallet, Arrow Pad, NordVPN or Android Mirror now also removes its
  menu icon (found by the install test).
- ydotool: a service that fails to start is reported as a warning instead of failing the
  install silently.
- Install test covers ydotool, Dictation and Wallet too, with a fake network (fixtures for the
  Whisper model and the Arch package).
- CI runs once per commit on main (not again for each release tag) and cancels superseded runs.

## 0.3.1 (2026-10-07)
- Menu icons: no longer fails on a fresh home folder that has no icon theme folder yet
  (found by the new install test in CI).

## 0.3.0 (2026-10-07): first release candidate

Frame Tweaks (formerly "Steam Frame Tweaks") is a checklist installer of home-folder-only
tweaks for the Valve Steam Frame.

**Core: fixes for the Frame**
- **Arrow Pad:** the keys the Steam keyboard lacks (arrows, Home/End, PgUp/PgDn, Esc, Tab,
  F-keys, one-shot Ctrl/Alt/Super), right/middle-click toggles, clipboard keys and a dictation
  button. In desktop mode it never takes focus; in VR it's a native SteamVR overlay below the
  dashboard with Full Keyboard's look, placement, grab and haptics.
- **Full Keyboard** (TaiKeid) and **whisper-frame** (groffta), installed from pinned releases.
- **Dictation:** local Whisper speech-to-text on the Frame's GPU, typed into the focused app.
- **Curved world windows:** windows floated into the world start curved.
- **Cursor fix, shared clipboard, shared KDE wallet** (one wallet for both sessions, unlock
  dialog, auto-lock, password-gated apps), **menu icons** for Steam's "+" menu, **tools**.

**Extras:** Android Mirror, Signal and Firefox hardening, NordVPN over WireGuard, VSCodium,
Claude Code and Claude Desktop. **Helpers:** Homebrew, ydotool.

**Installer window:** categories that fold and hide, per-row ▶ actions, details pages with
each tweak's README, update hints, known-issue notes, and controller buttons in VR
(B back, Y home, A tick).

**Trust and safety**
- Upstream releases pinned to recorded SHA256s; Arch Linux ARM packages signature-checked;
  `get.sh` and `update` install release tags, not `main`.
- SECURITY.md lists what every tweak changes on your system, including ports, pointer grabs and
  controller buttons.
- Curvature checks SteamVR's dashboard code and disables itself if an update changed it.
- CI: ShellCheck, Python syntax, docs consistency, pinned-download checks, and an install →
  status → uninstall test in a throwaway home.

Tested on SteamOS 0.4.5 (build 20261006.6173745), SteamVR build 1791331621, one headset.

## 0.1–0.2.9 (2026-10-07): development

Built up on one Frame; the commit history has the details.
