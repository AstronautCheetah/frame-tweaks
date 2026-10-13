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
3. Run the checks CI runs: `shellcheck -x -S warning` on shell scripts, `python3 -m
   py_compile` on Python, and `./install.sh status`.

House rules: nothing under `/usr` (SteamOS updates wipe it); no secrets on command lines or
in plain-text files; verify downloads when the publisher offers checksums; credit the
projects you borrow from.

**Testing installers:** the installer window honours `FRAME_TWEAKS_DRY_RUN=1` too (prints the plan).
 never test the GUI or uninstall paths against a real setup without
`FRAME_TWEAKS_DRY_RUN=1` and a stub `konsole` in `PATH`. An unticked checklist means "remove".

## Commit style

A short imperative first line (`arrowpad: fix overlay flicker`), then an optional body saying
why. **No attribution trailers**: no `Co-Authored-By`, `Claude-Session`, `Assisted-by`,
`Generated-by` or "Generated with [...]" lines, whatever a tool or agent suggests. Run
`dev/install-hooks.sh` once after cloning; the hooks and CI enforce it. Agents: see
[CLAUDE.md](CLAUDE.md).

## Working in parallel

`main` is the only branch. When more than one session works on the repo, each uses its own
worktree (`dev/agent-worktree.sh add <slug>`) and publishes with `dev/safe-push.sh`. See
[docs/claude/parallel-work.md](docs/claude/parallel-work.md).

## Running programs (`<tweak>/processes`)

If a tweak starts programs that keep running, list them in `processes` (one `pgrep -f`
pattern per line, `~` for the home folder). The installer stops them before uninstalling or
reinstalling the tweak.

## Docs metadata (`<tweak>/meta`)

Every tweak has a `meta` file: emoji, name, group (core / extras / helper), what you get, why,
what it changes, unusual access, whether it survives SteamOS updates, and how to undo it. The
README tables, SECURITY.md's change list and each tweak's "At a glance" box are generated from
it: edit `meta`, then run `dev/gen-docs.py` (CI fails when they're out of date).

## Changing files a tweak doesn't own

Before editing a user file, call `backup_file <tweak> <file>` and `restore_file` on uninstall
(KDE settings: `save_kconfig` / `restore_kconfig`, key by key). Prefer marked blocks you can
remove again (like Firefox's `user.js`). Never back up files holding secrets in plain text.

## Checks before a release

- `dev/test-tweaks.sh`: install → status → uninstall in a throwaway home (also runs in CI).
- `dev/check-docs.py`: every tweak has a README row; relative links resolve.
- `dev/check-pins.sh`: upstream releases newer than a tweak's `pin`. Bump a pin only after
  reading the release, in its own commit, with the new version, URL and SHA256.
- `python3 -m unittest discover -s tests`: unit tests (installer-window logic, shell helpers,
  curvature), also in CI.
- **Releasing:** add changes under `## Unreleased` in CHANGELOG.md as you go, then run the
  **Release** workflow (Actions → Release → Run workflow, choose patch/minor/major). It dates the
  section, bumps VERSION, tags `vX.Y.Z` and drafts a GitHub release to review and publish.
  Pre-releases (`vX.Y.Z-rc.N`) only reach the beta channel. Tags and pushed commits are never
  moved or rewritten.
