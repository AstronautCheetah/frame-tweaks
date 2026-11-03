#!/bin/bash
# A linked project (its manifest's link:, docs/mods.md "Linking a project"): what its install.sh,
# uninstall.sh, status.sh and run.sh would do, from the link's fields. Frame Tweaks runs the
# project's own install and uninstall commands, as its README gives them, in the terminal it
# opens for installs (they may ask questions); nothing of the project is copied or patched here,
# so the project's own channel (and its own checksums) is what's trusted.
#   lib/link.sh install|uninstall|status|run|update-check ID
# A link with a tested version (link.tested; lib/tested-versions' link-<id> for the official
# packs) installs that one unless asked for the newest: FT_LINK_CHOICE=ID:newest (or ID:tested),
# from ./install.sh link-version. Without either, a reinstall keeps the choice installed before.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
action=${1:?} id=${2:?}
field() { python3 "$REPO_DIR/lib/sft.py" link "$id" "$1"; }
name=$(field title) || exit 1
# (its commands run with lib/link-path first on PATH: xdg-open there drops SteamVR's vrmonitor://
# links, which nothing on the Frame opens)
LINK_PATH="$REPO_DIR/lib/link-path:$PATH"
# restart: steamvr: when it was uninstalled (SteamVR runs it until it restarts)
UNLOADED="$HOME/.local/state/frame-tweaks/unloaded/$id"
# Which version Frame Tweaks installed: "tested <version>" or "newest" (lib/sft.py link_choice).
# ./install.sh forget_version removes it with the install record.
CHOICE="$HOME/.local/state/frame-tweaks/link-version/$id"
# restart: steamvr: the version an install put back over the same version SteamVR had loaded
# already (a ↻ reinstall, say): no restart is needed for that one, though the install record it
# rewrote is newer than SteamVR. Gone with any other install, and with the uninstall.
LOADED="$HOME/.local/state/frame-tweaks/loaded/$id"

# same_version A B: the same release (a leading v either way), or for a commit, one abbreviating
# the other (lib/tested-versions has it whole, a version: command prints it short).
same_version() {
    local a=${1#v} b=${2#v} hex='^[0-9a-f]{7,40}$'
    [ "$a" = "$b" ] && return 0
    [[ $a =~ $hex && $b =~ $hex ]] && [[ $a == "$b"* || $b == "$a"* ]]
}
# shown TAG: how a version is shown: a whole commit by its first 7 characters, as git does.
shown() { if [[ $1 =~ ^[0-9a-f]{40}$ ]]; then echo "${1:0:7}"; else echo "$1"; fi; }
# installed_version: what its version: command prints (a leading v dropped), if that's a version
# (starts with a digit) or a commit; nothing otherwise ("unknown": built without its tags).
installed_version() {
    local cmd cur
    cmd=$(field version)
    [ -n "$cmd" ] || return 0
    cur=$(PATH=$LINK_PATH bash -c "$cmd" 2>/dev/null | head -1) || cur=
    cur=${cur#v}
    if [[ $cur =~ ^[0-9] || $cur =~ ^[0-9a-f]{7,40}$ ]]; then echo "$cur"; fi
}
# how_installed TESTED: the status line's words for which version is there.
how_installed() {
    local tested cur choice=""
    [ -n "$1" ] || { t "installed by its own installer (it updates its own way)"; return; }
    tested=$(shown "$1")
    cur=$(installed_version)
    [ ! -f "$CHOICE" ] || choice=$(head -1 "$CHOICE")
    if [ -n "$cur" ] && same_version "$cur" "$tested"; then
        t "installed by its own installer: the version Frame Tweaks tested (%s)" "$tested"
    elif [ -n "$cur" ]; then
        t "installed by its own installer: %s, not the version Frame Tweaks tested (%s)" "$cur" "$tested"
    elif [ "$choice" = newest ]; then
        t "installed by its own installer: its newest version, not yet tested by Frame Tweaks"
    elif [ "${choice%% *}" = tested ]; then
        t "installed by its own installer: the version Frame Tweaks tested (%s)" "$(shown "${choice#tested }")"
    else
        t "installed by its own installer (it updates its own way)"
    fi
}

# restart_pending: restart: steamvr and installed after SteamVR started (its install record, or a
# newer change to an installed path), unless what was installed is the version SteamVR had loaded
# already (LOADED). True only while SteamVR runs.
restart_pending() {
    local path
    if [ -f "$LOADED" ] && same_version "$(head -1 "$LOADED")" "$(installed_version)"; then return 1; fi
    vr_started_before "$HOME/.local/state/frame-tweaks/installed/$id" && return 0
    while IFS= read -r path; do
        path=${path/#\~/$HOME}
        [ -e "$path" ] && vr_started_before "$path" && return 0
    done < <(field installed)
    return 1
}

case $action in
    install)
        cmd=$(field install) tested=$(field tested) choice=""
        case ${FT_LINK_CHOICE:-} in "$id:"*) choice=${FT_LINK_CHOICE#"$id:"} ;; esac
        # (asked for nothing: what was installed before stays the choice, ↻ included; else the tested one)
        if [ -z "$choice" ] && [ -f "$CHOICE" ] && [ "$(head -1 "$CHOICE")" = newest ]; then choice=newest; fi
        version=""
        if [ -z "$tested" ]; then
            [ "${choice:-newest}" = newest ] || die "$(t "%s has no tested version here: it installs its newest" "$name")"
            say "$(t "Installing %s with its own installer (from the project, not checked by Frame Tweaks):" "$name")"
        elif [ "$choice" = newest ]; then
            say "$(t "Installing the newest %s, not yet tested by Frame Tweaks, with its own installer (from the project):" "$name")"
        else
            choice=tested version=$tested
            say "$(t "Installing %s %s, the version Frame Tweaks tested, with its own installer (from the project):" "$name" "$(shown "$tested")")"
        fi
        echo "  $cmd"
        # (loaded: SteamVR has this version loaded already, or loads it when it starts: installed,
        # nothing waiting for a restart, and the same version installed after)
        loaded=""
        if [ "$(field restart)" = steamvr ] && [ ! -e "$UNLOADED" ] && ! restart_pending; then
            loaded=$(installed_version)
        fi
        # (exported to its command alone: the version to install, empty for the newest)
        FT_LINK_VERSION=$version PATH=$LINK_PATH bash -c "$cmd" || exit
        rm -f "$UNLOADED" "$LOADED"
        if [ -n "$loaded" ] && same_version "$loaded" "$(installed_version)"; then
            mkdir -p "${LOADED%/*}" && echo "$loaded" > "$LOADED"
        fi
        if [ -n "$tested" ]; then
            mkdir -p "${CHOICE%/*}"
            if [ "$choice" = newest ]; then echo newest; else echo "tested $tested"; fi > "$CHOICE"
        else
            rm -f "$CHOICE"
        fi ;;
    uninstall)
        cmd=$(field uninstall)
        [ -n "$cmd" ] || die "$(t "%s has no uninstall command here: see its README" "$name")"
        say "$(t "Uninstalling %s with its own uninstaller:" "$name")"
        echo "  $cmd"
        PATH=$LINK_PATH bash -c "$cmd" || exit
        rm -f "$LOADED"
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
        # project, often older than SteamVR.) Not after an install of the version SteamVR had
        # loaded already (restart_pending, LOADED).
        restart=$(field restart)
        while IFS= read -r path; do
            path=${path/#\~/$HOME}
            [ -e "$path" ] || continue
            [ "$restart" = steamvr ] && restart_pending &&
                status_restart "$(t 'installed; restart SteamVR to load it')"
            status_ok "$(how_installed "$(field tested)")"
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
        # With a tested version: "<installed> <newest> <tested>", newest "-" when it couldn't be
        # looked up (the window still offers the way back to the tested one). A commit as the
        # tested version (a project without releases) makes the newest its default branch's head.
        repo=$(field github) tested=$(field tested)
        [ -n "$(field version)" ] && [ -n "$repo" ] || exit 1
        cur=$(installed_version)
        [ -n "$cur" ] || exit 1
        if [[ $tested =~ ^[0-9a-f]{7,40}$ ]]; then
            latest=$(GIT_TERMINAL_PROMPT=0 timeout 8 git ls-remote "https://github.com/$repo" HEAD 2>/dev/null |
                     cut -c1-7 | head -1) || latest=
        else
            latest=$(curl -fsI --max-time 8 "https://github.com/$repo/releases/latest" |
                     sed -n 's|^[Ll]ocation: .*/releases/tag/v\{0,1\}\([^[:space:]]*\).*|\1|p' | head -1) || latest=
        fi
        if [ -n "$tested" ]; then echo "$cur ${latest:--} $(shown "$tested")"
        elif [ -n "$latest" ]; then echo "$cur $latest"
        else exit 1; fi ;;
    *) die "lib/link.sh install|uninstall|status|run|update-check ID" ;;
esac
