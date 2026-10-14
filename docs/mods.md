# Packs: adding your own tweaks

Every tweak Frame Tweaks offers comes from a **pack**: a folder of tweak folders. Its own tweaks
are the official pack, [`packs/official/`](../packs/official/), and they're loaded exactly like
anyone else's. To add programs or fixes of your own, write a pack. You don't need to change
Frame Tweaks itself, and your pack survives its updates.

Start from the example, [`examples/hello-pack/`](../examples/hello-pack/): one small tweak that
uses most of what's described here.

## Where packs go, and trust

- **Your packs:** `~/.local/share/frame-tweaks/packs/<pack>/` (the installer window's
  **🧩 Packs → Open packs folder**). Packs elsewhere: list their folders in `FRAME_TWEAKS_PACKS`,
  separated by `:`.
- **Trust:** a pack's tweaks run as you, with your files and passwords in reach, so a new pack
  is listed but not used until you trust it: **🧩 Packs → Trust…**, or
  `./install.sh mods trust "<pack name>"`. Trust covers the pack's files as they are then; if
  any change (an update, or something tampering with them), the pack waits until you trust it
  again.
- `./install.sh mods` lists the packs, whether each is in use, and any problems.
  `./install.sh mods untrust "<pack name>"` stops using one; tweaks of it you installed stay
  until you uninstall them.

## A pack

```
my-pack/
  pack.md            optional: the pack's name, author, api, category and tweak order
  my-tweak/
    README.md        the manifest (front matter) and the tweak's documentation
    install.sh  uninstall.sh  status.sh
    run.sh  check-system.sh  update-check.sh  migrate.sh  stopped.sh    (optional)
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
| `category` | Its group in the list: an existing one (Accessibility, Convenience, VR environment, Privacy & security, System, Developer) or a new one. |
| `tier` | `core` (a fix for the Frame), `extras` (an app setup) or `helper` (something other tweaks need). |
| `summary` | One line, shown in the list and in `./install.sh list`. |
| `what`, `why` | Its details page. |
| `author` | Who made it ("Made by"). |
| `changes`, `access`, `survives_updates`, `undo` | What it changes on the system, any unusual access it has, whether it survives SteamOS updates, and how to undo it (the official README tables and SECURITY.md are made from these). |

**Optional:**

| Key | Example | What it does |
|---|---|---|
| `depends` | `[ydotool]` | Tweaks installed first (from any pack in use). If one is missing, this one isn't offered. |
| `source` | `{relation: from, url: https://…}` | The project it comes from (`from`) or uses (`uses`), linked in the list. |
| `hidden_by_default` | `true` | Hidden in the list until you choose to show it. |
| `experimental` | text | Marks it 🧪 and says what relies on another program's internals and what happens when they change. |
| `icon` | `{file: icon.png}` · `{theme: face-smile}` · `{flatpak: org.app.Id}` | Its icon in the list: a picture in its folder, a Breeze icon name, or an installed Flatpak's icon (these can be combined; tried in the order flatpak, file, theme). |
| `run` | `{label: Open}` | The list's Run button, which runs `run.sh` (the tweak needs one). |
| `processes` | `["^~/.local/bin/my-daemon"]` | Programs it keeps running (`pgrep -f` patterns, `~` for your home folder). They're stopped before it's uninstalled or reinstalled, then `stopped.sh` runs if it has one. |
| `settings` | (below) | A settings page in the installer window, and `./install.sh settings ID`. |
| `known_issue` | `{version, short, long, latest}` | A problem with an upstream version: `short` on its row, `long` on its details page, and a check whether `latest` (a GitHub releases API URL) has something newer than `version`. |
| `wallet_apps` | `[org.signal.Signal]` | Apps it sets up to use the shared KDE wallet (the Wallet apps page says so). |
| `test` | `{offline: true, keeps: [.config/…], needs: [orca]}` | `dev/test-tweaks.sh` installs, checks and removes it in a throwaway home folder (only official and example tweaks run in CI). `keeps`: the files its uninstall leaves on purpose; `needs`: commands it needs to be tested. |
| `replaces` | `true` | Use it instead of the tweak with the same id in another pack. |
| `upstream_readme` | `https://raw.githubusercontent.com/owner/repo/v1.0/README.md` | For a tweak that installs another project: that project's README at the pinned version. In the official pack, `dev/fetch-upstream-readmes.py` copies it (with its pictures) into the tweak's folder and `dev/gen-docs.py` appends it below the tweak's own README. |

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
```

Only the listed keys are written; anything else in the file is kept. Your program reads the
file itself (a `shell` file can be `source`d).

### The YAML

The front matter is a strict, simple form of YAML, so it means the same to Frame Tweaks, to
other YAML tools and to whoever reads it:

- `key: value`; nested mappings and lists indented with spaces; `[a, b]` and `{k: v}` on one line.
- Long text: `key: >-` with the text indented on the next lines (lines are joined with spaces;
  a blank line starts a new line). `|` keeps line breaks as they are.
- **Quote** a value that starts with `` ` ``, `[`, `{`, `*`, `&`, `!`, `|`, `>`, `'`, `"`, `%`
  or `@`, that contains `: ` or ` #`, or that YAML could read as something else: `yes`, `no`,
  `on`, `off` (any case), dates, and numbers like `010` or `1_000`. Unquoted, these are refused,
  with the line number, rather than guessed at.
- No anchors (`&`), aliases (`*`) or tags (`!`).

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
(`~/.local/bin`), `$APPS` (the app menu's folder) and the helpers below.

- `install.sh`: installs it. It must be safe to run again, and install only into your home
  folder (SteamOS's system partition is read-only and updates wipe it). Exit non-zero on failure.
- `uninstall.sh`: removes what `install.sh` added, keeps the user's settings and data, and says
  what it kept.
- `status.sh`: prints one line and exits through `status_ok` (installed and working),
  `status_missing` (not installed) or `status_warn` (installed, needs attention). It must
  change nothing; the installer window runs it often.
- `run.sh` (with `run:`): what the Run button does. Launch apps through their menu entry
  (`gtk-launch <id>`), so wallet gates apply.
- `check-system.sh`: whether the SteamOS or SteamVR parts it relies on are still there (one
  line; exit 0 or 1); `./install.sh check-system` and updates run it.
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
| `remove_files PATH...` | Removes them, saying what went. |
| `backup_file TWEAK FILE`, `restore_file TWEAK FILE` | Keep a user file as it was before you changed it, and put it back on uninstall. KDE settings: `save_kconfig` / `restore_kconfig`. |
| `fetch_pinned ID OUT [PIN]` | Downloads the file a `pin` names and checks its SHA256 (see below). |
| `alarm_fetch REPO NAME DEST` | An Arch Linux ARM package, signature-checked, unpacked into DEST. `runs_here BINARY` says whether it can run on SteamOS. |
| `need_brew` | Homebrew, installed if needed (with the user's consent). |
| `ensure_tweaks_venv`, `install_py_tool FILE` | A Python program in `~/.local/bin`, run on Frame Tweaks' shared venv. `pip_pinned VENV PKG` installs packages at tested versions. |
| `install_dashboard_patch NAME FILE`, `remove_dashboard_patch NAME`, `dashboard_patch_status NAME TEXT` | A SteamVR dashboard patch (see the VR environment tweaks; depend on `vr-dashboard`). |
| `sysctl_user ...` | `systemctl --user`, also from a desktop-mode shell. |
| `tweak_dir ID` | Another tweak's folder, to run its scripts. |

**Pinned downloads:** a `pin` file in the tweak's folder (`version=`, `url=`, `sha256=`;
optionally `latest=`, an API URL `dev/check-pins.sh` reads). `fetch_pinned <id> <file>` then
refuses anything that doesn't match the checksum.

## Packs and Frame Tweaks updates

`api:` in `pack.md` is the version of this format the pack is written for. A Frame Tweaks that
only knows older versions leaves the pack out and says so, rather than misreading it. Fields
it doesn't know are reported as warnings and ignored, so packs can use newer optional fields.
The helpers in `lib/common.sh` and the manifest fields above are what a pack can rely on.

## Sending a tweak to Frame Tweaks

A tweak in a pack is already in the shape the official pack uses: to propose it for Frame
Tweaks itself, add its folder to `packs/official/` and its id to `packs/official/pack.md`, then
follow [CONTRIBUTING.md](../CONTRIBUTING.md).
