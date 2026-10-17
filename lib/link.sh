#!/bin/bash
# A linked project (its manifest's link:, docs/mods.md "Linking a project"): what its install.sh,
# uninstall.sh, status.sh and run.sh would do, from the link's fields. Frame Tweaks runs the
# project's own install and uninstall commands, as its README gives them, in the terminal it
# opens for installs (they may ask questions); nothing of the project is pinned, checked, copied
# or patched here, so the project's own channel is what's trusted.
#   lib/link.sh install|uninstall|status|run|update-check ID
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
action=${1:?} id=${2:?}
field() { python3 "$REPO_DIR/lib/sft.py" link "$id" "$1"; }
name=$(field title) || exit 1
# (its commands run with lib/link-path first on PATH: xdg-open there drops SteamVR's vrmonitor://
# links, which nothing on the Frame opens)
LINK_PATH="$REPO_DIR/lib/link-path:$PATH"
# restart: steamvr: when it was uninstalled (SteamVR runs it until it restarts)
UNLOADED="$HOME/.local/state/frame-tweaks/unloaded/$id"

case $action in
    install)
        cmd=$(field install)
        say "$(t "Installing %s with its own installer (from the project, not checked by Frame Tweaks):" "$name")"
        echo "  $cmd"
        PATH=$LINK_PATH bash -c "$cmd" || exit
        rm -f "$UNLOADED" ;;
    uninstall)
        cmd=$(field uninstall)
        [ -n "$cmd" ] || die "$(t "%s has no uninstall command here: see its README" "$name")"
        say "$(t "Uninstalling %s with its own uninstaller:" "$name")"
        echo "  $cmd"
        PATH=$LINK_PATH bash -c "$cmd" || exit
        if [ "$(field restart)" = steamvr ]; then
            mkdir -p "${UNLOADED%/*}" && touch "$UNLOADED"
            say "$(t 'Restart SteamVR to unload it: ⟳ Restart SteamVR on its row in the Frame Tweaks window, or reboot.')"
        fi ;;
    status)
        # restart: steamvr: SteamVR loads it only as it starts, so a SteamVR that started before
        # the install hasn't, and one that started before the uninstall still runs it (the
        # installer window offers to restart it either way). The install: Frame Tweaks' record of
        # it, rewritten by every install and ↻, or a newer change to the path. (Not the path's
        # date alone: an installer that copies with cp -p keeps the date the file had in the
        # project, often older than SteamVR.)
        restart=$(field restart)
        while IFS= read -r path; do
            path=${path/#\~/$HOME}
            [ -e "$path" ] || continue
            [ "$restart" = steamvr ] &&
                { vr_started_before "$HOME/.local/state/frame-tweaks/installed/$id" || vr_started_before "$path"; } &&
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
    update-check)
        # "<installed> <newest>" for the window's update hint (↻ then installs it): what its version:
        # command prints, and its GitHub project's newest release, from where the "latest release"
        # link leads (no API: no rate limit). Nothing when either is missing, or the installed
        # one isn't a version ("unknown": built without its tags).
        cmd=$(field version) repo=$(field github)
        [ -n "$cmd" ] && [ -n "$repo" ] || exit 1
        cur=$(PATH=$LINK_PATH bash -c "$cmd" 2>/dev/null | head -1) cur=${cur#v}
        case $cur in [0-9]*) ;; *) exit 1 ;; esac
        latest=$(curl -fsI --max-time 8 "https://github.com/$repo/releases/latest" |
                 sed -n 's|^[Ll]ocation: .*/releases/tag/v\{0,1\}\([^[:space:]]*\).*|\1|p' | head -1)
        [ -n "$latest" ] && echo "$cur $latest" ;;
    *) die "lib/link.sh install|uninstall|status|run|update-check ID" ;;
esac
