#!/bin/bash
# steam-frame-tweaks: install, check, update and remove desktop-mode tweaks for the Steam Frame.
#
#   ./install.sh                     graphical checklist (in desktop mode), else this help
#   ./install.sh install ID... | all install components (dependencies are added automatically)
#   ./install.sh uninstall ID...     remove components
#   ./install.sh status [ID...]      health check of installed components (changes nothing)
#   ./install.sh update [--to vX.Y.Z] move to the newest (or given) release, re-run what's installed
#   ./install.sh hold|unhold ID...   keep a tweak as it is during updates (or stop doing so)
#   ./install.sh debug-info          write a redacted report for bug reports
#   ./install.sh check-system        are the SteamOS/SteamVR parts the tweaks rely on still there?
#   ./install.sh list                components and what they do
#   ./install.sh menu                (re)create the "Frame Tweaks" app-menu entry
#   ./install.sh ID...               same as "install ID..."
#
# Everything installs into your home directory; nothing touches SteamOS's read-only system
# partition, so OS updates don't undo it. Every installer is safe to re-run.
set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")" || exit 1
VERSION=$(cat VERSION 2>/dev/null || echo dev)
# shellcheck source=lib/common.sh
source lib/common.sh 2>/dev/null
set +e     # common.sh turns on -e for tweak scripts; this script checks results itself
STATE="$HOME/.local/state/frame-tweaks"
LOGS="$STATE/logs"

# One install/uninstall/update at a time (installer window and terminal alike). The lock is on
# fd 8; tweak scripts run with it closed, so a background process they start can't keep it.
take_lock() {
    mkdir -p "$STATE"
    exec 8>"$STATE/install.lock"
    flock -n 8 || { echo "Another Frame Tweaks install, update or removal is running; try again when it's done." >&2; exit 1; }
}

# Every changing run is logged (the last 5 are kept), for ./install.sh debug-info.
start_log() {
    mkdir -p "$LOGS"
    local log; log="$LOGS/$(date +%Y%m%d-%H%M%S)-$$-$1.log"
    { echo "# frame-tweaks $VERSION: $*"; date; } > "$log"
    exec > >(tee -a "$log") 2>&1
    find "$LOGS" -name '*.log' -printf '%T@ %p\n' | sort -n | head -n -5 | cut -d' ' -f2- | xargs -r rm -f
}

# components.tsv: id, title, category, depends (space-separated), description, source,
# author, why, flags (tab-separated; see the header line)
declare -A TITLE DEPS DESC
IDS=()
# (Tabs become \x1f first: read merges empty fields between whitespace separators like tab.)
while IFS=$'\x1f' read -r id title _category deps desc _rest; do
    [[ -z $id || $id == \#* ]] && continue
    IDS+=("$id"); TITLE[$id]=$title; DEPS[$id]=$deps; DESC[$id]=$desc
done < <(tr '\t' '\037' < components.tsv)

# The installer's own app-menu entry (desktop menu and Steam's VR "+" menu).
ensure_menu_entry() {
    local apps="$HOME/.local/share/applications" icons="$HOME/.local/share/icons/hicolor" n
    local id=io.github.AstronautCheetah.FrameTweaks
    mkdir -p "$apps" "$HOME/.local/share/metainfo"
    for n in 64 128 256; do
        mkdir -p "$icons/${n}x$n/apps"
        if [[ $n == 256 ]]; then install -m644 icons/frame-tweaks.png "$icons/256x256/apps/$id.png"
        else install -m644 "icons/frame-tweaks-$n.png" "$icons/${n}x$n/apps/$id.png"; fi
    done
    install -m644 icons/frame-tweaks.png "$icons/256x256/apps/frame-tweaks.png"   # the window's own icon
    sed "s|@REPO@|$PWD|g" "share/applications/$id.desktop" > "$apps/$id.desktop"
    install -m644 "share/metainfo/$id.metainfo.xml" "$HOME/.local/share/metainfo/"
    rm -f "$apps/steam-frame-tweaks.desktop"          # its old name
    update-desktop-database -q "$apps" 2>/dev/null || true
    touch "$apps" "$icons"     # Steam's "+" menu rescans on these
}

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
is_component() { [[ -n ${TITLE[$1]:-} ]]; }

# status <id>: prints the component's one-line status; returns 0 ok, 1 missing, 2 warning
status_of() { "./$1/status.sh" 2>/dev/null; }

# with_deps <id>...: the ids plus their dependencies, dependencies first, no duplicates
with_deps() {
    local -A seen=(); local out=()
    visit() {
        local id=$1 d
        [[ -n ${seen[$id]:-} ]] && return
        seen[$id]=1
        for d in ${DEPS[$id]}; do visit "$d"; done
        out+=("$id")
    }
    local id
    for id in "$@"; do visit "$id"; done
    printf '%s\n' "${out[@]}"
}

check_ids() {
    local id
    for id in "$@"; do is_component "$id" || { echo "unknown component: $id (see ./install.sh list)" >&2; exit 1; }; done
}

cmd_list() {
    bold "steam-frame-tweaks $VERSION"
    local id
    for id in "${IDS[@]}"; do printf '  %-15s %s\n' "$id" "${DESC[$id]}"; done
}

cmd_status() {
    local ids=("$@") id rc line worst=0
    [[ ${#ids[@]} -eq 0 ]] && ids=("${IDS[@]}")
    check_ids "${ids[@]}"
    for id in "${ids[@]}"; do
        line=$(status_of "$id"); rc=$?
        case $rc in
            0) printf '  \033[32m✔\033[0m %-15s %s\n' "$id" "${line#ok       }" ;;
            1) printf '  \033[2m·\033[0m %-15s \033[2mnot installed\033[0m\n' "$id" ;;
            *) printf '  \033[33m!\033[0m %-15s %s\n' "$id" "${line#warning  }"; worst=2 ;;
        esac
    done
    return $worst
}

cmd_install() {
    [[ $# -eq 0 ]] && { echo "install what? (./install.sh list)" >&2; exit 1; }
    ensure_menu_entry
    [[ $1 == all ]] && set -- "${IDS[@]}"
    check_ids "$@"
    local id failed=()
    for id in $(with_deps "$@"); do
        bold "── $id: ${TITLE[$id]}"
        if held "$id" && [[ -n ${FRAME_TWEAKS_UPDATING:-} ]]; then
            echo "held: left as it is (./install.sh unhold $id)"; echo; continue
        fi
        stop_processes "$id"            # a reinstall must not leave the old copy running
        if ! "./$id/install.sh" 8>&-; then failed+=("$id"); echo "!! $id failed" >&2
        else record_version "$id"; fi
        echo
    done
    [[ ${#failed[@]} -eq 0 ]] || { echo "Failed: ${failed[*]}" >&2; return 1; }
    bold "Done."; cmd_status "$@"
}

cmd_uninstall() {
    [[ $# -eq 0 ]] && { echo "uninstall what?" >&2; exit 1; }
    check_ids "$@"
    local id other d
    for id in "$@"; do
        # Refuse to remove something an installed component depends on.
        for other in "${IDS[@]}"; do
            for d in ${DEPS[$other]}; do
                if [[ $d == "$id" && " $* " != *" $other "* ]] && status_of "$other" >/dev/null; then
                    echo "$id is needed by $other: uninstall $other too, or keep $id" >&2; exit 1
                fi
            done
        done
    done
    for id in "$@"; do bold "── removing $id"; stop_processes "$id"; "./$id/uninstall.sh" 8>&-; forget_version "$id"; echo; done
}

cmd_update() {
    local want=""
    [[ ${1:-} == --to ]] && { want=${2:?"--to needs a release, e.g. v0.3.1"}; [[ $want == v* ]] || want="v$want"; }
    if [[ -d .git ]]; then
        if git symbolic-ref -q HEAD >/dev/null; then       # a developer checkout on a branch
            bold "Updating the checkout"; git pull --ff-only || { echo "git pull failed; not reinstalling" >&2; exit 1; }
        else                                                # a release (tag): move to the newest
            git fetch --quiet --tags origin || { echo "couldn't reach GitHub; not updating" >&2; exit 1; }
            local tag; tag=${want:-$(git tag -l 'v*' | newest_tag)}
            [ -n "$tag" ] || { echo "no release found" >&2; exit 1; }
            git rev-parse -q --verify "refs/tags/$tag" >/dev/null || { echo "no release $tag" >&2; exit 1; }
            bold "Updating to $tag ($(release_channel) channel)"; git -c advice.detachedHead=false checkout --quiet "$tag"
        fi
        FRAME_TWEAKS_UPDATING=1 exec ./install.sh _reinstall   # re-exec so the new version of this script runs
    fi
    cmd_reinstall
}

cmd_reinstall() {
    local id installed=()
    for id in "${IDS[@]}"; do status_of "$id" >/dev/null; [[ $? -ne 1 ]] && installed+=("$id"); done
    [[ ${#installed[@]} -eq 0 ]] && { echo "Nothing installed yet."; return; }
    run_migrations "${installed[@]}"
    cmd_install "${installed[@]}"
    echo; bold "Checking the SteamOS/SteamVR parts the tweaks rely on"; cmd_check_system || true
}

cmd_gui() {
    ensure_menu_entry
    # The full window (hide rows, live status) needs PyQt6, shared with Arrow Pad and the
    # NordVPN tray. Offer to set it up; otherwise fall back to kdialog's plain checklist.
    local qt="$HOME/.local/share/arrowpad/venv"
    if ! "$qt/bin/python" -c 'import PyQt6' 2>/dev/null &&
       kdialog --title "Frame Tweaks" --yesno "Set up the full installer window? It needs PyQt6 (about 280 MB, shared with Arrow Pad and the NordVPN tray).\n\nNo = use the simple checklist."; then
        python3 -m venv "$qt" && "$qt/bin/pip" install -q -c lib/python-constraints.txt PyQt6 ||
            kdialog --sorry "Couldn't install PyQt6; using the simple checklist."
    fi
    if "$qt/bin/python" -c 'import PyQt6' 2>/dev/null; then
        # A copy of the interpreter under its own name, so SteamVR gives the window its own
        # controller bindings (it keys them by program name; Arrow Pad also runs on Python).
        local sft="$qt/bin/sft-python"
        cp -u "$(readlink -f "$qt/bin/python")" "$sft" 2>/dev/null || true
        if "$sft" -c 'import PyQt6' 2>/dev/null; then exec "$sft" gui/frame-tweaks-gui.py; fi
        exec "$qt/bin/python" gui/frame-tweaks-gui.py
    fi
    cmd_kdialog_gui
}

cmd_kdialog_gui() {
    local args=() id st
    for id in "${IDS[@]}"; do
        status_of "$id" >/dev/null; st=$?
        args+=("$id" "${TITLE[$id]}: ${DESC[$id]}" "$([[ $st -ne 1 ]] && echo on || echo off)")
    done
    local picked
    picked=$(kdialog --title "Frame Tweaks $VERSION" --geometry 900x560 --separate-output \
        --checklist "Tick what you want installed. Unticking an installed tweak removes it." "${args[@]}") || exit 0
    local add=() del=()
    for id in "${IDS[@]}"; do
        status_of "$id" >/dev/null; st=$?
        if grep -qx "$id" <<<"$picked"; then [[ $st -ne 0 ]] && add+=("$id")
        else [[ $st -ne 1 ]] && del+=("$id"); fi
    done
    [[ ${#add[@]} -eq 0 && ${#del[@]} -eq 0 ]] && { kdialog --msgbox "Nothing to change."; exit 0; }
    # Removals get their own warning, and an empty selection never removes anything:
    # a dialog that fails or is dismissed oddly must not wipe the user's setup.
    if [[ ${#del[@]} -gt 0 ]]; then
        if [[ -z $picked ]]; then
            kdialog --sorry "Nothing was selected, so nothing will be removed. To remove everything, use: ./install.sh uninstall ${del[*]}"
            exit 0
        fi
        kdialog --title "Remove tweaks?" --warningcontinuecancel \
            "These installed tweaks were unticked and will be REMOVED:\n\n  ${del[*]}\n\nContinue?" || del=()
    fi
    [[ ${#add[@]} -eq 0 && ${#del[@]} -eq 0 ]] && exit 0
    if [[ -n ${FRAME_TWEAKS_DRY_RUN:-} ]]; then   # for tests: show the plan, change nothing
        echo "would remove: ${del[*]:-none}"; echo "would install: ${add[*]:-none}"; exit 0
    fi
    local cmd="cd '$PWD'"
    [[ ${#del[@]} -gt 0 ]] && cmd+=" && ./install.sh uninstall ${del[*]}"
    [[ ${#add[@]} -gt 0 ]] && cmd+=" && ./install.sh install ${add[*]}"
    cmd+="; echo; read -rp 'Press Enter to close…'"
    exec konsole --separate -e bash -c "$cmd"
}

usage() { sed -n '2,18s/^# \{0,1\}//p' "$0"; }

# ---- stopping a tweak's programs ------------------------------------------------------------
# <id>/processes lists the programs a tweak runs (pgrep -f patterns, ~ = $HOME). They're
# stopped before the tweak is uninstalled or reinstalled, so an old copy can't keep running.
stop_processes() {
    local id=$1 pat pids n=0
    [[ -f ./$id/processes ]] || return 0
    while IFS= read -r pat; do
        [[ -z $pat || $pat == \#* ]] && continue
        pat=${pat//\~/$HOME}
        pids=$(pgrep -f -- "$pat" | grep -vx "$$" || true)
        [[ -n $pids ]] || continue
        # shellcheck disable=SC2086
        kill $pids 2>/dev/null || true
        for _ in 1 2 3 4 5 6; do pgrep -f -- "$pat" >/dev/null || break; sleep 0.5; done
        pids=$(pgrep -f -- "$pat" || true)
        # shellcheck disable=SC2086
        [[ -z $pids ]] || kill -9 $pids 2>/dev/null || true      # didn't stop within 3 s
        n=$((n + 1))
    done < "./$id/processes"
    if [[ $n -gt 0 ]]; then
        echo "stopped $id's running programs"
        # A stopped pad can't release keys it held down: make sure no modifier stays pressed.
        [[ $id == arrowpad && -x $BIN/ydotool ]] &&
            clear_stuck_modifiers
    fi
}

# ---- per-tweak versions (for migrations) and holds -------------------------------------------
# installed/<id> records the Frame Tweaks version that last installed a tweak. A tweak's
# optional migrate.sh runs before its install.sh when that recorded version is older, with the
# old version as $1 (e.g. to move a setting to a new place).
record_version() { mkdir -p "$STATE/installed"; echo "$VERSION" > "$STATE/installed/$1"; }
forget_version() { rm -f "$STATE/installed/$1"; }
held() { [[ -f "$STATE/held/$1" ]]; }
run_migrations() {
    local id old
    for id in "$@"; do
        [[ -x ./$id/migrate.sh && -f $STATE/installed/$id ]] || continue
        held "$id" && [[ -n ${FRAME_TWEAKS_UPDATING:-} ]] && continue
        old=$(cat "$STATE/installed/$id")
        [[ $old != "$VERSION" ]] || continue
        bold "── migrating $id from $old"
        "./$id/migrate.sh" "$old" 8>&- || echo "!! $id migration failed" >&2
    done
}
cmd_hold() {
    local mode=$1; shift
    [[ $# -gt 0 ]] || { echo "$mode what? (./install.sh list)" >&2; exit 1; }
    check_ids "$@"; mkdir -p "$STATE/held"
    local id
    for id in "$@"; do
        if [[ $mode == hold ]]; then touch "$STATE/held/$id"; echo "$id: held (updates leave it as it is)"
        else rm -f "$STATE/held/$id"; echo "$id: updated normally again"; fi
    done
}

# ---- diagnostics ----------------------------------------------------------------------------
cmd_debug_info() {
    local out; out="$HOME/frame-tweaks-debug-$(date +%Y%m%d-%H%M%S).txt"
    {
        echo "# Frame Tweaks debug info (user names, home path, host name, IP and e-mail addresses removed)"
        echo "frame-tweaks: $VERSION ($(git describe --tags --always 2>/dev/null || echo no git)); channel: $(release_channel)"
        grep -E '^(VERSION_ID|BUILD_ID)=' /etc/os-release | tr '\n' ' '; echo
        echo "steamvr: $(tr -d '\r' < /opt/steamvr/bin/version.txt 2>/dev/null || echo unknown); kernel: $(uname -r) $(uname -m)"
        echo; echo "## status"; cmd_status 2>&1 | sed 's/\x1b\[[0-9;]*m//g'
        echo; echo "## held tweaks"; ls "$STATE/held" 2>/dev/null || true
        echo; echo "## check-system"; cmd_check_system 2>&1
        echo; echo "## failed user services"; sysctl_user --failed --no-legend --plain 2>&1 | head -20
        local log
        for log in $(ls -t "$LOGS"/*.log 2>/dev/null | head -2); do
            echo; echo "## log $(basename "$log")"; sed 's/\x1b\[[0-9;]*m//g' "$log" | tail -150
        done
    } | sed -E -e "s|$HOME|~|g" -e "s/\b$USER\b/<user>/g" -E -e "s/(^|[[:space:]@/'\"(])$(hostname 2>/dev/null || echo nohost)([[:space:]:.,)'\"]|$)/\1<host>\2/g" \
             -e 's/\b([0-9]{1,3}\.){3}[0-9]{1,3}\b/<ip>/g' -e 's/[[:alnum:]._%+-]+@[[:alnum:].-]+\.[[:alpha:]]{2,}/<email>/g' \
        > "$out"
    echo "Wrote $out"
    echo "Read it before sharing; attach it to a bug report: https://github.com/AstronautCheetah/frame-tweaks/issues"
}

# check-system: run each installed tweak's optional check-system.sh, which tests whether the
# SteamOS / SteamVR internals it relies on are still there (useful after a SteamOS update).
cmd_check_system() {
    local id code out bad=0
    for id in "${IDS[@]}"; do
        [[ -x ./$id/check-system.sh ]] || continue
        status_of "$id" >/dev/null; [[ $? -eq 1 ]] && continue
        out=$("./$id/check-system.sh" 2>&1); code=$?
        if [[ $code -eq 0 ]]; then printf '  \e[32m✔\e[0m %-15s %s\n' "$id" "$out"
        else printf '  \e[33m!\e[0m %-15s %s\n' "$id" "$out"; bad=1; fi
    done
    return $bad
}

case ${1:-} in
    "")          if [[ ! -t 0 || -n ${FRAME_TWEAKS_GUI:-} ]] && command -v kdialog >/dev/null && [[ -n ${WAYLAND_DISPLAY:-${DISPLAY:-}} ]]; then cmd_gui
                 else usage; echo; cmd_status; fi ;;
    gui)         cmd_gui ;;
    install)     shift; take_lock; start_log install "$@"; run_migrations "$@"; cmd_install "$@" ;;
    uninstall|remove) shift; take_lock; start_log uninstall "$@"; cmd_uninstall "$@" ;;
    status|check) shift; cmd_status "$@" ;;
    update)      shift; take_lock; start_log update "$@"; cmd_update "$@" ;;
    _reinstall)  take_lock; start_log reinstall; cmd_reinstall ;;
    hold|unhold) cmd_hold "$@" ;;
    debug-info)  cmd_debug_info ;;
    check-system) cmd_check_system ;;
    _deps)       shift; [[ ${1:-} == all ]] && set -- "${IDS[@]}"; check_ids "$@"; with_deps "$@" | tr "\n" " "; echo ;;
    list)        cmd_list ;;
    menu)        ensure_menu_entry; echo "Added 'Frame Tweaks' to the app menu." ;;
    -h|--help|help) usage ;;
    --version|version) echo "$VERSION" ;;
    *)           take_lock; start_log install "$@"; run_migrations "$@"; cmd_install "$@" ;;
esac
