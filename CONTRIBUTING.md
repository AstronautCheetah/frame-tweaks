# Contributing

Tweaks are self-contained folders. To add one:

1. Add a line to `components.tsv` (tab-separated, see its header): id, title, category
   (Accessibility, Convenience, VR windows, Privacy & security, System, Developer), dependencies, one-line description,
   source (`relation|url`, if it comes from another project), author, why it's useful on the
   Frame, flags (`hidden-by-default`, `helper`). The installer window shows all of it.
2. Create `<id>/` with:
   - `install.sh`: idempotent (safe to re-run), installs only under `$HOME`. Start with
     `source "$(dirname "$0")/../lib/common.sh"` for `$BIN`, `$APPS`, `say`/`warn`/`die`,
     `ensure_path`, `alarm_fetch`, `install_desktop` and friends.
   - `status.sh`: prints one line and exits via `status_ok` (installed and healthy),
     `status_missing` (not installed) or `status_warn` (installed, needs attention).
     It must change nothing.
   - `uninstall.sh`: removes what `install.sh` added (`remove_files`), keeps user settings and
     data, and says what it kept.
   - `README.md`: problem, install, use, configuration, how it works, gotchas.
   - optional `run.sh`, with a `# label: Open` line: what the installer window's ▶ button does
     (launch through the app's menu entry with `gtk-launch <id>` so gates apply). Without it the
     button shows Help.
3. Run the checks CI runs (see "Checks" below).

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

A short imperative first line (`arrowpad: fix overlay flicker`), then an optional body saying
why. **No AI attribution**: no `Co-authored-by` line naming an AI tool or bot (Claude,
Anthropic, Copilot, ChatGPT, OpenAI, Gemini, Codex, Cursor, Aider, `[bot]` accounts), and no
`Claude-Session`, `Assisted-by`, `Generated-by` or "Generated with [...]" lines, whatever a tool
suggests. You're responsible for what you submit, however it was written. Human co-authors are
welcome: `Co-authored-by: Jane Doe <jane@example.com>` is fine (GitHub adds those when it
squash-merges a pull request with several authors). `dev/check-trailers.sh` is the rule; the
hooks and CI run it.

## Running programs (`<tweak>/processes`)

If a tweak starts programs that keep running, list them in `processes` (one `pgrep -f`
pattern per line, `~` for the home folder). The installer stops them before uninstalling or
reinstalling the tweak.

## Docs metadata (`<tweak>/meta`)

Every tweak has a `meta` file: emoji, name, group (core / extras / helper), what you get, why,
what it changes, unusual access, whether it survives SteamOS updates, and how to undo it. The
README tables, SECURITY.md's change list and each tweak's "At a glance" box are generated from
it: edit `meta`, then run `dev/gen-docs.py` (CI fails when they're out of date). For example:

```text
emoji: 📱
name: Android Mirror
group: extras
what: Mirror and control your Android phone in a desktop window.
why: Use your phone without taking the headset off.
changes: `adb` in `~/.local/lib/android-tools`, Homebrew `scrcpy`, `phone` launcher
access: Network connection to your phone's wireless debugging
survives-updates: Yes (everything is in your home folder)
undo: `./install.sh uninstall adb-scrcpy`
```

Other optional files: `check-system.sh` (are the SteamOS/SteamVR parts it relies on still
there? one line, exit 0 or 1), `processes` (above), and for a pinned upstream download a `pin`
file (`version=`, `url=`, `sha256=` or `rev=`, and `latest=`, how `dev/check-pins.sh` finds
newer releases).

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
- `dev/gen-docs.py --check`: generated README/SECURITY sections match each tweak's `meta`.
- `dev/check-docs.py`: every tweak has a README row; relative links resolve.
- `dev/test-tweaks.sh`: install → status → uninstall in a throwaway home.
- `git log --format=%B | dev/check-trailers.sh`: commit messages (above).
- A new tweak with a dashboard patch (`install_dashboard_patch`) is picked up by
  `tests/test_vr_dashboard.py` automatically; one that can be tested offline belongs in
  `dev/test-tweaks.sh`'s default list.

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
After bumping a pin that has a `mirror=` line, run `dev/mirror-pins.sh` to upload Frame Tweaks'
copy (a new pin needs `mirror=` and `license=`, or `nomirror=` saying why it can't be copied).

What happens when nobody does: installed tweaks keep working (nothing updates itself). Fresh
installs fall back where they can (Frame Tweaks' copy of a vanished pinned download; newest
Python packages if the pinned ones won't install; the working adb/ydotool if a new build won't
run), and 🧪 experimental tweaks switch themselves off after a SteamVR change they don't
recognise.

## Releasing (maintainers)

Add changes under `## Unreleased` in CHANGELOG.md as you go, then run the **Release** workflow
(Actions → Release → Run workflow, choose patch/minor/major). It dates the section, bumps
VERSION, tags `vX.Y.Z` and drafts a GitHub release to review and publish. Pre-releases
(`vX.Y.Z-rc.N`) only reach the beta channel.
