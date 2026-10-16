# Packs: adding your own tweaks

Every tweak Frame Tweaks offers comes from a **pack**: a folder of tweak folders. Its own tweaks
are in three official packs, [`packs/core/`](../packs/core/),
[`packs/integrations/`](../packs/integrations/) (other projects' apps it fits to the Frame) and
[`packs/third-party/`](../packs/third-party/) (other projects' apps installed as they are), and
they're loaded exactly like anyone else's. To add programs or fixes of your own, write a pack.
You don't need to change
Frame Tweaks itself, and your pack survives its updates.

Start from the example, [`examples/hello-pack/`](../examples/hello-pack/): one small tweak that
uses most of what's described here.

## Where packs go, and trust

- **Your packs:** `~/.local/share/frame-tweaks/packs/<pack>/` (the installer window's
  **🧩 Packs → Open packs folder**). Packs elsewhere: list their folders in `FRAME_TWEAKS_PACKS`,
  separated by `:`.
- **From a link:** a pack shared as a git repository (the pack at its top: its `pack.md` and
  tweak folders) is added with **🧩 Packs → Add a pack from a link**, or `./install.sh mods add
  LINK [BRANCH|TAG]`. It's cloned into your packs folder and, like any pack, isn't used until
  you trust it. **Update** (`mods update PACK`) brings its newer version, which waits until you
  trust it again; **Remove…** (`mods remove PACK`) deletes it once its tweaks are uninstalled.
  **⟳ Check for updates** in the window (and `mods updates`) asks each one's repository whether
  its branch has moved on, without downloading anything, and the Packs page marks those that have.
  So a pack author publishes an update by pushing to the branch people added.
  Links start with `https://` (or `ssh://`, `git@host:`); a pack added at a tag stays at it.
- **Trust:** a pack's tweaks run as you, with your files and passwords in reach, so a new pack
  is listed but not used until you trust it: **🧩 Packs → Trust…**, or
  `./install.sh mods trust "<pack name>"` (or its folder, if two packs share a name). Trust
  covers the pack's files as they are then (names, contents, links, which ones can run); if any
  change (an update, or something tampering with them), the pack waits until you trust it again.
- `./install.sh mods` lists the packs, whether each is in use, and any problems.
  `./install.sh mods untrust "<pack name>"` stops using one; tweaks of it you installed stay
  until you uninstall them, which takes trusting the pack again first (Frame Tweaks only knows
  the tweaks of packs in use).

## A pack

```
my-pack/
  pack.md            optional: the pack's name, author, api, category and tweak order
  my-tweak/
    README.md        the manifest (front matter) and the tweak's documentation
    install.sh  uninstall.sh  status.sh
    run.sh  check-system.sh  needed.sh  update-check.sh  migrate.sh  stopped.sh    (optional)
    ...              whatever the scripts install: programs, .desktop files, icons, pins
```

`pack.md` (all optional; without it, the folder's name is the pack's name):

```yaml
---
name: My pack
author: Your name
api: 1                         # the pack format it's written for (this version knows 1)
categories: [Games]            # new categories, in order (after the official ones)
order: [my-tweak, other-one]   # its tweaks' order (the rest follow, alphabetically)
formerly: [old-folder]         # (an official pack) its folder's earlier names: turned off under one stays off
---
What the pack is, for people reading it.
```

A tweak's **id** is its folder's name: lower-case letters, digits and `-`. If it's an id
another pack already uses (an official tweak's, say), it's used **instead of** that one only
if its manifest says `replaces: true`. Otherwise it's left out, and `./install.sh mods` says
why. The installer window marks tweaks from your packs with 🧩 and the pack's name, and says
when one replaces another.

## The manifest

A tweak's `README.md` starts with a block of YAML between two `---` lines. Everything Frame
Tweaks knows about the tweak comes from there. The rest of the file is its documentation,
shown on its details page, pictures included: `![Alt text](screenshot.png)` with a path relative
to the README shows the file from the tweak's folder (wide ones are scaled to fit).

```yaml
---
title: Hello Frame
emoji: 👋
category: Examples
tier: extras
summary: One line for the list
what: What you get, for its details page and the README tables.
why: Why it's useful on the Frame.
author: Your name
changes: What it installs or changes, and where
access: Unusual access it has (the network, a device, another app's data), or None
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall hello-frame`"
---
# Hello Frame
...
```

**Required** (all text):

| Key | What it's for |
|---|---|
| `title` | Its name in the list. |
| `emoji` | Its emoji in the README tables. |
| `category` | Its group in the list: an existing one (Accessibility, Convenience, VR environment, System, Hardware, Privacy & security, Developer) or a new one. |
| `tier` | `core` (a fix for the Frame), `extras` (an app setup) or `helper` (something other tweaks need; the README tables mark it "helper"). It describes the tweak and doesn't change how it installs. |
| `summary` | One line, shown in the list and in `./install.sh list`. |
| `what`, `why` | Its details page. |
| `author` | Who made it ("Made by"). |
| `changes`, `access`, `survives_updates`, `undo` | What it changes on the system, any unusual access it has, whether it survives SteamOS updates, and how to undo it (the official README tables and SECURITY.md are made from these). |

**Optional:**

| Key | Example | What it does |
|---|---|---|
| `depends` | `[ydotool]` | Tweaks installed first (from any pack in use). If one is missing, this one isn't offered. |
| `source` | `{relation: from, url: https://…}` | The project it's linked to in the list, and how: `from`, `uses` (the default), or a few words of your own such as `styled after`. |
| `hidden_by_default` | `true` | Hidden in the list until you choose to show it. |
| `experimental` | text | Marks it 🧪 and says what relies on another program's internals and what happens when they change. |
| `icon` | `{file: icon.png}` · `{theme: face-smile}` · `{flatpak: org.app.Id}` | Its icon in the list: a picture in its folder, a Breeze icon name, or an installed Flatpak's icon (these can be combined; tried in the order flatpak, file, theme). |
| `run` | `{label: Open}` | The Run button's label. A tweak with a `run.sh` gets the button anyway, labelled Run. |
| `processes` | `["^~/.local/bin/my-daemon"]` | Programs it keeps running: a list of `pgrep -f` patterns, one line each, `~` for your home folder. They're stopped before it's uninstalled or reinstalled, then `stopped.sh` runs if it has one. Anchor them (`^…`) and make them specific: whatever matches is stopped, the installer itself included if its own command line matches. |
| `config` | `[~/.config/my-tweak.json]` | Where it keeps its settings: files or folders under `~/.config/`, `~/.var/app/` or `~/.local/state/frame-tweaks/` (its `settings.file` counts without being listed). An uninstall keeps them and says so, or removes them when ⚙ Preferences → Uninstalling, or `--remove-settings`, says to. Data such as a history or keys belongs elsewhere, and stays. |
| `app` | `Hello Viewer` | The name of another project's app it installs (Claude Desktop, say). Uninstalling Frame Tweaks leaves such tweaks, and what they depend on, installed unless asked to remove them, so the app and your work in it stay. |
| `sudo` | `once, to add a udev rule that lets you pause charging` | When and why installing it asks for the sudo password; the window tags its row **sudo** and says so on its page, and the README tables mark it *(sudo)*. `homebrew`: only while Homebrew isn't installed (a tweak that calls `need_brew`). |
| `formerly` | `[old-name]` | The tweak's earlier ids, after a rename (its folder's name). What Frame Tweaks keeps under one (its install record, held, hidden) moves to the new id once, `depends:` on one still finds it, and `./install.sh` says what it's called now. Moving a tweak to another pack needs nothing: ids are the same in every pack. |
| `settings` | (below) | A settings page in the installer window, and `./install.sh settings ID`. |
| `known_issue` | `{version, short, long, latest}` | A problem with an upstream version: `short` on its row, `long` on its details page, and a check whether `latest` (a GitHub releases API URL) has something newer than `version`. |
| `wallet_apps` | `[org.signal.Signal]` | Apps it sets up to use the shared KDE wallet (the Wallet apps page says so). |
| `test` | `{offline: true, keeps: [.config/…], needs: [orca]}` | `dev/test-tweaks.sh` installs, checks and removes it in a throwaway home folder (it runs the official packs' and the example's tweaks, not your own pack's). `keeps`: the files its uninstall leaves on purpose; `needs`: commands it needs to be tested. |
| `replaces` | `true` | Use it instead of the tweak with the same id in another pack. |
| `upstream_readme` | `https://raw.githubusercontent.com/owner/repo/v1.0/README.md` | For a tweak that installs another project: that project's README at the pinned version. In the official packs, `dev/fetch-upstream-readmes.py` copies it (with its pictures) into the tweak's folder and `dev/gen-docs.py` appends it below the tweak's own README. |

**Settings:**

```yaml
settings:
  file: ~/.config/frame-tweaks/hello-frame.conf    # under ~/.config/
  format: shell                                    # shell (KEY=VALUE lines) or json
  about: What these settings are for.
  note: When changes apply.
  options:
    - key: HELLO_GREETING
      title: Greeting
      default: hello
      choices:
        - {label: Hello, value: hello}
        - {label: Ahoy, value: ahoy}
    - key: HELLO_LOUD                              # two choices, shown as one tick box
      title: Shout it
      checkbox: true                               # (the first choice is "ticked")
      default: "no"
      choices:
        - {label: "Yes", value: "yes"}
        - {label: "No", value: "no"}
  include: [speech]                                # optional: other tweaks' settings, on this page too
  actions:                                         # optional: buttons that run a script
    - label: "Forget {HELLO_NAME}"                  # (an illustration: hello-frame has none) {KEY}: that setting's value
      script: hello-frame                          # in the tweak's folder, run with bash
      args: [--forget]
      when: HELLO_NAME                             # shown only while that setting has a value
      about: What pressing it does.
```

Only the listed keys are written (a `shell` file's values quoted where they must be, so it can
be `source`d); anything else in the file is kept. Your program reads the file itself. An option
with `swatches: true` shows its choices as colour circles (their values are colours).

### The YAML

The front matter is a strict, simple form of YAML, so it means the same to Frame Tweaks, to
other YAML tools and to whoever reads it:

- `key: value`; nested mappings and lists indented with spaces; `[a, b]` and `{k: v}` on one line.
- Long text: `key: >-` with the text indented on the next lines (lines are joined with spaces;
  a blank line starts a new line). `|` keeps line breaks as they are.
- **Quote** a value that starts with `` ` ``, `[`, `{`, `*`, `&`, `!`, `|`, `>`, `'`, `"`, `%`,
  `@` or `? `, that contains `: `, or that YAML could read as something else: `yes`, `no`, `on`,
  `off` (any case), dates, and numbers like `010` or `1_000`. Unquoted, these are refused, with
  the line number, rather than guessed at. A ` #` starts a comment, as in YAML: quote a value
  that should keep it.
- Inside `[...]` and `{...}`, also quote a value that starts with `:` or `#` or holds `?`, `[` or
  `{`, and leave no empty values (`[a, ]`).
- Keys are plain words: not ones YAML reads as numbers, true/false or dates (`1:`, `on:`).
- No anchors (`&`), aliases (`*`), tags (`!`) or tabs.

`./install.sh mods check <folder>` checks a tweak or a whole pack without using it.

### The README's text

Write it for someone deciding whether to tick the tweak, in this order (the official tweaks and
[`examples/hello-pack/`](../examples/hello-pack/) follow it):

1. `# Title`, then what it is (`what`) and **Why on a Steam Frame:** (`why`).
2. A screenshot, if it has a window.
3. `## Install`: tick it in the window, or `./install.sh install <id>`, and any step after
   (a reboot, a SteamVR restart).
4. `## Use`, then if needed `## Settings`, `## How it works`, `## Good to know`.
5. `## What it changes`: the `survives_updates`, `changes`, `access` and `undo` facts.
6. `## Credits`, then a `---` line and `Check: … · Remove: …`.

The installer window shows `what` and `why` above the README already. In the official pack,
`dev/gen-docs.py` writes parts 1 and 5 from the front matter.

## The scripts

The installer runs each script with `bash`, from any folder; they don't need to be executable.
Start each one with:

```bash
source "$FRAME_TWEAKS_LIB/common.sh"
```

That gives you `$TWEAK_DIR` (the tweak's own folder: use it for its files), `$BIN`
(`~/.local/bin`), `$APPS` (the app menu's folder) and the helpers below. It also turns on
`set -euo pipefail`: a command that fails stops the script (add `|| true` where a failure is
fine). During the ↻ Reinstall button's uninstall, `$FRAME_TWEAKS_REINSTALL` is set (keep the
user's setup, the install follows); during an update, `$FRAME_TWEAKS_UPDATING`.

- `install.sh`: installs it. It must be safe to run again, and install only into your home
  folder (SteamOS's system partition is read-only and updates wipe it). Exit non-zero on failure.
- `uninstall.sh`: removes what `install.sh` added, keeps the user's settings and data, and says
  what it kept.
- `status.sh`: prints one line and exits through `status_ok` (installed and working),
  `status_missing` (not installed) or `status_warn` (installed, needs attention). It must
  change nothing; the installer window runs it often. Something SteamVR loads only as it
  starts (a driver, a dashboard patch) says so with `status_restart` once installed, until
  SteamVR has restarted: the window then offers **⟳ Restart SteamVR** on its row. Once
  uninstalled, `status_unload` does the same while SteamVR still runs it (the row shows it as
  not installed). `vr_started_before FILE` tells whether the running SteamVR started before FILE
  changed: keep a file whose time is the uninstall's for that.
- `run.sh` (with `run:`): what the Run button does. Launch apps through their menu entry
  (`gtk-launch <id>`), so wallet gates apply.
- `check-system.sh`: whether the SteamOS or SteamVR parts it relies on are still there (one
  line; exit 0 or 1); `./install.sh check-system` and updates run it.
- `needed.sh`: whether this Frame needs the tweak at all: exit 0 if it does, exit 1 with one line
  saying why if it doesn't (SteamOS now does it itself, say). Check what the Frame has, a
  package's version (`pacman -Q`, `vercmp`) or a file, rather than the SteamOS version, which the
  beta and stable branches number differently. A tweak that isn't needed isn't offered: the
  window hides it (**Show hidden** lists it, saying why, with its box disabled), and
  `./install.sh install` skips it. If it's installed already, it stays in the list, updates
  reinstall it, and its `status.sh` should say it can be removed (the Mouse cursor fix does).
- `update-check.sh`: prints `<installed> <latest>` versions; the window offers an update when
  the second is newer.
- `migrate.sh <old-version>`: runs before `install.sh` when the Frame Tweaks version that last
  installed it was older (to move a setting to a new place, say).
- `stopped.sh`: runs after its `processes` were stopped.

**Helpers** (from `lib/common.sh`; read it for the details):

| Helper | What it does |
|---|---|
| `say`, `warn`, `die` | Messages; `die` exits. |
| `ask "question?"` | Yes or no, in the terminal or a dialog. |
| `ensure_path` | Puts `~/.local/bin` on PATH for terminals and the desktop. |
| `install_desktop FILE` | A `.desktop` file into the app menu (`@BIN@` becomes `~/.local/bin`). |
| `install_icon NAME` | `NAME.png` from the tweak's folder into the icon theme (Steam's VR menu finds it). |
| `remove_desktop FILE...`, `remove_icon NAME` | Their undo, for `uninstall.sh` (including the copy kept while the wallet guards an entry). |
| `brew_cmd NAME` | A command's path, on PATH or in Homebrew (for `status.sh`); fails without it. |
| `remove_files PATH...` | Removes them, saying what went. |
| `write_file DEST [MODE] < content` | Replaces a program (or any file) with new content by renaming a finished copy over it, so a running copy isn't changed under it. Use it, not `>` or `cp`, for anything in `~/.local/bin` (CI checks). |
| `install_i18n` | Frame Tweaks' translations, for a program of the tweak that shows text (`locale/MARKING.md`), and the Python modules programs share, in the same folder: `ftconf` (settings files, JSON or `KEY=value`, and rotating logs) and `vrkit` (SteamVR poses, grip squeezes, haptic ticks). A program puts `os.environ.get("FRAME_TWEAKS_PYLIB") or ~/.local/share/frame-tweaks/i18n` on `sys.path` (tests point it at `lib/`). |
| `backup_file TWEAK FILE`, `restore_file TWEAK FILE` | Keep a user file as it was before you changed it, and put it back on uninstall. KDE settings: `save_kconfig` / `restore_kconfig`. |
| `fetch_pinned ID OUT [PIN]` | Downloads the file a `pin` names and checks its SHA256 (see below). |
| `alarm_fetch REPO NAME DEST` | An Arch Linux ARM package, signature-checked, unpacked into DEST. `runs_here BINARY` says whether it can run on SteamOS. |
| `need_brew` | Homebrew, installed if needed (with the user's consent). |
| `ensure_qt_venv` | PyQt6 in the venv Arrow Pad, Screen snip, the NordVPN tray and the window share (`$QT_VENV`). |
| `ensure_openvr VENV` | The openvr bindings in that venv, on SteamVR's own arm64 library; returns 1 without SteamVR. |
| `ensure_tweaks_venv`, `install_py_tool FILE` | A Python program in `~/.local/bin`, run on Frame Tweaks' shared venv. `pip_pinned VENV PKG` installs packages at tested versions. |
| `install_dashboard_patch NAME FILE`, `remove_dashboard_patch NAME`, `dashboard_patch_status NAME TEXT` | A SteamVR dashboard patch (see the VR environment tweaks; depend on `vr-dashboard`). |
| `sysctl_user ...` | `systemctl --user`, also from a desktop-mode shell. |
| `tweak_dir ID` | Another tweak's folder, to run its scripts. |

**Pinned downloads:** a `pin` file in the tweak's folder (`version=`, `url=`, `sha256=`;
optionally `latest=`, an API URL `dev/check-pins.sh` reads). `fetch_pinned <id> <file>` then
refuses anything that doesn't match the checksum.

## Linking a project

Some projects install themselves well and only need to be found, with a way to install,
uninstall and start them from the Frame Tweaks window. A **link** does that without integrating
anything: Frame Tweaks runs the project's own commands, as its README gives them, and doesn't
pin, check, copy or patch what they install. The project's own channel is what's trusted, and
the window says so (🔗 on its row, and on its details page). A linked tweak needs no scripts:
its manifest's `link:` says what they'd do.

```yaml
link:
  install: curl -fsSL https://example.org/get.sh | bash     # its own install command
  uninstall: curl -fsSL https://example.org/uninstall.sh | bash   # optional
  installed: [~/project, ~/.local/share/project]   # any of these existing means it's installed
  run: gtk-launch project-settings                 # optional: what the Run button starts
  readme: https://github.com/someone/project#readme   # its README, linked (not copied)
  restart: steamvr                                 # optional: SteamVR loads it only as it starts
run: {label: Open}                                 # the Run button's label, with link.run
```

- **Install and uninstall** run in the terminal the window opens, so the project's installer can
  ask its own questions. `lib/link.sh` does the scripts' part. One thing differs from running
  them yourself: `xdg-open vrmonitor://…`, which SteamVR's `vrpathreg` runs to tell its monitor
  app (not on the Frame) about a new driver, does nothing instead of failing noisily.
- **Status** is "installed" while any `installed` path exists. With `restart: steamvr` (a SteamVR
  driver, say), a path that changed after SteamVR started means it isn't loaded yet, and an
  uninstall after SteamVR started means SteamVR still runs it: either way the row offers
  ⟳ Restart SteamVR until SteamVR has restarted.
- **Updates:** ↻ runs its installer again, which updates most projects; Frame Tweaks' own updates
  leave it alone (it updates its own way).
- The other fields are as for any tweak; `changes`, `access` and `undo` describe what the
  project's installer does. Name the app in `app:` if it should stay installed when Frame Tweaks
  itself is uninstalled.

When to link and when to integrate: link a project that installs, updates and uninstalls itself
well. Integrate it (scripts of your own, its download pinned and checked) when it needs fitting
to the Frame, or when the installer window should vouch for exactly what it installs.

## Packs and Frame Tweaks updates

`api:` in `pack.md` is the version of this format the pack is written for. A Frame Tweaks that
only knows older versions leaves the pack out and says so, rather than misreading it. Fields
it doesn't know are reported as warnings and ignored, so packs can use newer optional fields.
The helpers in `lib/common.sh` and the manifest fields above are what a pack can rely on.

## Sharing a pack

1. **Give it a git repository of its own,** with the pack at its top: its `pack.md` and the
   tweak folders, as in [`examples/hello-pack/`](../examples/hello-pack/). Others add it with its
   link (**🧩 Packs → Add a pack from a link**, or `./install.sh mods add LINK`). Tag a version
   for a fixed one (`mods add LINK v1.0`); without a tag they follow its default branch, and
   each **Update** waits until they trust the pack again.
2. **Check it on each change** with Frame Tweaks' pack check: copy the example's
   [`.github/workflows/pack-check.yml`](../examples/hello-pack/.github/workflows/pack-check.yml)
   into your repository. It reads the pack as Frame Tweaks does (`./install.sh mods check`) and
   checks its shell scripts with ShellCheck:

   ```yaml
   - uses: AstronautCheetah/frame-tweaks/.github/actions/check-pack@main
     with:
       path: .          # where the pack is in your repository
   ```
3. **Get it listed** on [Community packs](community-packs.md), where others find it: open a
   [Share a pack](https://github.com/AstronautCheetah/frame-tweaks/issues/new?template=share_a_pack.yml)
   issue with its link and the commit to check. A maintainer checks that it loads and reads it
   for anything harmful before listing it.

## Sending a tweak to Frame Tweaks

A tweak in a pack is already in the shape the official packs use: to propose it for Frame
Tweaks itself, add its folder to `packs/core/` and its id to `packs/core/pack.md` (or the
same in `packs/integrations/` or `packs/third-party/` for a tweak that installs another
project's app), then
follow [CONTRIBUTING.md](../CONTRIBUTING.md).
