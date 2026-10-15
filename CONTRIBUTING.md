# Contributing

Thanks for helping. Reports from your Frame, translations, docs, fixes and new tweaks are all
welcome, and much of the work doesn't need a Frame.

- **Something broke?** Use **🐞 Report a problem** in the installer window: it saves a report
  and offers the bug form to attach it to (in a terminal, `./install.sh report`).
- **A Frame on a SteamOS or SteamVR version not under the README's "Tested on"?** Say what
  works and what doesn't, in an issue.
- **Translations:** [locale/README.md](locale/README.md).
- **A fix or a new tweak:** read on. For a big change, open an issue first (**Tweak idea**), so
  we can agree on the approach before you put the time in.

## What needs a Frame, and what doesn't

Frame Tweaks is shell and Python, plus a little JavaScript for the VR dashboard patches. Most of
it runs on any Linux PC, and CI runs every check on Ubuntu (x86_64).

- **Any Linux PC:** the installer (`install.sh`, `lib/`); every tweak's install, status and
  uninstall, in a throwaway home (`dev/test-tweaks.sh`); manifests and the generated docs;
  translations; the installer window's logic (its unit tests, and the window itself in dry-run
  mode, below).
- **Only a Steam Frame:** anything in VR (the dashboard patches, Arrow Pad's VR panel, the
  window's controller buttons), the two sessions' shared wallet and clipboard, and the
  programs the tweaks install, running for real (Dictation, Android Mirror, Screen snip…).

Say in your pull request what you tested, and on what; the maintainer tests the rest on a Frame.

## Words used here

- **The Frame:** Valve's Steam Frame, a standalone VR headset that runs SteamOS on an ARM
  (aarch64) processor, with a KDE Plasma *desktop mode*.
- **The two sessions:** Steam's VR session (X display `:0`, where windows float in VR) and desktop
  mode, a Plasma session nested inside it, with its own D-Bus and runtime folder. The *outer bus*
  is the VR session's D-Bus.
- **Tweak:** one row of the checklist: a folder with a README (its *manifest* is the README's
  YAML front matter) and `install.sh`, `status.sh` and `uninstall.sh`.
- **Pack:** a folder of tweaks. The three *official packs* (Original, Integrations, 3rd Party)
  are in `packs/`; anyone else's needs trusting first.
- **Helper:** a tweak others depend on, installed along with them (`tier: helper`), such as
  ydotool. Not to be confused with the shell helpers in `lib/common.sh`.
- **Pin:** a file recording the exact version and SHA256 of something a tweak downloads.
- **ALARM:** Arch Linux ARM, where adb and ydotool come from (SteamOS is Arch-based).
- **🧪 Experimental:** relies on SteamVR's internals; it checks them each time SteamVR starts and
  switches itself off when they change.
- **Dashboard patch:** JavaScript that VR dashboard patching puts into SteamVR's dashboard, a web
  page, through its DevTools port.

## Getting set up

1. Fork the repository on GitHub, clone your fork, and turn on the hooks (they check commit
   messages; see "Commit style"):

   ```sh
   git clone https://github.com/YOU/frame-tweaks && cd frame-tweaks
   dev/install-hooks.sh
   ```

2. Install what the checks use: Python 3.12 or newer, ShellCheck, and PyQt6 for the installer
   window's tests. On Ubuntu or Debian:

   ```sh
   sudo apt install shellcheck python3-venv xvfb libarchive-tools appstream desktop-file-utils
   python3 -m venv .venv && .venv/bin/pip install -c lib/python-constraints.txt PyQt6 pyyaml
   ```

   On a minimal system (a container, say), Qt also needs `libegl1 libgl1 libxkbcommon0
   libfontconfig1 libxtst6`. Other distributions have the same tools under similar names. On a
   Frame, only ShellCheck is missing (`brew install shellcheck`, with the
   [Homebrew](packs/original/homebrew/) tweak), the full installer window's Python already has
   PyQt6 (`~/.local/share/arrowpad/venv`), and SteamOS's own `/usr/bin/python3` has PyYAML.

3. Check that everything passes before you change anything: `dev/check.sh` (below).

To find your way around, [docs/DESIGN.md](docs/DESIGN.md) explains how the pieces fit together
(start with its "Layout" table), and [docs/mods.md](docs/mods.md) is the reference for a tweak's
files, its manifest, and the helpers its scripts can use.

## Checks

`dev/check.sh` runs the checks CI runs, on any Linux PC; `dev/check.sh docs tests` runs just
those. A check whose tool isn't installed is skipped, with a note saying how to get it. The
checks:

- `shell`: ShellCheck (`shellcheck -x -S warning`) on every shell script and the libraries they
  source, and that programs in `~/.local/bin` are replaced with `write_file` (`lib/common.sh`),
  never written into.
- `python`: every Python file compiles, the tweaks' modules too.
- `i18n`: the translation template is current (`dev/i18n.py extract` updates it).
- `commits`: your commits' messages ("Commit style", below).
- `manifests`: every manifest is valid and names its scripts (`python3 lib/sft.py mods check
  FOLDER`), dependencies resolve, and every pin is complete ("Pinned downloads").
- `tests`: the unit tests (`python3 -m unittest discover -s tests`). Some need PyQt6 and run
  headless (`QT_QPA_PLATFORM=offscreen`); the click-swap test also uses Xvfb, the manifest
  reader's is compared with PyYAML's where it's installed, and the Arch Linux ARM ones need
  Arch's `vercmp` (a Frame has it). `dev/check.sh` finds a Python with PyQt6 (`PYTHON=…`,
  `.venv`, then `python3`).
- `metadata`: the AppStream metadata and the desktop entry validate.
- `docs`: every tweak has a README row and relative links resolve (`dev/check-docs.py`), and the
  generated README and SECURITY sections match the manifests (`dev/gen-docs.py --check`).
- `tweaks`: install → status → uninstall of each offline-testable tweak in a throwaway home
  (`dev/test-tweaks.sh`), without network where user namespaces allow it.

A new tweak with a dashboard patch (`install_dashboard_patch`) is picked up by
`tests/test_vr_dashboard.py` automatically; one that can be tested offline says
`test: {offline: true}` in its manifest, and `dev/test-tweaks.sh` includes it.

## Trying a change

- **A tweak's scripts:** `dev/test-tweaks.sh ID` installs, checks and removes it in a throwaway
  home, with stand-ins for systemctl, flatpak, brew, kdialog and friends, and no network. It
  fails if anything is written outside that home: on a busy machine, other programs writing into
  `/tmp` meanwhile can trip it, so `TEST_IGNORE` (a regular expression of paths) leaves them out,
  e.g. `TEST_IGNORE='^/tmp/adb\.' dev/test-tweaks.sh`.
- **The installer window**, without changing anything:

  ```sh
  FRAME_TWEAKS_DRY_RUN=1 .venv/bin/python gui/frame-tweaks-gui.py
  ```

  With `FRAME_TWEAKS_DRY_RUN=1`, **Apply changes**, the ▶ buttons and the Wallet apps page
  print what they would do instead of doing it. Never run the window without it on a setup you
  care about: an unticked row means "remove". What the window saves for itself still saves (the
  language chosen in ⚙, a pack trusted or turned off, hidden rows): add `HOME=$(mktemp -d)` to
  keep even that out of your own settings. For extra safety, put a stand-in `konsole` first on
  your `PATH` (the window runs installs in Konsole).
- **On a Frame:** `./install.sh install ID` in your clone installs your copy of the tweak, and
  `./install.sh status ID` checks it. (On a PC it installs too, for real, into your home folder,
  and the Homebrew ones and Battery charge limit ask for sudo: use `dev/test-tweaks.sh` there.) `./install.sh gui` and `./install.sh menu` point the
  app-menu entry at the clone they run in; afterwards, `~/frame-tweaks/install.sh menu` points it
  back at your usual copy.

### Environment variables

| Variable | What it does |
|---|---|
| `FRAME_TWEAKS_DRY_RUN=1` | The installer window and the simple checklist show what they'd do instead of doing it. |
| `FRAME_TWEAKS_PACKS=DIR:DIR` | More pack folders (trusted like any other). |
| `FRAME_TWEAKS_LANGUAGE=es_419` | The language (`en`: English), instead of the one chosen in ⚙ or the keyboard's. |
| `FRAME_TWEAKS_CHANNEL=beta` | Pre-releases too, for `get.sh` and updates. `get.sh` keeps it in `~/.config/frame-tweaks/channel` (as `./install.sh channel beta` and ⚙ Preferences do). |
| `FRAME_TWEAKS_REPO=URL`, `FRAME_TWEAKS_DIR=DIR` | Where `get.sh` installs from, and into. |
| `FRAME_TWEAKS_ALLOW_UNSIGNED=1` | Lets an update take a release the release key didn't sign: an emergency switch. |
| `ALARM_MIRROR=URL`, `ALARM_ALLOW_DOWNGRADE=1` | The Arch Linux ARM mirror to use; allow a package older than one installed before. |
| `TEST_IGNORE=REGEX`, `TEST_WORK=DIR` | `dev/test-tweaks.sh`: paths other programs write meanwhile; keep its work folder there. |

The installer sets more for the tweaks' scripts (`FRAME_TWEAKS_LIB`, `FRAME_TWEAKS_REINSTALL`,
`FRAME_TWEAKS_UPDATING`): [docs/mods.md](docs/mods.md), "The scripts".

## Adding a tweak

Tweaks are self-contained folders in packs. Frame Tweaks' own are in three official packs:
`packs/original/` (tweaks written for Frame Tweaks), `packs/integrations/` (other projects' apps
that Frame Tweaks fits to the Frame: a tray icon, a key in the wallet, menu entries) and
`packs/third-party/` (other projects' apps installed as they are, from their pinned source or
release, with their own README appended). A tweak's README.md starts with its manifest (YAML
front matter), which is all the installer, the installer window, the docs and the tests know
about it. To add one:

1. Create `packs/PACK/ID/` with a `README.md` (manifest, then: problem, install, use,
   configuration, how it works, gotchas), `install.sh`, `uninstall.sh` and `status.sh`, plus
   any optional scripts. [examples/hello-pack/](examples/hello-pack/) is a small complete one to
   copy, and [docs/mods.md](docs/mods.md) explains every field and helper.
2. Add its id to `order:` in that pack's `pack.md`, where it belongs in the list (tweaks it
   doesn't list come after, alphabetically).
3. Run `dev/gen-docs.py` (the README tables, SECURITY.md's rows, and the intro and "What it
   changes" section of the tweak's README come from its manifest) and `dev/i18n.py extract` (its
   title, summary, what and why are translated). For a 3rd Party tweak with `upstream_readme:`,
   `dev/fetch-upstream-readmes.py ID` first. Then `dev/check.sh`.
4. A tweak with a window: a screenshot under its intro, and in the README's **Screenshots**
   (a folded `<details>` section). The Original tweaks' windows are drawn off-screen with sample
   content by `dev/screenshots.py` (into `docs/images/`; run it with a Python that has PyQt6,
   such as Arrow Pad's), so they can be taken again when a window changes and never show
   anything of the machine they're taken on; add yours there. Views that exist only in VR are
   taken in the headset.

House rules: nothing under `/usr` (SteamOS updates wipe it); no secrets on command lines or in
plain-text files; verify downloads when the publisher offers checksums; link to other projects
rather than copying their code, and credit the projects you borrow from (CREDITS.md and the
tweak's README).

## Sending a change

1. Push a branch to your fork and open a pull request against `main`. One topic per pull
   request; the template asks what you tested, and on what (a Steam Frame and its SteamOS
   version, or a PC).
2. CI runs the checks on every pull request (GitHub asks a maintainer to approve the first run
   from a new contributor).
3. A maintainer merges with *squash* or *rebase*. What you send is released under the
   project's [MIT licence](LICENSE), like the rest of it.

## Commit style

[Conventional Commits](https://www.conventionalcommits.org/), checked by
[commitizen](https://commitizen-tools.github.io/commitizen/) (`.cz.toml`): a first line
`<type>(<scope>): <subject>`, e.g. `fix(arrowpad): stop the overlay flickering`, then, after a
blank line, an optional body saying why. Keep the first line short; the body has room for the rest. Types: `feat`
(something new for users), `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`,
`style`, `revert`; the scope is optional, usually a tweak's id (or `gui`, `installer`, `lib`,
`dev`, `release`). With commitizen installed (`brew install commitizen` or
`pipx install commitizen`), `cz commit` asks for each part; the commit-msg hook checks every
message either way (`dev/check-commit-msg.sh`).

Co-author and attribution lines are up to you. You're responsible for what you submit, however
it was written. If you'd rather your own commits never pick up a tool's attribution line,
`git config frame-tweaks.refuseToolTrailers true` makes the hooks refuse them
(`dev/check-trailers.sh`).

## Translations

Text the installer window shows goes through gettext (`lib/i18n.py`): wrap it as `_("…")`, use
`ngettext(one, many, n)` for counts and `pgettext(context, "…")` when the same English word needs
different translations. Build text with placeholders inside the translated string
(`_("{n} tweaks installed").format(n=n)`), not by joining pieces, so translators see whole
sentences. A tweak's title, summary, what, why and settings labels are translated
automatically. Translators: see [locale/README.md](locale/README.md).

**English only is fine.** You don't need to translate anything, or speak another language:
write your text in English, marked as above, and the maintainers translate it before the next
release. Until then it shows in English, in every language. What helps:

- Mark every text people see, including tooltips and messages (`tests/test_marked_text.py`
  finds Qt text that isn't marked). Names (Frame Tweaks, NordVPN, SteamVR) stay as they are.
- Whole sentences with placeholders, as above; a `pgettext` context when a short word could be
  read two ways ("Right" as a direction, or a mouse button).
- If you can, run `dev/i18n.py extract`. If you don't, CI only warns on your pull request, and a
  maintainer runs it before merging.

After a change lands on main, the **Translations needed** issue (the Translations workflow)
lists what each language still lacks. A translation marked `# needs review` (one made by a
machine, say) is shown like any other, and counted apart until a person checks it
([locale/README.md](locale/README.md)).

## Pinned downloads

For a download from another project, add a `pin` file (`version=`, `url=`, `sha256=` or
`rev=`, and `latest=`, how `dev/check-pins.sh` finds newer releases) and fetch it with
`fetch_pinned`. Each pin also needs `mirror=`, `license=` and `license_file=` (Frame Tweaks'
copy, its licence, and the URLs of the licence texts at the pinned version, see below) or
`nomirror=` saying why it can't be copied.

## Changing files a tweak doesn't own

Before editing a user file, call `backup_file <tweak> <file>` and `restore_file` on uninstall
(KDE settings: `save_kconfig` / `restore_kconfig`, key by key). Prefer marked blocks you can
remove again (like Firefox's `user.js`). Never back up files holding secrets in plain text.

## Keeping up with upstream (maintainers)

A weekly workflow (**Upstream check**, `dev/check-upstream.sh`) keeps one issue labelled
`upstream-check` up to date, so nobody has to remember to look:

- 🔴 **Needs attention:** a pinned download vanished or changed, an Arch Linux ARM package we
  install is gone or needs a newer glibc than SteamOS has, or Homebrew's scrcpy moved to a major
  version Android Mirror's VR extras weren't tested with (they switch themselves off meanwhile).
- 🟡 **Worth a look:** newer versions to try (`dev/check-pins.sh`'s list, and anything newer than
  `lib/tested-versions`).

To take a newer version: read upstream's changes (`dev/bump-pin.py` prints the link), run
`dev/bump-pin.py <tweak>` (or `python`), test (the VR tweaks in the headset too), then commit it
on its own. After testing a newer scrcpy, android-tools or ydotool, update `lib/tested-versions`
(and for a new scrcpy major version, `SCRCPY_TESTED` in `adb-scrcpy/phone-touch`).
A tweak that installs another project shows that project's README below its own
(`upstream_readme:` in its manifest). After bumping its pin, point `upstream_readme:` at the same
version and run `dev/fetch-upstream-readmes.py <tweak>` and `dev/gen-docs.py`.

After bumping a pin that has a `mirror=` line, run `dev/mirror-pins.sh` to upload Frame Tweaks'
copy and its licence texts (a new pin needs `mirror=`, `license=` and `license_file=`, or
`nomirror=` saying why it can't be copied).

What happens when nobody does: installed tweaks keep working (nothing updates itself). Fresh
installs fall back where they can (Frame Tweaks' copy of a vanished pinned download; newest
Python packages if the pinned ones won't install; the working adb/ydotool if a new build won't
run), and 🧪 experimental tweaks switch themselves off after a SteamVR change they don't
recognise.

## Working on several changes at once (maintainers)

`main` is the only branch. To work on two things in parallel, `dev/agent-worktree.sh add <name>`
makes a separate checkout under `tmp/` (a git worktree of `origin/main`), and
`dev/safe-push.sh` publishes its commits onto `main`, replaying them if `main` moved meanwhile.
`dev/agent-worktree.sh remove <name>` cleans up.

## Releasing (maintainers)

Add changes under `## Unreleased` in CHANGELOG.md as you go, then run the **Release** workflow
(Actions → Release → Run workflow, choose patch/minor/major). It dates the section, bumps
VERSION, tags `vX.Y.Z` and drafts a GitHub release to review and publish. The tag is what
`get.sh` and `./install.sh update` install, so the release is out as soon as the workflow pushes
it; the draft is only its page of notes on GitHub.

**Test releases for testers.** Tick **Pre-release** in the Release workflow: it tags
`vX.Y.Z-rc.N` and drafts a release marked as a pre-release; publish it as one, so GitHub's
"latest" stays on the stable release. Only people who opted in get it. Send testers this
install command (it keeps their choice for later updates), or point them to ⚙ Preferences →
**Get test releases too**:

```sh
curl -fsSL https://raw.githubusercontent.com/AstronautCheetah/frame-tweaks/main/get.sh | FRAME_TWEAKS_CHANNEL=beta bash
```

Testers go back with the same box unticked (or `./install.sh channel stable`): they stay on the
test release until the next stable one is out, which ranks above its test releases, or go back
at once (the window offers it; `./install.sh update --to stable`). An update never moves to an
older release unasked.

**How many people use it** (Frame Tweaks itself never reports anything): GitHub counts clones
(each install is one; updates may count too) and page views, but keeps only 14 days. The **Traffic**
workflow saves them daily into `traffic.csv` on the draft release "traffic" (maintainers only),
with each release's downloads. It needs a fine-grained token for this repository with
**Administration: read** (what GitHub's traffic API asks for), as the secret `TRAFFIC_TOKEN`:
`gh secret set TRAFFIC_TOKEN`, pasting the token when asked. Without it the workflow only warns.
Read it with `gh release download traffic --pattern traffic.csv`.

**Translations first.** The workflow stops unless the translation template is current and every
language has every text (`dev/i18n.py stats --strict`), so before releasing: `dev/i18n.py
extract` and `update`, then translate what's missing (`dev/i18n.py export LANG DIR`,
[locale/BATCH.md](locale/BATCH.md)). Texts marked as needing review don't hold a release up.
"Release with texts not translated yet" overrides it, for an urgent fix: they show in English.

**Release tags are signed** with an SSH key: the workflow signs with the private key in the
repository secret `RELEASE_SIGNING_KEY`, and `./install.sh update` refuses a release whose tag
isn't signed by a key listed in `dev/release-signers` *as already installed* (`verify_release`
in `lib/common.sh`). Setting it up, once:

```sh
ssh-keygen -t ed25519 -N "" -C "Frame Tweaks releases" -f ~/frame-tweaks-release-key
gh secret set RELEASE_SIGNING_KEY < ~/frame-tweaks-release-key
```

Put the public key (`~/frame-tweaks-release-key.pub`) in `dev/release-signers` as
`releases namespaces="git" <type> <key>`, commit it, and keep the private key somewhere safe
(a password manager), not on the Frame. **Changing the key:** add the new public key to
`dev/release-signers` and release with the old one first, so installed copies learn the new key
before a release signed with it arrives; then switch the secret.
