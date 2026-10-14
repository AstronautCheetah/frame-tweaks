#!/bin/bash
# frame-tweaks: install, check, update and remove desktop-mode tweaks for the Steam Frame.
#
#   ./install.sh                     graphical checklist (in desktop mode), else this help
#   ./install.sh install ID... | all install components (dependencies are added automatically)
#   ./install.sh uninstall ID... | all  remove components (settings kept)
#   ./install.sh reinstall ID...     remove and install again (settings kept; a clean copy)
#   ./install.sh status [ID...]      health check of installed components (changes nothing)
#   ./install.sh update [--to vX.Y.Z] move to the newest (or given) release, re-run what's installed
#   ./install.sh hold|unhold ID...   keep a tweak as it is during updates (or stop doing so)
#   ./install.sh debug-info          write a redacted report for bug reports
#   ./install.sh check-system        are the SteamOS/SteamVR parts the tweaks rely on still there?
#   ./install.sh list                components and what they do
#   ./install.sh info ID             one component's details (as in the installer window)
#   ./install.sh run ID              its Run / Open button (e.g. open Arrow Pad)
#   ./install.sh settings ID [KEY=VALUE... | --reset]   show or change its settings (scroll-strips, adb-scrcpy)
#   ./install.sh mods [trust|untrust|on|off PACK | check FOLDER]   packs of tweaks (docs/mods.md)
#   ./install.sh hide|unhide ID...   hide a row in the installer window (or show it again)
#   ./install.sh hide-group|unhide-group NAME   the same for a whole group, e.g. "VR environment"
#   ./install.sh wallet lock|unlock|status      the shared KDE wallet (wallet-unlock)
#   ./install.sh wallet-apps [ARGS]  apps that use the wallet (wallet-launcher; --help for its options)
#   ./install.sh timers [ARGS]       close-after timers for apps (app-timers; --help for its options)
#   ./install.sh menu [--remove]     (re)create the "Frame Tweaks" app-menu entry (or remove it)
#   ./install.sh ID...               same as "install ID..."
#
# Everything installs into your home directory; nothing touches SteamOS's read-only system
# partition, so OS updates don't undo it. Every installer is safe to re-run.
set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")" || exit 1
VERSION=$(cat VERSION 2>/dev/null || echo dev)
# shellcheck source=lib/common.sh
source lib/common.sh
FT_BUILD=$(ft_version)        # what to show: VERSION plus the commit, between releases
set +e     # common.sh turns on -e for tweak scripts; this script checks results itself
STATE="$HOME/.local/state/frame-tweaks"
LOGS="$STATE/logs"
migrate_legacy_dirs
# The tweaks moved into packs/official/ (0.6): an update leaves their old folders behind
# holding only Python's __pycache__ (git doesn't track it).
# The same for packs/official, which became packs/original, packs/integrations and packs/third-party (after 0.6.0).
shopt -s nullglob
for d in */__pycache__ packs/official/*/__pycache__; do
    d=${d%/__pycache__}
    others=("$d"/* "$d"/.[!.]*)
    [[ -d $d && ${#others[@]} -eq 1 ]] && rm -rf -- "$d"     # (nothing but __pycache__)
done
shopt -u nullglob
rmdir packs/official 2>/dev/null     # (only if that left it empty)

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
    { echo "# frame-tweaks $FT_BUILD: $*"; date; } > "$log"
    # (tee without the lock's fd 8: holding it, tee kept the lock after `update` re-runs this
    # script for its second stage, which then found "another install running" and stopped.)
    exec > >(tee -a "$log" 8>&-) 2>&1
    # (Only the installer's own logs, named by date: tweaks keep theirs here too, e.g. a tweak's own *.log.)
    find "$LOGS" -name '[0-9]*-*.log' -printf '%T@ %p\n' | sort -n | head -n -5 | cut -d' ' -f2- | xargs -r rm -f
}

# The tweaks, from the packs (lib/sft.py registry: the official packs and the user's trusted
# packs, each tweak described by its README.md front matter; see docs/mods.md).
declare -A TITLE DEPS DESC DIR EXPERIMENTAL
IDS=()
while IFS=$'\x1f' read -r id title deps desc dir exp; do
    IDS+=("$id"); TITLE[$id]=$title; DEPS[$id]=$deps; DESC[$id]=$desc; DIR[$id]=$dir; EXPERIMENTAL[$id]=$exp
done < <(python3 lib/sft.py registry)
[[ ${#IDS[@]} -gt 0 ]] || { echo "$(t 'No tweaks found (python3 lib/sft.py mods says why)')" >&2; exit 1; }
# Where each tweak is, for scripts that call another tweak's (lib/common.sh tweak_dir).
FRAME_TWEAKS_DIRS=$(for id in "${IDS[@]}"; do echo "$id=${DIR[$id]}"; done)
export FRAME_TWEAKS_DIRS

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
    sed "s|@REPO@|$PWD|g" "share/applications/$id.desktop" | python3 lib/i18n.py desktop > "$apps/$id.desktop"
    install -m644 "share/metainfo/$id.metainfo.xml" "$HOME/.local/share/metainfo/"
    rm -f "$apps/steam-frame-tweaks.desktop"          # its old name
    update-desktop-database -q "$apps" 2>/dev/null || true
    touch "$apps" "$icons"     # Steam's "+" menu rescans on these
}
remove_menu_entry() {
    local apps="$HOME/.local/share/applications" icons="$HOME/.local/share/icons/hicolor" n
    local id=io.github.AstronautCheetah.FrameTweaks
    rm -f "$apps/$id.desktop" "$HOME/.local/share/metainfo/$id.metainfo.xml" "$icons/256x256/apps/frame-tweaks.png"
    for n in 64 128 256; do rm -f "$icons/${n}x$n/apps/$id.png"; done
    update-desktop-database -q "$apps" 2>/dev/null || true
    touch "$apps" "$icons" 2>/dev/null || true
}

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
is_component() { [[ -n ${TITLE[$1]:-} ]]; }

# status <id>: prints the component's one-line status; returns 0 ok, 1 missing, 2 warning
status_of() { bash "${DIR[$1]}/status.sh" 2>/dev/null; }

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
    for id in "$@"; do
        is_component "$id" ||
            { echo "unknown component: $id (see ./install.sh list; a pack that isn't trusted: ./install.sh mods)" >&2; exit 1; }
    done
}

cmd_list() {
    bold "frame-tweaks $FT_BUILD"
    local id
    for id in "${IDS[@]}"; do
        printf '  %-15s %s%s\n' "$id" "${DESC[$id]}" "${EXPERIMENTAL[$id]:+ $(t '(experimental)')}"
    done
    [[ " ${EXPERIMENTAL[*]} " == *1* ]] && echo "$(t "(experimental: relies on SteamVR's internals; see ./install.sh info ID)")"
    return 0
}

cmd_status() {
    local ids=("$@") id rc line worst=0
    [[ ${#ids[@]} -eq 0 ]] && ids=("${IDS[@]}")
    check_ids "${ids[@]}"
    for id in "${ids[@]}"; do
        line=$(status_of "$id"); rc=$?
        case $rc in
            0) printf '  \033[32m✔\033[0m %-15s %s\n' "$id" "${line#ok       }" ;;
            1) printf '  \033[2m·\033[0m %-15s \033[2m%s\033[0m\n' "$id" "$(t 'not installed')" ;;
            *) printf '  \033[33m!\033[0m %-15s %s\n' "$id" "${line#warning  }"; worst=2 ;;
        esac
    done
    return $worst
}

cmd_install() {
    [[ $# -eq 0 ]] && { echo "$(t 'install what? (./install.sh list)')" >&2; exit 1; }
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
        if ! bash "${DIR[$id]}/install.sh" 8>&-; then failed+=("$id"); echo "!! $(t '%s failed' "$id")" >&2
        else record_version "$id"; fi
        echo
    done
    [[ ${#failed[@]} -eq 0 ]] || { echo "$(t 'Failed: %s' "${failed[*]}")" >&2; return 1; }
    bold "$(t 'Done.')"; cmd_status "$@"
}

cmd_uninstall() {
    [[ $# -eq 0 ]] && { echo "$(t 'uninstall what?')" >&2; exit 1; }
    if [[ $1 == all ]]; then           # everything installed, each tweak before what it depends on
        local i all=() order
        mapfile -t order < <(with_deps "${IDS[@]}")
        for (( i=${#order[@]}-1; i>=0; i-- )); do
            status_of "${order[i]}" >/dev/null; [[ $? -ne 1 ]] && all+=("${order[i]}")
        done
        [[ ${#all[@]} -eq 0 ]] && { t 'Nothing installed.'; echo; return; }
        set -- "${all[@]}"
    fi
    check_ids "$@"
    local id other d
    for id in "$@"; do
        # Refuse to remove something an installed component depends on.
        for other in "${IDS[@]}"; do
            for d in ${DEPS[$other]}; do
                if [[ $d == "$id" && " $* " != *" $other "* ]] && status_of "$other" >/dev/null; then
                    echo "$(t '%s is needed by %s: uninstall %s too, or keep %s' "$id" "$other" "$other" "$id")" >&2; exit 1
                fi
            done
        done
    done
    for id in "$@"; do bold "── $(t 'removing %s' "$id")"; stop_processes "$id"; bash "${DIR[$id]}/uninstall.sh" 8>&-; forget_version "$id"; echo; done
}

# Remove, then install again. Unlike uninstall, a tweak others depend on may be removed here:
# it's back a moment later.
cmd_reinstall_ids() {
    [[ $# -eq 0 ]] && { echo "$(t 'reinstall what?')" >&2; exit 1; }
    check_ids "$@"
    local id
    # (FRAME_TWEAKS_REINSTALL: an uninstall that keeps what other tweaks put in its care, e.g. the
    # dashboard patches of the tweaks that use the VR environment helper.)
    for id in "$@"; do bold "── $(t 'removing %s' "$id")"; stop_processes "$id"; FRAME_TWEAKS_REINSTALL=1 bash "${DIR[$id]}/uninstall.sh" 8>&-; forget_version "$id"; echo; done
    cmd_install "$@"
}

cmd_update() {
    local want=""
    [[ ${1:-} == --to ]] && { want=${2:?"$(t '--to needs a release, e.g. v0.3.1')"}; [[ $want == v* ]] || want="v$want"; }
    if [[ -d .git ]]; then
        if git symbolic-ref -q HEAD >/dev/null; then       # a developer checkout on a branch
            bold "$(t 'Updating the checkout')"
            if ! git pull --ff-only; then
                git fetch --quiet origin 2>/dev/null
                if ! git merge-base --is-ancestor HEAD "@{upstream}" 2>/dev/null; then
                    echo "$(t "This checkout and GitHub's main have gone separate ways. Without local work to
keep: git reset --hard @{upstream}")" >&2
                fi
                echo "$(t 'git pull failed; not reinstalling')" >&2; exit 1
            fi
        else                                                # a release (tag): move to the newest
            # (--force: GitHub's tags win over local ones with the same name.)
            git fetch --quiet --force --tags origin || { echo "$(t "couldn't reach GitHub; not updating")" >&2; exit 1; }
            local tag; tag=${want:-$(git tag -l 'v*' | newest_tag)}
            [ -n "$tag" ] || { echo "$(t 'no release found')" >&2; exit 1; }
            git rev-parse -q --verify "refs/tags/$tag" >/dev/null || { echo "$(t 'no release %s' "$tag")" >&2; exit 1; }
            verify_release "$PWD" "$tag" || exit 1
            bold "$(t 'Updating to %s (%s channel)' "$tag" "$(release_channel)")"; git -c advice.detachedHead=false checkout --quiet "$tag"
        fi
        FRAME_TWEAKS_UPDATING=1 exec ./install.sh _reinstall   # re-exec so the new version of this script runs
    fi
    cmd_reinstall
}

cmd_reinstall() {
    local id installed=()
    for id in "${IDS[@]}"; do status_of "$id" >/dev/null; [[ $? -ne 1 ]] && installed+=("$id"); done
    [[ ${#installed[@]} -eq 0 ]] && { t 'Nothing installed yet.'; echo; return; }
    run_migrations "${installed[@]}"
    cmd_install "${installed[@]}"
    echo; bold "$(t 'Checking the SteamOS/SteamVR parts the tweaks rely on')"; cmd_check_system || true
}

cmd_gui() {
    ensure_menu_entry
    # The full window (hide rows, live status) needs PyQt6, shared with Arrow Pad and the
    # NordVPN tray. Offer to set it up; otherwise fall back to kdialog's plain checklist.
    local qt="$HOME/.local/share/arrowpad/venv"
    if ! "$qt/bin/python" -c 'import PyQt6' 2>/dev/null &&
       kdialog --title "Frame Tweaks" --yesno "$(t 'Set up the full installer window? It needs PyQt6 (about 280 MB, shared with Arrow Pad and the NordVPN tray).\n\nNo = use the simple checklist.')"; then
        python3 -m venv "$qt" && pip_pinned "$qt" PyQt6 ||
            kdialog --sorry "$(t "Couldn't install PyQt6; using the simple checklist.")"
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
    picked=$(kdialog --title "Frame Tweaks $FT_BUILD" --geometry 900x560 --separate-output \
        --checklist "$(t 'Tick what you want installed. Unticking an installed tweak removes it.')" "${args[@]}") || exit 0
    local add=() del=()
    for id in "${IDS[@]}"; do
        status_of "$id" >/dev/null; st=$?
        if grep -qx "$id" <<<"$picked"; then [[ $st -ne 0 ]] && add+=("$id")
        else [[ $st -ne 1 ]] && del+=("$id"); fi
    done
    [[ ${#add[@]} -eq 0 && ${#del[@]} -eq 0 ]] && { kdialog --msgbox "$(t 'Nothing to change.')"; exit 0; }
    # Removals get their own warning, and an empty selection never removes anything:
    # a dialog that fails or is dismissed oddly must not wipe the user's setup.
    if [[ ${#del[@]} -gt 0 ]]; then
        if [[ -z $picked ]]; then
            kdialog --sorry "$(t 'Nothing was selected, so nothing will be removed. To remove everything, use: %s' "./install.sh uninstall ${del[*]}")"
            exit 0
        fi
        kdialog --title "$(t 'Remove tweaks?')" --warningcontinuecancel \
            "$(t 'These installed tweaks were unticked and will be REMOVED:\n\n  %s\n\nContinue?' "${del[*]}")" || del=()
    fi
    [[ ${#add[@]} -eq 0 && ${#del[@]} -eq 0 ]] && exit 0
    if [[ -n ${FRAME_TWEAKS_DRY_RUN:-} ]]; then   # for tests: show the plan, change nothing
        echo "would remove: ${del[*]:-none}"; echo "would install: ${add[*]:-none}"; exit 0
    fi
    local cmd="cd '$PWD'"
    [[ ${#del[@]} -gt 0 ]] && cmd+=" && ./install.sh uninstall ${del[*]}"
    [[ ${#add[@]} -gt 0 ]] && cmd+=" && ./install.sh install ${add[*]}"
    # (In VR a floating window has an X button below it: easier than a key without a keyboard.)
    local close; close=$(t 'Press Enter to close…')
    [[ ${DISPLAY:-} == :0 ]] && close=$(t 'Press Enter to close, or press the X button floating below to close.')
    cmd+="; echo; read -rp $(printf %q "$close")"
    exec konsole --separate -e bash -c "$cmd"
}

usage() { sed -n '2,/^#   \.\/install\.sh ID\.\.\./s/^# \{0,1\}//p' "$0"; }   # (the header, to the last command)

# ---- stopping a tweak's programs ------------------------------------------------------------
# A tweak's manifest lists the programs it runs (processes: pgrep -f patterns, ~ = $HOME).
# They're stopped before the tweak is uninstalled or reinstalled, so an old copy can't keep
# running; then its optional stopped.sh runs (e.g. Arrow Pad releasing keys it held down).
stop_processes() {
    local id=$1 pat pids n=0
    while IFS= read -r pat; do
        [[ -z $pat ]] && continue
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
    done < <(python3 lib/sft.py processes "$id")
    if [[ $n -gt 0 ]]; then
        echo "$(t "stopped %s's running programs" "$id")"
        [[ -f ${DIR[$id]}/stopped.sh ]] && bash "${DIR[$id]}/stopped.sh" 8>&-
    fi
    return 0
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
        is_component "$id" || continue           # (unknown ids are refused right after)
        [[ -f ${DIR[$id]}/migrate.sh && -f $STATE/installed/$id ]] || continue
        held "$id" && [[ -n ${FRAME_TWEAKS_UPDATING:-} ]] && continue
        old=$(cat "$STATE/installed/$id")
        # Only from an older release: going back to an older one doesn't run them backwards.
        [[ $old != "$VERSION" && $(printf '%s\n%s\n' "$old" "$VERSION" | sort -V | head -1) == "$old" ]] || continue
        bold "── migrating $id from $old"
        bash "${DIR[$id]}/migrate.sh" "$old" 8>&- || echo "!! $(t '%s migration failed' "$id")" >&2
    done
}
cmd_hold() {
    local mode=$1; shift
    [[ $# -gt 0 ]] || { echo "$(t '%s what? (./install.sh list)' "$mode")" >&2; exit 1; }
    check_ids "$@"; mkdir -p "$STATE/held"
    local id
    for id in "$@"; do
        if [[ $mode == hold ]]; then touch "$STATE/held/$id"; echo "$(t '%s: held (updates leave it as it is)' "$id")"
        else rm -f "$STATE/held/$id"; echo "$(t '%s: updated normally again' "$id")"; fi
    done
}

# ---- diagnostics ----------------------------------------------------------------------------
cmd_debug_info() {
    local out; out="$HOME/frame-tweaks-debug-$(date +%Y%m%d-%H%M%S).txt"
    # Your phone's name too (Android Mirror's PHONE_NAME), escaped for sed.
    local phone; phone=$(bash -c '. "$HOME/.config/frame-tweaks/phone.conf" 2>/dev/null; printf %s "${PHONE_NAME:-}"' |
                         sed 's/[][\.*^$/&|]/\\&/g')       # (read as phone does: it's shell-quoted)
    {
        echo "# Frame Tweaks debug info (user names, home path, host and phone names, IP, MAC and e-mail addresses removed)"
        echo "frame-tweaks: $FT_BUILD (release $VERSION); channel: $(release_channel)"
        grep -E '^(VERSION_ID|BUILD_ID)=' /etc/os-release | tr '\n' ' '; echo
        echo "steamvr: $(tr -d '\r' < /opt/steamvr/bin/version.txt 2>/dev/null || echo unknown); kernel: $(uname -r) $(uname -m)"
        echo; echo "## status"; cmd_status 2>&1 | sed 's/\x1b\[[0-9;]*m//g'
        echo; echo "## held tweaks"; ls "$STATE/held" 2>/dev/null || true
        echo; echo "## check-system"; cmd_check_system 2>&1
        echo; echo "## failed user services"; sysctl_user --failed --no-legend --plain 2>&1 | head -20
        echo; echo "## release that last installed each tweak"
        (cd "$STATE/installed" 2>/dev/null && grep -H . -- * | sed 's/:/: /')
        local unit id
        for unit in "$HOME"/.config/systemd/user/*.service; do       # the tweaks' own services
            [[ -f $unit ]] || continue
            for id in "${!DIR[@]}"; do
                grep -rqF "$(basename "$unit")" "${DIR[$id]}" 2>/dev/null || continue
                echo; echo "## service $(basename "$unit") ($id), last 60 lines"
                journalctl --user -u "$(basename "$unit")" -n 60 --no-pager -o short-iso 2>&1
                break
            done
        done
        local log
        for log in $(ls -t "$LOGS"/[0-9]*-*.log 2>/dev/null | head -2); do
            echo; echo "## log $(basename "$log")"; sed 's/\x1b\[[0-9;]*m//g' "$log" | tail -150
        done
    } | sed -E -e "s|$HOME|~|g" -e "s/\b$USER\b/<user>/g" -E -e "s/(^|[[:space:]@/'\"(])$(hostname 2>/dev/null || echo nohost)([[:space:]:.,)'\"]|$)/\1<host>\2/g" \
             -e 's/\b([0-9]{1,3}\.){3}[0-9]{1,3}\b/<ip>/g' -e 's/[[:alnum:]._%+-]+@[[:alnum:].-]+\.[[:alpha:]]{2,}/<email>/g' \
             -e 's/\b([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}\b/<mac>/g' -e 's/\b([[:xdigit:]]{1,4}:){7}[[:xdigit:]]{1,4}\b|[[:xdigit:]]{0,4}(:[[:xdigit:]]{1,4})*::([[:xdigit:]]{1,4}:)*[[:xdigit:]]{0,4}/<ipv6>/g' \
             ${phone:+-e "s/$phone/<phone>/g"} \
        > "$out"
    echo "Wrote $out"
    echo "$(t 'Read it before sharing; attach it to a bug report: %s' https://github.com/AstronautCheetah/frame-tweaks/issues)"
}

# check-system: run each installed tweak's optional check-system.sh, which tests whether the
# SteamOS / SteamVR internals it relies on are still there (useful after a SteamOS update).
cmd_check_system() {
    local id code out bad=0
    for id in "${IDS[@]}"; do
        [[ -f ${DIR[$id]}/check-system.sh ]] || continue
        status_of "$id" >/dev/null; [[ $? -eq 1 ]] && continue
        out=$(bash "${DIR[$id]}/check-system.sh" 2>&1); code=$?
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
    reinstall)   shift; take_lock; start_log reinstall "$@"; run_migrations "$@"; cmd_reinstall_ids "$@" ;;
    status|check) shift; cmd_status "$@" ;;
    update)      shift; take_lock; start_log update "$@"; cmd_update "$@" ;;
    _reinstall)  take_lock; start_log reinstall; cmd_reinstall ;;
    hold|unhold) cmd_hold "$@" ;;
    debug-info)  cmd_debug_info ;;
    check-system) cmd_check_system ;;
    _deps)       shift; [[ ${1:-} == all ]] && set -- "${IDS[@]}"; check_ids "$@"; with_deps "$@" | tr "\n" " "; echo ;;
    list)        cmd_list ;;
    # The installer window's other buttons, through the same code (lib/sft.py) or tools it uses.
    info|hide|unhide|hide-group|unhide-group|settings|mods) python3 lib/sft.py "$@" ;;
    run)         shift; [[ $# -eq 1 ]] || { echo "$(t 'run what?')" >&2; exit 1; }; check_ids "$1"
                 [[ -n $(python3 lib/sft.py run-label "$1") ]] || { echo "$(t '%s has nothing to run' "$1")" >&2; exit 1; }
                 setsid -f bash "${DIR[$1]}/run.sh" >/dev/null 2>&1 </dev/null ;;
    wallet)      shift; case ${1:-} in
                     lock) exec "$HOME/.local/bin/wallet-unlock" --lock ;;
                     unlock) exec "$HOME/.local/bin/wallet-unlock" ;;
                     status) exec "$HOME/.local/bin/wallet-unlock" --status ;;
                     *) echo "wallet lock|unlock|status" >&2; exit 1 ;;
                 esac ;;
    wallet-apps) shift; exec "$HOME/.local/bin/wallet-launcher" "${@:---list}" ;;
    timers)      shift; exec "$HOME/.local/bin/app-timers" "${@:---list}" ;;
    menu)        if [[ ${2:-} == --remove ]]; then remove_menu_entry; echo "$(t "Removed 'Frame Tweaks' from the app menu.")"
                 else ensure_menu_entry; echo "$(t "Added 'Frame Tweaks' to the app menu.")"; fi ;;
    -h|--help|help) usage ;;
    --version|version) echo "$FT_BUILD" ;;
    *)           take_lock; start_log install "$@"; run_migrations "$@"; cmd_install "$@" ;;
esac
