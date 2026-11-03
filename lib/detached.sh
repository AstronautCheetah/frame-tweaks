#!/bin/bash
# lib/detached.sh COMMAND...: run an install, update or removal the installer window started (in
# the terminal it opens) so that closing that terminal, the window or desktop mode doesn't cut it
# short. An update stopped halfway left tweaks of the old version beside files of the new one, and
# an update or reinstall may restart the very window that started it.
#
# How: as a transient user service (ft-install-PID) whose terminal is a pty that systemd-run --pty
# relays to this one, so questions, sudo's password prompt, colours and Ctrl+C work as before.
# Not a scope (systemd-run --scope): that only moves the process to a unit of its own; it stays on
# this terminal, whose hangup ends it all the same. Closed, the relay hangs up the service's pty:
# the command ignores that hangup (SIGHUP) and goes on, its output still in ./install.sh's log
# (start_log, ~/.local/state/frame-tweaks/logs), and its lock (take_lock) tells a window opened
# meanwhile that it's still running. (A question asked after that gets no answer: no, as without
# a terminal; a sudo prompt fails that one tweak.)
#
# With tmux (part of SteamOS), better: the command runs in a tmux session of its own (socket and
# session ft-install-PID) whose server is that service, and this terminal only attaches to it.
# Closing the terminal detaches; the install goes on with its pty, so a question or sudo's prompt
# waits for an answer, and `./install.sh attach` (the window's "Show it") brings it back, prompt
# and all. Its exit status goes through a file ($RUN_DIR/ft-install-PID.rc): tmux's attach
# doesn't hand it back.
#
# The splash (lib/splash.py) is drawn here, around the relay: inside, it would pass the hangup on
# to the command (it does, on purpose, in a terminal). Without a usable systemd (units_usable),
# the command runs as it did before, in this terminal. FRAME_TWEAKS_DRY_RUN: print the command.
set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")/.." || exit 1
# shellcheck source=lib/common.sh
source lib/common.sh
set +e     # (common.sh turns on -e for tweak scripts)
[ $# -gt 0 ] || die "lib/detached.sh COMMAND..."

if units_usable && command -v tmux >/dev/null && [ -z "${FRAME_TWEAKS_NO_TMUX:-}" ]; then
    unit="ft-install-$$"
    rcfile="$XDG_RUNTIME_DIR_USER/$unit.rc"
    rm -f "$rcfile"
    session_env_args
    inner=$(printf '%q ' "$@")
    note=$(t 'Closing this terminal does not stop it: it goes on, and "./install.sh attach" (or Show it in the window) brings it back.')
    # (Type=forking: tmux new-session -d starts its server and returns; the server is the unit.
    # remain-on-exit off: the session ends with the command, and so does the unit.)
    start=(env XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR_USER" DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR_USER/bus"
           systemd-run --user --quiet --collect --unit="$unit" -p Type=forking --working-directory="$REPO_DIR"
           --setenv=FRAME_TWEAKS_SPLASH=off "${SESSION_ENV_ARGS[@]}"
           -- tmux -L "$unit" new-session -d -s "$unit" -x 200 -y 50
           "printf '%s\n\n' $(printf '%q' "$note"); $inner; echo \$? > $(printf '%q' "$rcfile")"
           \; set-option -t "$unit" status off)      # (no status bar: it read as part of the output)
    if [ -n "${FRAME_TWEAKS_DRY_RUN:-}" ]; then
        printf 'would run:'; printf ' %q' "${start[@]}"; echo
        exit 0
    fi
    "${start[@]}" || exit 1
    attach=(tmux -L "$unit" attach-session -t "$unit")
    if command -v python3 >/dev/null; then python3 lib/splash.py -- "${attach[@]}"; else "${attach[@]}"; fi
    # (the terminal closed meanwhile: nothing runs this; the install goes on. Detached by hand
    # (tmux's Ctrl+B D): it goes on too, and this says so.)
    if tmux -L "$unit" has-session -t "$unit" 2>/dev/null; then
        echo "$(t 'Still running on its own: ./install.sh attach brings it back.')"
        exit 0
    fi
    for _ in 1 2 3 4 5 6 7 8 9 10; do [ -s "$rcfile" ] && break; sleep 0.2; done
    rc=$(cat "$rcfile" 2>/dev/null || echo 1)
    rm -f "$rcfile"
    exit "$rc"
elif units_usable; then
    unit="ft-install-$$"
    session_env_args
    # (env, not systemd_run_user: splash.py runs a program, not a shell function)
    # IgnoreSIGPIPE=no: as in a terminal (a service ignores SIGPIPE by default). No memory limit
    # or NoNewPrivileges here, unlike run_unit: installers use sudo.
    cmd=(env XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR_USER" DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR_USER/bus"
         systemd-run --user --pty --quiet --collect --unit="$unit" --working-directory="$REPO_DIR"
         -p IgnoreSIGPIPE=no --setenv=FRAME_TWEAKS_SPLASH=off "${SESSION_ENV_ARGS[@]}"
         -- bash -c 'trap "" HUP; printf "%s\n\n" "$1"; shift; exec "$@"' ft-install
         "$(t 'Closing this terminal does not stop it: it goes on as %s (its output: %s).' "$unit" "$HOME/.local/state/frame-tweaks/logs")"
         "$@")
else
    cmd=("$@")
fi
if [ -n "${FRAME_TWEAKS_DRY_RUN:-}" ]; then
    printf 'would run:'; printf ' %q' "${cmd[@]}"; echo
    exit 0
fi
if command -v python3 >/dev/null; then exec python3 lib/splash.py -- "${cmd[@]}"; fi
exec "${cmd[@]}"
