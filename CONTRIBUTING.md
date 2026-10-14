# Contributing

Tweaks are self-contained folders in packs; Frame Tweaks' own are the official pack,
`packs/official/`. A tweak's README.md starts with its manifest (YAML front matter), which is
all the installer, the installer window, the docs and the tests know about it. The format, the
scripts and the helpers they can use: [docs/mods.md](docs/mods.md). To add one:

1. Create `packs/official/<id>/` with a `README.md` (manifest, then: problem, install, use,
   configuration, how it works, gotchas), `install.sh`, `uninstall.sh` and `status.sh`, plus
   any optional scripts. [examples/hello-pack/](examples/hello-pack/) is a small complete one.
2. Add its id to `order:` in `packs/official/pack.md`, where it belongs in the list.
3. Run `dev/gen-docs.py` (the README tables, SECURITY.md's rows and its "At a glance" box come
   from its manifest), then the checks CI runs (see "Checks" below).

House rules: nothing under `/usr` (SteamOS updates wipe it); no secrets on command lines or
in plain-text files; verify downloads when the publisher offers checksums; credit the
projects you borrow from.

**Testing installers:** the installer window honours `FRAME_TWEAKS_DRY_RUN=1` (it prints the
plan instead of running it). Never test the window or the uninstall paths against a real setup
without `FRAME_TWEAKS_DRY_RUN=1` and a stub `konsole` in `PATH`: an unticked checklist means
"remove".

## Sending a change

1. Fork the repository, make a branch in your fork, and open a pull request against `main`.
   One topic per pull request; say what you tested, and on what (a Steam Frame, SteamOS version).
2. Run `dev/install-hooks.sh` once after cloning: the hooks check commit messages (below).
3. CI runs the checks below on every pull request. A maintainer merges with *squash* or
   *rebase*.

## Commit style

[Conventional Commits](https://www.conventionalcommits.org/), checked by
[commitizen](https://commitizen-tools.github.io/commitizen/) (`.cz.toml`): a first line
`<type>(<scope>): <subject>` in the imperative, under about 72 characters, e.g.
`fix(arrowpad): stop the overlay flickering`, then an optional body saying why. Types: `feat`
(something new for users), `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`,
`style`, `revert`; the scope is optional, usually a tweak's id (or `gui`, `installer`, `lib`,
`dev`, `release`). With commitizen installed (`brew install commitizen` or
`pipx install commitizen`), `cz commit` asks for each part; the commit-msg hook checks every
message either way (`dev/check-commit-msg.sh`).

Co-author and attribution lines are up to you. You're responsible for what you submit, however
it was written. If you'd rather your own commits never pick up a tool's attribution line,
`git config frame-tweaks.refuseToolTrailers true` makes the hooks refuse them
(`dev/check-trailers.sh`).

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

## Checks

What CI runs, and what to run before sending a change:

- `shellcheck -x -S warning` on shell scripts; `python3 -m py_compile` on Python.
- `python3 -m unittest discover -s tests`: unit tests. Some need PyQt6 (the installer window)
  and run headless with `QT_QPA_PLATFORM=offscreen`; the click-swap test also uses `Xvfb`. Use
  the venv the installer window sets up (`~/.local/share/arrowpad/venv/bin/python`), or
  `pip install PyQt6` (versions in `lib/python-constraints.txt`).
- `dev/gen-docs.py --check`: generated README/SECURITY sections match the manifests.
- `python3 lib/sft.py mods check packs/official`: every manifest is valid and its scripts exist.
- `dev/check-docs.py`: every tweak has a README row; relative links resolve.
- `dev/test-tweaks.sh`: install → status → uninstall in a throwaway home.
- `dev/check-commit-msg.sh --all`: commit message format (above).
- A new tweak with a dashboard patch (`install_dashboard_patch`) is picked up by
  `tests/test_vr_dashboard.py` automatically; one that can be tested offline says
  `test: {offline: true}` in its manifest, and `dev/test-tweaks.sh` includes it.

### Keeping up with upstream (maintainers)

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
VERSION, tags `vX.Y.Z` and drafts a GitHub release to review and publish. Pre-releases
(`vX.Y.Z-rc.N`) only reach the beta channel.
