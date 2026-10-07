# Contributing

Tweaks are self-contained folders. To add one:

1. Add a line to `components.tsv`: `id<TAB>Title<TAB>dependencies<TAB>one-line description`.
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
3. Run the checks CI runs: `shellcheck -x -S warning` on shell scripts, `python3 -m
   py_compile` on Python, and `./install.sh status`.

House rules: nothing under `/usr` (SteamOS updates wipe it); no secrets on command lines or
in plain-text files; verify downloads when the publisher offers checksums; credit the
projects you borrow from.

**Testing installers:** the installer window honours `FRAME_TWEAKS_DRY_RUN=1` too (prints the plan).
 never test the GUI or uninstall paths against a real setup without
`FRAME_TWEAKS_DRY_RUN=1` and a stub `konsole` in `PATH`. An unticked checklist means "remove".
