#!/bin/bash
# A linked project (its manifest's link:, docs/mods.md "Linking a project"): what its install.sh,
# uninstall.sh, status.sh and run.sh would do, from the link's fields. Frame Tweaks runs the
# project's own install and uninstall commands, as its README gives them, in the terminal it
# opens for installs (they may ask questions); nothing of the project is pinned, checked, copied
# or patched here, so the project's own channel is what's trusted.
#   lib/link.sh install|uninstall|status|run ID
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
action=${1:?} id=${2:?}
field() { python3 "$REPO_DIR/lib/sft.py" link "$id" "$1"; }
name=$(field title) || exit 1
# restart: steamvr: when it was uninstalled (SteamVR runs it until it restarts)
UNLOADED="$HOME/.local/state/frame-tweaks/unloaded/$id"

case $action in
    install)
        cmd=$(field install)
        say "$(t "Installing %s with its own installer (from the project, not checked by Frame Tweaks):" "$name")"
        echo "  $cmd"
        bash -c "$cmd" || exit
        rm -f "$UNLOADED" ;;
    uninstall)
        cmd=$(field uninstall)
        [ -n "$cmd" ] || die "$(t "%s has no uninstall command here: see its README" "$name")"
        say "$(t "Uninstalling %s with its own uninstaller:" "$name")"
        echo "  $cmd"
        bash -c "$cmd" || exit
        if [ "$(field restart)" = steamvr ]; then
            mkdir -p "${UNLOADED%/*}" && touch "$UNLOADED"
            say "$(t 'Restart SteamVR to unload it (reboot, or: %s).' "steamvr restart")"
        fi ;;
    status)
        # restart: steamvr: SteamVR loads it only as it starts, so a SteamVR that started before
        # the install hasn't, and one that started before the uninstall still runs it (the
        # installer window offers to restart it either way).
        restart=$(field restart)
        while IFS= read -r path; do
            path=${path/#\~/$HOME}
            [ -e "$path" ] || continue
            [ "$restart" = steamvr ] && vr_started_before "$path" &&
                status_restart "$(t 'installed; restart SteamVR to load it')"
            status_ok "$(t "installed by its own installer (it updates its own way)")"
        done < <(field installed)
        [ "$restart" = steamvr ] && vr_started_before "$UNLOADED" &&
            status_unload "$(t 'uninstalled; restart SteamVR to unload it')"
        status_missing "$(t 'not installed')" ;;
    run)
        cmd=$(field run)
        [ -n "$cmd" ] || die "$(t '%s has nothing to run' "$name")"
        exec bash -c "$cmd" ;;
    *) die "lib/link.sh install|uninstall|status|run ID" ;;
esac
