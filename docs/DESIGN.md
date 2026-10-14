# Frame Tweaks: design notes

How Frame Tweaks' core works and why it is built the way it is. This page is for contributors
and reviewers. What each tweak does, and how, is in its own README under
[`packs/official/`](../packs/official/); how to write a tweak or a pack is in [mods.md](mods.md).

## Goal

Someone with a Valve Steam Frame picks fixes and app setups from a checklist, and each one
installs, checks and removes on its own. Nothing should need `steamos-readonly disable`,
nothing should break at the next SteamOS update, and what is installed should keep working if
nobody maintains the project any more.

## Constraints

The design follows from what the Frame is:

- **ARM64 SteamOS.** Binaries must be aarch64. `lib/common.sh` warns when it runs on anything
  else. Arch Linux ARM packages run as-is, because SteamOS is Arch-based.
- **A read-only system partition that updates replace.** Anything installed into `/usr` (with
  `steamos-readonly disable` and pacman) is gone after the next SteamOS update. So every tweak
  installs into `$HOME`: `~/.local/bin`, `~/.local/share`, `~/.config`, user systemd units and
  the app menu in `~/.local/share/applications`. The README lists the two exceptions: Homebrew
  needs sudo once to create `/home/linuxbrew`, and NordVPN adds NetworkManager connections.
- **Two sessions at once.** Steam's VR session runs on X display `:0`, where floating VR
  windows live. Desktop mode is a Plasma session nested inside it, on Wayland, with its own
  D-Bus bus and `XDG_RUNTIME_DIR`. Programs started from the desktop, from shortcuts and from
  VR can each see a different environment, clipboard and wallet. Several tweaks exist only
  because of this: [clipboard](../packs/official/clipboard/) syncs the two clipboards,
  [wallet](../packs/official/wallet/) makes both sessions use one KDE wallet, and
  [`lib/browser.py`](../lib/browser.py) sends a web link to the session where the browser is
  already running. `sysctl_user` in `lib/common.sh` runs `systemctl --user` with the outer
  session's runtime folder and bus, so it also works from a desktop-mode shell.
- **The nested desktop is a KWin window.** A Right Ctrl press toggles KWin's input grab, and
  then every key and click goes to the desktop. Nothing in Frame Tweaks sends Right Ctrl (see
  *Safety rules*).
- **SteamVR's internals are not an API.** The VR environment tweaks patch SteamVR's dashboard,
  a web page whose code changes with SteamVR updates. They must turn themselves off when that
  code changes (see *Failing closed*).

## Layout

| Path | Role |
|---|---|
| [`install.sh`](../install.sh) | The commands: install, uninstall, reinstall, status, update, hold, check-system, debug-info, list, and so on. It decides what runs in which order, and takes the lock and the log. |
| [`lib/common.sh`](../lib/common.sh) | Helpers that tweak scripts source: messages, `fetch_pinned`, `alarm_fetch`, `pip_pinned`, backups, `status_ok`/`status_missing`/`status_warn`, dashboard-patch helpers. [mods.md](mods.md) lists what a pack can rely on. |
| [`lib/sft.py`](../lib/sft.py) | Loads the packs and their tweaks, and holds everything the installer window and `install.sh` share: the tweak list (`registry`), hidden rows and groups, the Run label, and tweak settings. Both front ends call it, so they can't drift apart. |
| [`lib/manifest.py`](../lib/manifest.py) | Reads (and writes) the YAML front matter of manifests, with no dependencies. |
| [`gui/`](../gui/) | The installer window (PyQt6): the list, details pages, Packs and Wallet apps pages. |
| [`packs/official/<id>/`](../packs/official/) | One folder per tweak: `README.md` (its manifest, then its documentation), `install.sh`, `uninstall.sh`, `status.sh` and optional scripts. `pack.md` sets the order and categories. |
| [`dev/`](../dev/) | Maintainer tools: docs generation and checks, pin checks and bumps, the mirror, the test harness, git hooks. |
| [`tests/`](../tests/) | Unit tests (`python3 -m unittest discover -s tests`). |

### Manifests: the README is the source of truth

A tweak's `README.md` starts with YAML front matter. That block is all the installer, the
window, the generated docs and the tests know about the tweak: title, category, tier,
dependencies, the processes it runs, settings, what it changes and how to undo it. Before
packs, this lived in separate files (`components.tsv`, `meta`, `processes`, `# label:` lines);
the CHANGELOG records their removal. One file per tweak means a tweak folder is
self-contained, and can be copied into a pack or out of one.

[`dev/gen-docs.py`](../dev/gen-docs.py) builds the README tables, SECURITY.md's "What each
tweak changes" rows and each tweak's "At a glance" box from the manifests, between
`<!-- generated:NAME -->` markers. CI runs it with `--check`, so the docs can't fall behind
the manifests.

### Why a strict YAML subset

`lib/manifest.py` reads a subset of YAML, written so that a file means the same thing to this
reader, to PyYAML and to a person:

- **No dependency.** SteamOS's Python may not have PyYAML, and the installer must run before
  anything is installed.
- **No guessing.** Values that YAML 1.1 readers turn into something else (`yes`, `no`, `on`,
  `off`, dates, `010`, `1_000`, `.5`) are refused with the line number and must be quoted.
  Tabs, anchors, aliases, tags, duplicate keys and values that continue onto the next line
  without `>` or `|` are refused too.
- **Checked.** `tests/test_manifest.py` reads every official manifest with both readers and
  compares the results; CI installs PyYAML for this test only.

## Packs and trust

Every tweak comes from a pack: a folder of tweak folders with an optional `pack.md`.
`lib/sft.py` `pack_dirs` looks in three places, in this order: the official pack
(`packs/official/`), the folders in `~/.local/share/frame-tweaks/packs/`, and the folders
listed in `FRAME_TWEAKS_PACKS`.

- **The official pack loads like any other.** It goes through the same `read_pack` and
  `read_tweak` checks. The only difference is that it doesn't need trusting.
- **Other packs need trusting.** A pack's scripts run as the user, with their files and
  passwords in reach. `./install.sh mods trust PACK` records the pack's folder and a SHA256
  over its file names and contents (`.git` and `__pycache__` left out) in
  `~/.config/frame-tweaks/installer/trusted-packs`. If any file changes, the hash no longer
  matches and the pack is shown as "changed" and not used until it is trusted again. Trust
  covers content, not a name or a location.
- **Ids are folder names.** If a trusted pack has a tweak with an id that is already taken,
  it is left out with a problem message, unless its manifest says `replaces: true`. Then it
  takes the earlier tweak's place in the list, and the window says which one it replaced.
- **`api`.** `pack.md` can say which version of the pack format it uses. A pack with a newer
  `api` than this Frame Tweaks knows (`API` in `lib/sft.py`) is skipped with a message, rather
  than misread. Unknown manifest keys are warnings and are ignored, so packs can use optional
  fields that a newer version adds.
- **Problems don't stop the others.** A tweak with a bad manifest or a missing script is left
  out. A tweak whose dependency no pack in use provides is left out too, and this repeats until
  nothing is missing. `./install.sh mods` lists every problem; `./install.sh mods check FOLDER`
  checks a pack without using it. `install.sh` stops only if no tweak at all can be loaded.

## Lifecycle of a tweak

### Install

`./install.sh install ID...` (and the window's tick boxes, which run the same command):

1. Takes the lock (`flock` on `~/.local/state/frame-tweaks/install.lock`) and starts a log.
   Only one install, update or removal runs at a time, from the window or a terminal.
2. Runs migrations for the named tweaks (below).
3. Adds dependencies, dependencies first, without duplicates (`with_deps`).
4. For each tweak, stops its running programs (`stop_processes`, below), so a reinstall
   can't leave the old copy running, then runs its `install.sh`. If that succeeds, it
   records the Frame Tweaks version that installed it (`record_version`).
5. Prints the status of what was asked for.

Tweak scripts run with the lock's file descriptor closed, so a background program they start
can't keep the lock held. Every `install.sh` must be safe to run again: updates and
reinstalls simply run it again.

### Status

`status.sh` prints one line and exits 0 (installed and working), 1 (not installed) or 2
(installed, needs attention), through `status_ok`, `status_missing` and `status_warn`. It must
not change anything: the window runs it often, in the background.

Status is also how Frame Tweaks knows what is installed. `uninstall all`, `update` and
`check-system` all ask each tweak's `status.sh`, and count anything that doesn't exit 1 as
installed. The version records in `installed/` are used only for migrations.

### Uninstall

`uninstall.sh` removes what `install.sh` added, keeps the user's settings and data, and says
what it kept. `install.sh` refuses to remove a tweak that an installed tweak depends on, and
`uninstall all` removes dependents first.

Before changing a file the user owns, a tweak calls `backup_file`, and `restore_file` on
uninstall. The first copy wins, and a file that didn't exist is recorded as absent, so
restoring removes it. KDE settings are recorded and restored key by key (`save_kconfig`,
`restore_kconfig`), because the rest of the file may have changed in the meantime. Files that
hold secrets in plain text are never backed up: a backup would bring back the leak the tweak
removed. CONTRIBUTING.md also asks for marked blocks that can be removed again, as the
Firefox tweak does in `user.js`.

`reinstall` uninstalls and then installs, with `FRAME_TWEAKS_REINSTALL=1` set for the
uninstall. Then a tweak can keep what other tweaks left in its care; for example,
`vr-dashboard` keeps the other tweaks' dashboard patches.

### Optional scripts

- **`stopped.sh`** runs after the programs listed under `processes:` in the manifest were
  stopped. Those patterns are `pgrep -f` patterns; they are sent a kill, given 3 seconds, then
  killed with `-9`. Arrow Pad's `stopped.sh` releases modifier keys that a stopped pad can no
  longer release itself.
- **`migrate.sh OLD-VERSION`** runs before `install.sh` when the version recorded in
  `installed/<id>` is older than the current `VERSION` (going back to an older release runs
  none). A failed migration is reported and the
  install goes ahead. No official tweak needs one at the moment. Renames that affect Frame
  Tweaks as a whole, such as the old `steam-frame-tweaks` folders and settings moved into
  `~/.config/frame-tweaks/`, are handled in code on every run (`migrate_legacy_dirs`), not by
  asking the user.
- **`check-system.sh`** checks that the SteamOS or SteamVR parts the tweak relies on are still
  there, prints one line and exits 0 or 1. `./install.sh check-system` runs it for every
  installed tweak, and so does every update.
- **`update-check.sh`** prints the installed and latest upstream versions; the window offers an
  update when the second is newer.

### Holds

`./install.sh hold ID` creates `~/.local/state/frame-tweaks/held/<id>`. During an update
(`FRAME_TWEAKS_UPDATING` set), a held tweak is neither migrated nor reinstalled. An explicit
`install` or `reinstall` of it still runs.

## Updating Frame Tweaks itself

Releases are git tags, `vX.Y.Z`. Pre-releases are `vX.Y.Z-rc.N`.

- **[`get.sh`](../get.sh)** finds the newest release tag with `git ls-remote` and clones that
  tag into `~/frame-tweaks` (or checks it out, if a clone is already there). It never installs
  whatever is on `main` at that moment.
- **`./install.sh update`** works like this in a release checkout (a detached tag): fetch the
  tags, pick the newest one for the channel (or the one given with `--to`, to roll back), and
  check it out. Then it re-runs itself as `./install.sh _reinstall`, so the *new* version of the
  script does the rest: migrations, a reinstall of everything installed (holds respected) and
  `check-system`. In a developer checkout on a branch it uses `git pull --ff-only` instead.
- **Channels.** Stable takes only `vX.Y.Z`. Beta (`beta` in `~/.config/frame-tweaks/channel`,
  or `FRAME_TWEAKS_CHANNEL=beta`) also takes pre-releases, sorted below the release they lead
  up to: `-` is replaced by `~` before `sort -V`. `get.sh`, `lib/common.sh` `newest_tag` and
  the window's update hint each implement this rule.
- **Migrations are keyed by `VERSION`.** `installed/<id>` holds the `VERSION` that last
  installed each tweak, and the tweak's `migrate.sh` receives it. What people and logs see is the exact build
  instead (`lib/common.sh` `ft_version`, `lib/sft.py` `build_version`): `0.5.0` at a release
  tag, `0.5.0+3.abc1234` three commits later, `-dirty` with local changes. Only `v*` tags count
  (the `mirror` release has a tag of its own).
- **Releases** are made by the Release workflow
  ([`release.yml`](../.github/workflows/release.yml)). It turns CHANGELOG.md's
  `## Unreleased` section into the release notes, bumps `VERSION` and the AppStream metadata,
  commits, tags and drafts a GitHub release.


## State on disk

| Where | What |
|---|---|
| `~/frame-tweaks/` | The checkout (`get.sh`'s default; `FRAME_TWEAKS_DIR` changes it). The menu entry points here. |
| `~/.local/state/frame-tweaks/` | `install.lock`; `logs/` (every changing run, the last 5 kept, used by `debug-info`); `installed/<id>` (version records); `held/<id>`; `backups/<tweak>/` (originals of changed user files and KDE keys); `alarm/<package>` (last installed Arch Linux ARM version, for the downgrade check); `vr-debugger.prev` (the dashboard setting to restore). |
| `~/.config/frame-tweaks/` | `channel`; `installer/` (hidden and shown rows, folded and hidden groups, `trusted-packs`); tweak settings (`*.conf`, `*.json`), written only through the keys and values the manifest lists. |
| `~/.local/share/frame-tweaks/` | `packs/` (user packs); `venv/` (shared Python venv for small D-Bus tools); `vr-dashboard/` (the patcher and installed patches); `launcher-originals/` (menu entries before wallet-launcher wrapped them); some tweaks' data. |
| `~/.local/share/arrowpad/venv` | The PyQt6 venv shared by the installer window, Arrow Pad and the NordVPN tray. |

`./install.sh debug-info` writes a report from these (status, holds, check-system, failed
user services, the last two logs). User and host names, the home path, IP, MAC and e-mail
addresses and the phone's name are removed before it is written.

## Supply chain

Downloads from other projects are checked against values recorded in this repository, never
against a checksum fetched next to the file.

- **Pins.** A tweak's `pin` (or `NAME.pin`) file names a `version=`, an HTTPS `url=`, and a
  `sha256=` for a file or a `rev=` for a git commit. `fetch_pinned` downloads the URL and
  refuses it unless it matches. A git pin is cloned and checked out at the commit, and the
  install fails if `HEAD` isn't that commit. CI requires every pin to have these fields.
  Homebrew's installer is pinned the same way.
- **The mirror release.** Each pin also has `mirror=`, Frame Tweaks' own copy on this repo's
  `mirror` release (uploaded by [`dev/mirror-pins.sh`](../dev/mirror-pins.sh)), with its
  `license=`, or `nomirror=` saying why it can't be copied. Piper isn't copied: it bundles
  espeak-ng (GPL-3.0), whose source would have to be hosted with it. When upstream's file is
  gone or changed, `fetch_pinned` uses the copy, **checked against the same SHA256**. A git
  commit's copy is a source archive with its own `mirror_sha256=` in the pin. The mirror is
  therefore trusted no more than upstream: a changed copy is refused, just as a changed
  upstream file is.
- **Arch Linux ARM packages** (`alarm_fetch`): HTTPS mirrors only. Each package is verified with
  `gpgv` against ALARM's build key, shipped in [`lib/keys/`](../lib/keys/). A signature proves
  only that ALARM built the file, so two more checks follow: the signed package's own
  `.PKGINFO` must name the package that was asked for, and a version older than the last one
  installed on this device is refused (a mirror replaying an old build).
  `ALARM_ALLOW_DOWNGRADE=1` overrides this.
- **Homebrew** packages (scrcpy, wl-clipboard, Tesseract and others) come from Homebrew as it is
  on the day of install; they aren't pinned.
- **Python packages** install through `pip_pinned`, with
  [`lib/python-constraints.txt`](../lib/python-constraints.txt) as a constraints file. CI
  checks that it has exact versions only.
- **Fallbacks favour working over exact.** If the pinned Python versions won't install (say,
  SteamOS moved to a newer Python), `pip_pinned` installs the newest ones with a warning. For
  adb and ydotool, `runs_here` checks with `ldd` that a new ALARM build can load its
  libraries on this SteamOS; if it can't, the working copy already installed is kept.
  [`lib/tested-versions`](../lib/tested-versions) records the scrcpy, android-tools and ydotool
  versions this release was tested with, and SteamOS's glibc and libstdc++. Android Mirror's
  `phone-touch` enforces the scrcpy major version (`SCRCPY_TESTED`): with an untested one,
  its VR extras switch off and the mirror stays a plain window.
- **Upstream check.** A weekly workflow ([`upstream.yml`](../.github/workflows/upstream.yml),
  [`dev/check-upstream.sh`](../dev/check-upstream.sh)) keeps one issue labelled
  `upstream-check` up to date. It lists what needs attention (a pinned file gone or changed, a
  missing mirror copy, an ALARM package gone or needing a newer glibc than SteamOS has, a new
  scrcpy major version) and what is worth a look (newer versions). It re-enables its own
  schedule each run, because GitHub disables scheduled workflows in repositories without
  recent commits.
- **Bumping.** [`dev/bump-pin.py`](../dev/bump-pin.py) moves a pin, or the Python constraints,
  to upstream's newest version. It computes the SHA256 itself, cross-checks it against a
  published `.sha256` when there is one, and prints the upstream changes to read. Nothing is
  committed automatically; the bump is tested and committed on its own.
- **CI actions** are pinned to commit SHAs.

## Failing closed around SteamVR internals

Tweaks that rely on SteamVR's internals have an `experimental:` text in their manifest. They
are marked 🧪 in the README, in the window and in `./install.sh list`, and the text says what
happens when SteamVR changes.

The dashboard tweaks share
[`vr-dashboard`](../packs/official/vr-dashboard/). Its `sft-dashboard` turns on SteamVR's
dashboard DevTools port (`127.0.0.1:8087`) through a `steamvr.service` drop-in, and only while
SteamVR is stopped, because SteamVR rewrites `steamvr.vrsettings` from memory. The previous
value is put back after SteamVR stops. While SteamVR runs, a watcher injects each installed
patch into the dashboard page every 5 seconds, again after a reload.

- **`// requires:` markers.** Each patch, and the shared `lib.js`, starts with lines like
  `// requires: what | exact text`, naming each piece of SteamVR's minified dashboard code it
  relies on. Before injecting, the watcher searches the installed dashboard files for every
  marker. If any is missing, that patch is not injected, and its status says "SteamVR changed
  (missing: …); off". A patch is never run against code it doesn't recognise.
- **`sft-dashboard check`** runs the same comparison without SteamVR running.
  `vr-dashboard`'s `check-system.sh` uses it, and so does every update.
- **`tests/test_vr_dashboard.py`** finds every patch that an official `install.sh` installs and
  checks its markers against the installed SteamVR when one is present (skipped elsewhere).
- **Scope.** The DevTools port has no password while it is open. SECURITY.md says so, and
  the installer window shows it before the tweak is ticked.

Other tweaks that rely on internals use `check-system.sh` the same way (for example
`recline`, `curvature`, `arrowpad`).

## Safety rules that shaped the design

- **Dry runs for anything that removes.** In the installer window, an unticked row means
  "remove". `FRAME_TWEAKS_DRY_RUN=1` makes the window, its Wallet apps page and the kdialog
  checklist print the plan instead of running it. CONTRIBUTING.md says never to test the
  window or uninstall paths against a real setup without it and a stub `konsole`. The kdialog
  checklist also refuses to remove anything when nothing came back selected, so a dialog
  that fails can't wipe a setup, and it asks again before any removal.
- **Changes run where they can be seen.** The window starts installs and removals in a Konsole
  window through `./install.sh`, the same path as the terminal, with its lock and log.
- **Pages, not dialogs, in VR.** In VR every new window opens in the dashboard, away from the
  installer. Details, settings, packs, messages and even crash reports are pages or
  in-window messages of the main window ([`gui/frame-tweaks-gui.py`](../gui/frame-tweaks-gui.py)).
  The window runs on a copy of the venv's Python named `sft-python`, because SteamVR keys
  controller bindings by program name and Arrow Pad also runs on Python.
- **Don't push the compositor.** Arrow Pad's VR overlay sends its picture with
  `SetOverlayFromFile`, not `SetOverlayRaw`: on the Frame, raw uploads never showed, and a
  2.5 MB raw upload crashed vrcompositor (SIGBUS). Picture size and update rate are capped
  ([`vroverlay.py`](../packs/official/arrowpad/vroverlay.py)).
- **Wallet gates go through launchers.** The wallet tweak protects apps by wrapping their menu
  entries. So `run.sh` scripts start apps with `gtk-launch <id>` (through the menu entry), and
  `install_desktop` re-applies the wrapper when a tweak reinstalls an entry it guards.
- **Never send Right Ctrl.** It toggles KWin's input grab on the nested desktop.
  `clear_stuck_modifiers` in `lib/common.sh` releases Shift, Ctrl, Alt and Super, but never
  Right Ctrl. [grab-guard](../packs/official/grab-guard/) only watches for it and never sends
  a key itself.
- **Sandboxed services.** Frame Tweaks' own user services use systemd sandboxing where it
  doesn't break them (see SECURITY.md).

## Testing and CI

[`ci.yml`](../.github/workflows/ci.yml) runs on every push to `main` and on pull requests:

- `shellcheck -x -S warning` on every shell script, and `py_compile` on every Python file.
- Commit message checks ([`dev/check-trailers.sh`](../dev/check-trailers.sh)) against the rules
  in CONTRIBUTING.md. The same script runs in the `commit-msg` and `pre-push` hooks
  (`dev/install-hooks.sh` turns them on).
- Manifest and installer self-checks: `lib/sft.py mods check packs/official`,
  `./install.sh list`, dependency resolution, every pin's fields, mirror lines, and exact
  versions in the Python constraints.
- Unit tests (`tests/`), with Qt headless (`QT_QPA_PLATFORM=offscreen`) and Xvfb for the
  click test. They cover the manifest reader against PyYAML, pack trust and replacement,
  settings shared with the VR panels, the window's logic (versions, channels, status
  parsing), shell helpers (including the mirror fallback and `alarm_fetch`'s signature,
  name and downgrade checks with a throwaway key), the dashboard patcher, `lib/browser.py`
  and parts of individual tweaks.
- AppStream metadata and desktop entry validation.
- Docs: [`dev/check-docs.py`](../dev/check-docs.py) (every tweak has a README row, relative
  links resolve) and `dev/gen-docs.py --check`.
- [`dev/test-tweaks.sh`](../dev/test-tweaks.sh): install, status and uninstall for each tweak
  whose manifest says `test: {offline: true}`, plus the example pack, each in a throwaway home.
  It uses stand-ins for systemctl, flatpak, brew, kdialog, gpgv and others, and a fake `curl`
  that serves fixtures and refuses every other URL. It fails if a step fails, if a tweak writes
  outside the fake home, or if uninstall leaves files other than those the manifest's
  `test: keeps:` lists.

What isn't tested automatically:

- Anything in the headset: overlays, dashboard patches in a running SteamVR, controller input,
  the two-session behaviour. CONTRIBUTING.md asks for VR tweaks to be tested in the headset
  before a pin bump.
- Tweaks without `test: {offline: true}`, about half of the official pack: those that need the
  network, Flatpak, a phone or SteamVR.
- Real downloads in CI (the weekly upstream check covers availability).
- Only official and example tweaks run in CI; user packs are checked only by `mods check`.
- Everything has been tested on one Frame and one SteamOS and SteamVR build (README,
  *Tested on*).

## Known limitations

- **Single device.** Other SteamOS devices and versions aren't tested; `lib/common.sh` only
  warns off aarch64.
- **SteamVR updates switch off 🧪 tweaks** until a Frame Tweaks update catches up. They fail
  closed, but they stop working.
- **Local programs.** While SteamVR runs, the dashboard DevTools port is open to any program on
  the Frame, Flatpak apps included. The same goes for ydotool's virtual keyboard while it runs.
  SECURITY.md's threat model is casual access, not malware running as the user.
- **Homebrew and Python packages aren't hash-pinned.** Homebrew formulae follow Homebrew;
  Python packages are pinned by version only, and may fall back to the newest versions.
- **Untrusting a pack doesn't uninstall its tweaks**, and `install.sh` only knows tweaks from
  packs in use. To remove one, trust the pack again first.
- **Status is per tweak.** "Installed" means `status.sh` doesn't exit 1. A tweak whose
  `status.sh` is wrong is updated or skipped wrongly.
- **Not done yet** (from [roadmap.md](roadmap.md)): rate-limit messages for update hints, and
  translations of the installer window.

## Considered and rejected

- **Installing into the system** (`steamos-readonly disable` and pacman). SteamOS updates wipe
  `/usr`, so this would need re-doing after each update. Home-folder installs, Flatpaks or
  config in `/etc` are used instead (README, *Things worth knowing about the Frame*; roadmap,
  *Not adopting*).
- **Nix.** steam-frame-nix offers declarative Home Manager modules. Frame Tweaks chose a
  checklist installer without Nix; the wallet tweak adapts steam-frame-nix's launcher approach
  instead (README, *How this compares*).
- **A root service** and **root-only tweaks** (SDWEAK, Btrfs changes):
  nothing here runs as root apart from Homebrew's one-time folder setup (roadmap, *Not
  adopting*).
- **Updates that reset the checkout** (`git reset --hard`): updates check out release tags, or
  fast-forward a developer branch, so local changes are never thrown away silently (roadmap,
  *Not adopting*).
- **A testing channel of pull-request builds** (as Decky has): only tagged releases reach users;
  the beta channel takes tagged pre-releases (roadmap, *Not adopting*).
- **PyYAML for manifests.** SteamOS's Python may not have it; `lib/manifest.py` reads a strict
  subset with no dependency, and the tests compare it with PyYAML.
- **Following `main` in `get.sh` and `update`.** Both install release tags since 0.3.0
  (CHANGELOG).
- **`SetOverlayRaw` for Arrow Pad's VR texture**: invisible on the Frame, and it crashed the
  compositor (see *Safety rules*).
- **Dialogs in the installer window**: they would open elsewhere in the VR dashboard (see
  *Safety rules*).
- **Homebrew's Rust for building clipboard-sync**: 3.4 GB with its LLVM. A pinned Rust
  toolchain in a temporary folder is used and deleted afterwards (CHANGELOG).
