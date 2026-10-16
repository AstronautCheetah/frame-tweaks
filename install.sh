#!/bin/bash
# frame-tweaks: install, check, update and remove desktop-mode tweaks for the Steam Frame.
#
#   ./install.sh                     graphical checklist (in desktop mode), else this help
#   ./install.sh gui [--show ID]     the installer window (--show: open on that tweak's page)
#   ./install.sh install ID... | all install components (dependencies are added automatically)
#   ./install.sh uninstall [--keep-settings|--remove-settings] ID... | all
#                                    remove components; their settings are kept unless the
#                                    option or ⚙ Preferences says to remove them
#   ./install.sh forget-settings [--list]  delete the settings uninstalled tweaks left behind
#   ./install.sh uninstall-self [--keep-tweaks] [--remove-apps] [--remove-settings|--keep-settings]
#                                    uninstall Frame Tweaks itself (first every tweak, unless
#                                    --keep-tweaks; other projects' apps such as Claude Desktop stay
#                                    unless --remove-apps); this folder too, unless it holds work of yours
#   ./install.sh reinstall ID...     remove and install again (settings kept; a clean copy)
#   ./install.sh status [ID...]      health check of installed components (changes nothing)
#   ./install.sh update [--to vX.Y.Z | --to stable]
#                                    move to the newest (or given) release, re-run what's installed
#                                    (--to stable: the newest stable one, e.g. back from a test release)
#   ./install.sh channel [stable|beta]  which releases updates take: stable, or test releases too
#   ./install.sh hold|unhold ID...   keep a tweak as it is during updates (or stop doing so)
#   ./install.sh debug-info          write a redacted report for bug reports
#   ./install.sh report              the same, and the bug form's address to attach it to
#   ./install.sh check-system        are the SteamOS/SteamVR parts the tweaks rely on still there?
#   ./install.sh list                components and what they do
#   ./install.sh info ID             one component's details (as in the installer window)
#   ./install.sh run ID              its Run / Open button (e.g. open Arrow Pad)
#   ./install.sh settings ID [KEY=VALUE... | --reset]   show or change its settings (scroll-strips, adb-scrcpy)
#   ./install.sh mods [trust|untrust|on|off PACK | check FOLDER]   packs of tweaks (docs/mods.md)
#   ./install.sh mods add LINK [BRANCH|TAG] | update PACK | remove PACK   a pack shared as a git repository
#   ./install.sh mods updates   which of those have a newer version where they came from
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
WINDOW_LOG="$LOGS/window.log"   # setting up and opening the full window (./install.sh report)
migrate_legacy_dirs
# The tweaks moved into packs/official/ (0.6): an update leaves their old folders behind
# holding only Python's __pycache__ (git doesn't track it).
# The same for packs/official, which became packs/core, packs/integrations and packs/third-party (after 0.6.0).
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
    # (Only the installer's own logs, named by date and not in a folder: tweaks keep theirs here too,
    # e.g. a tweak's own *.log or a folder of its dated logs.)
    find "$LOGS" -maxdepth 1 -name '[0-9]*-*.log' -printf '%T@ %p\n' | sort -n | head -n -5 | cut -d' ' -f2- | xargs -r rm -f
}

# The tweaks, from the packs (lib/sft.py registry: the official packs and the user's trusted
# packs, each tweak described by its README.md front matter; see docs/mods.md).
declare -A TITLE DEPS DESC DIR EXPERIMENTAL LINKED SUDO
IDS=()
while IFS=$'\x1f' read -r id title deps desc dir exp linked sudo; do
    IDS+=("$id"); TITLE[$id]=$title; DEPS[$id]=$deps; DESC[$id]=$desc; DIR[$id]=$dir; EXPERIMENTAL[$id]=$exp
    LINKED[$id]=$linked; SUDO[$id]=$sudo
done < <(python3 lib/sft.py registry)
# (Frame Tweaks' own commands work without: every pack off or not trusted)
[[ ${#IDS[@]} -gt 0 || ${1:-} =~ ^(uninstall-self|forget-settings|menu|channel)$ ]] ||
    { echo "$(t 'No tweaks found (python3 lib/sft.py mods says why)')" >&2; exit 1; }
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
    ensure_menu_language
}
# Menu entries in the keyboard's language (lib/i18n.py menus): a systemd path unit relabels them
# when Steam saves its keyboard layout or a language is chosen in the window's ⚙ Preferences, so a
# menu opens in the language chosen before it; nothing
# polls. The entries are shared by VR and desktop mode, so one keyboard decides: Steam's (the
# unit runs in the VR session's environment). The units are rewritten only when they change.
MENU_UNIT=frame-tweaks-menus
ensure_menu_language() {
    local u="$HOME/.config/systemd/user" py="$HOME/.local/share/frame-tweaks/i18n/i18n.py" changed=
    install_i18n
    mkdir -p "$u"
    printf '%s\n' "[Unit]" "Description=Frame Tweaks: menu entries in the keyboard's language" "" \
        "[Path]" "PathChanged=%h/.local/share/Steam/config/config.vdf" "PathChanged=%h/.config/frame-tweaks/language" "" \
        "[Install]" "WantedBy=default.target" > "$u/$MENU_UNIT.path.new"
    printf '%s\n' "[Unit]" "Description=Frame Tweaks: menu entries in the keyboard's language" "" \
        "[Service]" "Type=oneshot" "ExecStart=/usr/bin/python3 $py menus" \
        "# (It rewrites only Frame Tweaks' menu entries: the rest of the system is out of its reach.)" \
        "NoNewPrivileges=yes" "ProtectSystem=strict" "ProtectHome=read-only" \
        "ReadWritePaths=-%h/.local/share/applications -%h/.local/share/frame-tweaks/launcher-originals" \
        "PrivateTmp=yes" "PrivateNetwork=yes" "RestrictAddressFamilies=AF_UNIX" "LockPersonality=yes" \
        "RestrictRealtime=yes" "RestrictNamespaces=yes" "SystemCallArchitectures=native" > "$u/$MENU_UNIT.service.new"
    for f in "$u/$MENU_UNIT.path" "$u/$MENU_UNIT.service"; do
        if cmp -s "$f.new" "$f"; then rm -f "$f.new"; else mv "$f.new" "$f"; changed=1; fi
    done
    if [[ -n $changed ]]; then
        sysctl_user daemon-reload 2>/dev/null || true
        sysctl_user enable --now "$MENU_UNIT.path" >/dev/null 2>&1 || true
    fi
    sysctl_user start --no-block "$MENU_UNIT.service" 2>/dev/null || true     # (labelled by the unit, as always)
}
# (keep-language: the unit stays for the tweaks' own menu entries, when they outlive Frame Tweaks)
remove_menu_entry() {
    local apps="$HOME/.local/share/applications" icons="$HOME/.local/share/icons/hicolor" n
    local id=io.github.AstronautCheetah.FrameTweaks
    rm -f "$apps/$id.desktop" "$HOME/.local/share/metainfo/$id.metainfo.xml" "$icons/256x256/apps/frame-tweaks.png"
    if [[ ${1:-} != keep-language ]]; then
        sysctl_user disable --now "$MENU_UNIT.path" >/dev/null 2>&1 || true
        rm -f "$HOME/.config/systemd/user/$MENU_UNIT.path" "$HOME/.config/systemd/user/$MENU_UNIT.service"
    fi
    for n in 64 128 256; do rm -f "$icons/${n}x$n/apps/$id.png"; done
    update-desktop-database -q "$apps" 2>/dev/null || true
    touch "$apps" "$icons" 2>/dev/null || true
}

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
is_component() { [[ -n ${TITLE[$1]:-} ]]; }

# tweak_script ID NAME [ARGS]: run the tweak's NAME.sh; for a linked project (manifest link:, no
# scripts of its own), lib/link.sh does the same from the link's fields.
tweak_script() {
    local id=$1 name=$2; shift 2
    if [[ -f ${DIR[$id]}/$name.sh ]]; then bash "${DIR[$id]}/$name.sh" "$@"
    elif [[ -n ${LINKED[$id]:-} ]]; then bash "$REPO_DIR/lib/link.sh" "$name" "$id" "$@"
    else return 127; fi
}

# status <id>: prints the component's one-line status; returns 0 ok, 1 missing (or uninstalled,
# waiting for a SteamVR restart), 2 warning (or installed, waiting for one)
status_of() { tweak_script "$1" status 2>/dev/null; }
installed_ids() {           # every tweak that is installed (or half: status 0 or 2)
    local id
    for id in "${IDS[@]}"; do status_of "$id" >/dev/null; [[ $? -ne 1 ]] && echo "$id"; done
    return 0
}

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
    [[ ${#out[@]} -eq 0 ]] || printf '%s\n' "${out[@]}"      # (none: no empty line, which isn't an id)
}

check_ids() {
    local id
    for id in "$@"; do
        is_component "$id" && continue
        local now
        if now=$(python3 lib/sft.py renamed "$id" 2>/dev/null); then
            echo "$(t '%s is now called %s' "$id" "$now")" >&2; exit 1
        fi
        echo "unknown component: $id (see ./install.sh list; a pack that isn't trusted: ./install.sh mods)" >&2; exit 1
    done
}

cmd_list() {
    bold "frame-tweaks $FT_BUILD"
    local id
    for id in "${IDS[@]}"; do
        printf '  %-15s %s%s%s\n' "$id" "${DESC[$id]}" "${EXPERIMENTAL[$id]:+ $(t '(experimental)')}" \
            "${SUDO[$id]:+ $(t '(asks for your sudo password)')}"
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
            1) [[ $line == "restart  "* ]] && line=${line#restart  } || line=$(t 'not installed')
               printf '  \033[2m·\033[0m %-15s \033[2m%s\033[0m\n' "$id" "$line" ;;
            *) line=${line#warning  }; printf '  \033[33m!\033[0m %-15s %s\n' "$id" "${line#restart  }"; worst=2 ;;
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
        if ! tweak_script "$id" install 8>&-; then failed+=("$id"); echo "!! $(t '%s failed' "$id")" >&2
        else record_version "$id"; fi
        echo
    done
    [[ ${#failed[@]} -eq 0 ]] || { echo "$(t 'Failed: %s' "${failed[*]}")" >&2; return 1; }
    bold "$(t 'Done.')"; cmd_status "$@"
}

cmd_uninstall() {
    local settings
    settings=$(python3 lib/sft.py uninstall-settings)          # ⚙ Preferences: keep (default) or remove
    case ${1:-} in --keep-settings) settings=keep; shift ;; --remove-settings) settings=remove; shift ;; esac
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
    local failed=()
    for id in "$@"; do
        bold "── $(t 'removing %s' "$id")"; stop_processes "$id"
        # (As with install: a failure is reported, and the version record stays with what's left.)
        if tweak_script "$id" uninstall 8>&-; then forget_version "$id"; uninstall_settings "$id" "$settings"
        else failed+=("$id"); echo "!! $(t '%s failed' "$id")" >&2; fi
        echo
    done
    [[ ${#failed[@]} -eq 0 ]] || { echo "$(t 'Failed: %s' "${failed[*]}")" >&2; return 1; }
}

# uninstall_settings ID keep|remove: what's left of the tweak's settings (its manifest's config:
# list) after its uninstall.sh: removed, or kept and named. (A reinstall doesn't come here.)
uninstall_settings() {
    local id=$1 how=$2 c kept=()
    while IFS= read -r c; do
        [[ -n $c ]] || continue
        c=$HOME/${c#\~/}
        [[ -e $c || -L $c ]] || continue
        if [[ $how == remove ]]; then remove_files "$c"; else kept+=("${c/#$HOME/\~}"); fi
    done < <(python3 lib/sft.py config "$id")
    [[ ${#kept[@]} -eq 0 ]] || say "$(t 'Kept its settings: %s (to remove them too: ./install.sh uninstall --remove-settings %s)' "${kept[*]}" "$id")"
}

# forget-settings [--list]: the settings tweaks left behind when they were uninstalled (kept, as
# ⚙ Preferences said then). Installed tweaks' settings are never touched. (The window's ⚙
# Preferences button does the same.)
cmd_forget_settings() {
    local id p n=0
    # shellcheck disable=SC2046
    while IFS=$'\t' read -r id p; do
        n=$((n + 1))
        if [[ ${1:-} == --list ]]; then echo "$id	$p"; else say "$(t 'removed %s' "$p") ($id)"; fi
    done < <(python3 lib/sft.py leftover-settings $([[ ${1:-} == --list ]] || echo --delete) $(installed_ids))
    [[ $n -gt 0 ]] || { t 'No settings left behind by uninstalled tweaks.'; echo; }
}

# uninstall-self [--keep-tweaks] [--remove-apps] [--remove-settings|--keep-settings]: Frame Tweaks itself.
#  1. every tweak, unless --keep-tweaks (stops here if one fails: you can run it again), but
#     those that install another project's app (manifest app:, e.g. Claude Desktop) and what they
#     depend on, unless --remove-apps: the apps stay, and work as before;
#  2. with --remove-settings (default: ⚙ Preferences' choice), the settings uninstalled tweaks
#     left, and Frame Tweaks' own; those of tweaks still installed stay;
#  3. its app-menu entry; with no tweak left, the files they shared (~/.local/share/frame-tweaks
#     but your own packs/, ~/.cache/frame-tweaks, ~/.local/state/frame-tweaks but backups still
#     waiting to go back, and what VR dashboard patching needs to put SteamVR's setting back
#     when SteamVR stops) and the Python setup the window ran in;
#  4. this folder, if nothing of yours is in it (changes, your own packs, commits not pushed,
#     other worktrees): else it stays, and says why.
cmd_uninstall_self() {
    local tweaks=remove apps=keep settings installed p
    settings=$(python3 lib/sft.py uninstall-settings)
    while [[ $# -gt 0 ]]; do
        case $1 in
            --keep-tweaks) tweaks=keep ;;
            --remove-apps) apps=remove ;;
            --keep-apps) apps=keep ;;
            --remove-settings) settings=remove ;;
            --keep-settings) settings=keep ;;
            *) echo "$(t 'uninstall-self takes --keep-tweaks, --remove-apps, --remove-settings and --keep-settings')" >&2; exit 1 ;;
        esac
        shift
    done
    if [[ $tweaks == remove ]]; then
        bold "$(t 'Uninstalling every tweak')"
        local -A keep=() named=()
        local id order drop=() left=()
        if [[ $apps == keep ]]; then
            while IFS=$'\t' read -r id p; do [[ -n $id ]] && named[$id]=$p; done < <(python3 lib/sft.py apps)
            # (each app's tweak, and what it needs: removing that would be refused, or break it)
            for id in $(with_deps "${!named[@]}"); do keep[$id]=1; done
        fi
        mapfile -t order < <(with_deps "${IDS[@]}")
        for (( p=${#order[@]}-1; p>=0; p-- )); do        # (dependents first)
            id=${order[p]}
            status_of "$id" >/dev/null; [[ $? -ne 1 ]] || continue
            if [[ -n ${keep[$id]:-} ]]; then [[ -n ${named[$id]:-} ]] && left+=("${named[$id]}"); else drop+=("$id"); fi
        done
        if [[ ${#drop[@]} -gt 0 ]] && ! ( cmd_uninstall "--$settings-settings" "${drop[@]}" ); then
            echo "$(t 'Frame Tweaks is still here: see what failed above, then run this again.')" >&2; return 1
        fi
        [[ ${#drop[@]} -gt 0 ]] || { t 'Nothing installed.'; echo; }
        [[ ${#left[@]} -eq 0 ]] || say "$(t 'Left installed, as asked: %s (to remove them too: ./install.sh uninstall-self --remove-apps)' "$(IFS=,; echo "${left[*]}" | sed 's/,/, /g')")"
    fi
    # Tweaks of packs not in use (turned off, or no longer trusted) aren't listed, but their
    # install record says they're there, using what's shared: they count as installed.
    local others=() r
    for r in "$STATE"/installed/*; do
        [[ -e $r ]] && ! is_component "${r##*/}" && others+=("${r##*/}")
    done
    installed=$(installed_ids; [[ ${#others[@]} -eq 0 ]] || printf '%s\n' "${others[@]}")
    bold "$(t 'Uninstalling Frame Tweaks')"
    [[ ${#others[@]} -eq 0 ]] || say "$(t 'Still installed, from packs not in use (turned off, or not trusted): %s. To uninstall them too, use their pack again (./install.sh mods), then run this again.' "${others[*]}")"
    [[ $settings == remove ]] && cmd_forget_settings | grep -v "^$(t 'No settings left behind by uninstalled tweaks.')$"
    if [[ -n $installed ]]; then
        remove_menu_entry keep-language
        [[ $settings == remove ]] && remove_files "$HOME/.config/frame-tweaks/installer" "$HOME/.config/frame-tweaks/uninstall-settings"
        say "$(t 'Kept for the tweaks still installed (%s): ~/.local/share/frame-tweaks, ~/.local/state/frame-tweaks and their settings.' "$(echo $installed)")"
    else
        remove_menu_entry
        rm -f "$QT_VENV/bin/sft-python"; remove_qt_venv
        if [[ -d $HOME/.local/share/frame-tweaks ]]; then
            find "$HOME/.local/share/frame-tweaks" -mindepth 1 -maxdepth 1 ! -name packs -exec rm -rf {} +
            rmdir "$HOME/.local/share/frame-tweaks" 2>/dev/null && say "$(t 'removed %s' "$HOME/.local/share/frame-tweaks")"
            [[ -d $HOME/.local/share/frame-tweaks/packs ]] && say "$(t 'Kept your own packs: %s' "$HOME/.local/share/frame-tweaks/packs")"
        fi
        remove_files "$HOME/.cache/frame-tweaks"
        if [[ -d $STATE ]]; then
            for p in "$STATE"/* "$STATE"/.[!.]*; do
                [[ -e $p ]] || continue
                case ${p##*/} in
                    sft-dashboard-restore|vr-debugger.prev) [[ -e $STATE/sft-dashboard-restore ]] && continue ;;
                    backups) [[ -n $(find "$p" -type f -print -quit) ]] && { say "$(t 'Kept backups of files tweaks changed: %s' "$p")"; continue; } ;;
                esac
                rm -rf -- "$p"
            done
            rmdir "$STATE" 2>/dev/null && say "$(t 'removed %s' "$STATE")"
            [[ -e $STATE/sft-dashboard-restore ]] && say "$(t "SteamVR's own setting goes back when SteamVR stops; then this goes too: %s" "$STATE")"
        fi
        [[ $settings == remove ]] && remove_files "$HOME/.config/frame-tweaks"
    fi
    [[ $settings == keep ]] && [[ -d $HOME/.config/frame-tweaks ]] && say "$(t 'Kept the settings: %s' "$HOME/.config/frame-tweaks")"
    remove_checkout
}

# remove_checkout: this folder goes, unless something of yours is in it.
remove_checkout() {
    local here=$PWD why=
    if [[ -n ${FRAME_TWEAKS_KEEP_CHECKOUT:-} ]]; then      # (tests: the checkout they run from; first, always)
        say "FRAME_TWEAKS_KEEP_CHECKOUT: kept $here"
        bold "$(t 'Frame Tweaks is uninstalled.')"
        return
    fi
    if [[ -f .git ]]; then
        why=$(t 'it is a git worktree')
    elif [[ -e .git ]]; then
        if [[ -n $(git status --porcelain --ignored --untracked-files=all 2>/dev/null | grep -vE '(^|/)__pycache__/|\.pyc$') ]]; then
            why=$(t 'it has files of yours: changes, your own packs in packs/, or a tmp/ folder')
        elif [[ -n $(git log --branches --not --remotes --oneline 2>/dev/null | head -1) ]]; then
            why=$(t 'it has commits that are not pushed anywhere')
        elif [[ $(git worktree list 2>/dev/null | wc -l) -gt 1 || -n $(git stash list 2>/dev/null | head -1) ]]; then
            why=$(t 'it has other worktrees or stashed changes')
        fi
    elif [[ -n $(find packs -mindepth 1 -maxdepth 1 -type d ! -name core ! -name original ! -name integrations ! -name third-party -print -quit) ]]; then
        why=$(t 'it has your own packs in packs/')
    fi
    if [[ -n $why ]]; then
        say "$(t 'Kept this folder, %s: %s. Delete it yourself when you no longer need it.' "$here" "$why")"
    else
        cd / && rm -rf -- "$here" && say "$(t 'removed %s' "$here")"
    fi
    bold "$(t 'Frame Tweaks is uninstalled.')"
}

# Remove, then install again. Unlike uninstall, a tweak others depend on may be removed here:
# it's back a moment later.
cmd_reinstall_ids() {
    [[ $# -eq 0 ]] && { echo "$(t 'reinstall what?')" >&2; exit 1; }
    check_ids "$@"
    local id
    # (FRAME_TWEAKS_REINSTALL: an uninstall that keeps what other tweaks put in its care, e.g. the
    # dashboard patches of the tweaks that use the VR environment helper.)
    # (a linked project isn't removed first: its own installer, run again, updates it)
    for id in "$@"; do
        [[ -n ${LINKED[$id]:-} ]] && continue
        bold "── $(t 'removing %s' "$id")"; stop_processes "$id"; FRAME_TWEAKS_REINSTALL=1 bash "${DIR[$id]}/uninstall.sh" 8>&-; forget_version "$id"; echo
    done
    cmd_install "$@"
}

cmd_update() {
    local want=""
    [[ ${1:-} == --to ]] && { want=${2:?"$(t '--to needs a release, e.g. v0.3.1')"}; [[ $want == v* || $want == stable ]] || want="v$want"; }
    if [[ -d .git ]]; then
        local before; before=$(git rev-parse -q --verify HEAD)
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
            local tag current
            if [[ $want == stable ]]; then tag=$(git tag -l 'v*' | FRAME_TWEAKS_CHANNEL=stable newest_tag)
            else tag=${want:-$(git tag -l 'v*' | newest_tag)}; fi
            [ -n "$tag" ] || { echo "$(t 'no release found')" >&2; exit 1; }
            # Never back to an older release unasked: a tester whose channel is stable again stays
            # on the test release until a newer stable one is out (or asks: --to stable).
            current=$(git tag --points-at HEAD -l 'v*' | FRAME_TWEAKS_CHANNEL=beta newest_tag)
            if [[ -z $want && -n $current ]] && tag_newer "$current" "$tag"; then
                say "$(t "You're on %s, a test release newer than the newest stable release (%s): you stay on it until a newer stable release is out. To go back to %s now: %s" "$current" "$tag" "$tag" "./install.sh update --to stable")"
                tag=$current
            fi
            git rev-parse -q --verify "refs/tags/$tag" >/dev/null || { echo "$(t 'no release %s' "$tag")" >&2; exit 1; }
            verify_release "$PWD" "$tag" || exit 1
            [[ $(git rev-parse "refs/tags/$tag^{commit}") == "$before" ]] ||
                bold "$(t 'Updating to %s (%s channel)' "$tag" "$(release_channel)")"
            # (refs/tags/: the tag just verified, even if a branch has its name. A failed checkout,
            # local changes in the way say, stops here: the tree is the old one or half switched.)
            git -c advice.detachedHead=false checkout --quiet "refs/tags/$tag" ||
                { echo "$(t 'git checkout failed; not reinstalling')" >&2; exit 1; }
        fi
        # Nothing changed (the newest already, as when the install command runs again over an
        # install): the installed tweaks are as that version installs them, so their installers
        # aren't run again (all of them, minutes, before the window opened).
        if [[ $(git rev-parse -q --verify HEAD) == "$before" ]]; then
            say "$(t "Frame Tweaks is up to date (%s): nothing to reinstall. To run the installed tweaks' installers again anyway: %s" "$FT_BUILD" "./install.sh reinstall")"
            return 0
        fi
        FRAME_TWEAKS_UPDATING=1 exec ./install.sh _reinstall   # re-exec so the new version of this script runs
    fi
    cmd_reinstall
}

# channel [stable|beta]: which releases updates take (lib/common.sh release_channel)
cmd_channel() {
    local f="$HOME/.config/frame-tweaks/channel" pre
    case ${1:-} in
        "") release_channel; return ;;
        stable|beta) mkdir -p "${f%/*}"; echo "$1" > "$f" ;;
        *) echo "$(t 'channel stable|beta')" >&2; exit 1 ;;
    esac
    if [[ $1 == beta ]]; then
        say "$(t 'Updates now take test releases too (vX.Y.Z-rc.N: newer, less tested). To get the newest: %s' "./install.sh update")"
        return
    fi
    say "$(t 'Updates now take stable releases only.')"
    pre=$(git tag --points-at HEAD -l 'v*-*' 2>/dev/null | head -1)
    [[ -n $pre ]] && say "$(t "You're on %s, a test release: you move to the next stable release when it's out. To go back to the newest stable release now: %s" "$pre" "./install.sh update --to stable")"
    return 0
}

cmd_reinstall() {
    local id installed=() linked=()
    for id in "${IDS[@]}"; do
        status_of "$id" >/dev/null; [[ $? -ne 1 ]] || continue
        # (a linked project updates its own way: its installer isn't run with every update)
        if [[ -n ${LINKED[$id]:-} ]]; then linked+=("$id"); else installed+=("$id"); fi
    done
    [[ ${#linked[@]} -gt 0 ]] && say "$(t 'Linked, so they update their own way (their row: ↻ runs their installer again): %s' "${linked[*]}")"
    [[ ${#installed[@]} -eq 0 ]] && { t 'Nothing installed yet.'; echo; return; }
    run_migrations "${installed[@]}"
    cmd_install "${installed[@]}"
    echo; bold "$(t 'Checking the SteamOS/SteamVR parts the tweaks rely on')"; cmd_check_system || true
}

cmd_gui() {               # [--show ID]: open on that tweak's page
    ensure_menu_entry
    # The full window (hide rows, live status) needs PyQt6, the toolkit it's drawn with (shared
    # with Arrow Pad, Screen snip and the NordVPN tray, if they're installed). Offer to set it up;
    # otherwise fall back to kdialog's plain checklist. (Naming those tweaks in the question read
    # as if it installed them: it doesn't.)
    local qt="$QT_VENV"
    if ! "$qt/bin/python" -c 'import PyQt6' 2>/dev/null &&
       kdialog --title "Frame Tweaks" --yesno "$(t "Set up the full installer window? It needs PyQt6, the toolkit it's drawn with (about 280 MB, in your home folder). Nothing else is installed: you choose the tweaks in the window.\n\nNo = use the simple checklist instead: it installs and removes the same tweaks, without the details, status and settings pages.")"; then
        setup_window ||
            kdialog --sorry "$(t "Couldn't install PyQt6 (what happened: %s); using the simple checklist." "$WINDOW_LOG")"
    fi
    if "$qt/bin/python" -c 'import PyQt6' 2>/dev/null; then
        open_window "$@" && return 0
        kdialog --sorry "$(t "The full window didn't open (what happened: %s); using the simple checklist." "$WINDOW_LOG")"
    fi
    cmd_kdialog_gui
}

# setup_window: PyQt6 for the full window, where you can see it happen: pip's progress in this
# terminal, or (started from the app menu, with no terminal) in a Konsole window of its own. It
# used to set up without a word for a minute or more, which looked like nothing happening; a
# window closed then left it half done. pip's log goes to WINDOW_LOG either way.
setup_window() {
    mkdir -p "$LOGS"
    echo "$(date '+%F %T') setting up PyQt6 for the full window ($FT_BUILD)" >> "$WINDOW_LOG"
    if [ -t 1 ]; then
        cmd_setup_window
    elif command -v konsole >/dev/null; then
        konsole --separate -e "$REPO_DIR/install.sh" _setup-window >/dev/null 2>&1
    else
        notify-send -a "Frame Tweaks" "$(t 'Setting up the full installer window')" \
            "$(t "About 280 MB, usually a minute or two: the window opens when it's done.")" 2>/dev/null
        cmd_setup_window >> "$WINDOW_LOG" 2>&1
    fi
    "$QT_VENV/bin/python" -c 'import PyQt6' 2>/dev/null
}
cmd_setup_window() {              # (_setup-window: in the Konsole window setup_window opens)
    if PIP_LOG="$WINDOW_LOG" FRAME_TWEAKS_PIP_PROGRESS=1 ensure_qt_venv "$(t "Setting up the full installer window: PyQt6, the toolkit it's drawn with (about 280 MB, usually a minute or two). It opens when this is done.")"; then
        echo "$(date '+%F %T') PyQt6 set up" >> "$WINDOW_LOG"
        return 0
    fi
    echo "$(date '+%F %T') PyQt6 setup failed" >> "$WINDOW_LOG"
    if [ -t 0 ]; then echo; read -rp "$(t "That didn't work (what happened: %s). Press Enter to close." "$WINDOW_LOG")" _; fi
    return 1
}

# open_window: the full window (a second one hands over to the one already open, which says
# where it is). One that ends with an error before it's shown (within 20 s) didn't open: the
# caller says so and the simple checklist stands in, instead of nothing on screen.
open_window() {
    # A copy of the interpreter under its own name, so SteamVR gives the window its own
    # controller bindings (it keys them by program name; Arrow Pad also runs on Python).
    local py="$QT_VENV/bin/sft-python" start=$SECONDS rc
    cp -u "$(readlink -f "$QT_VENV/bin/python")" "$py" 2>/dev/null || true
    "$py" -c 'import PyQt6' 2>/dev/null || py="$QT_VENV/bin/python"
    mkdir -p "$LOGS"
    echo "$(date '+%F %T') opening the window ($FT_BUILD)" >> "$WINDOW_LOG"
    "$py" gui/frame-tweaks-gui.py "$@" 2> >(tee -a "$WINDOW_LOG" >&2)
    rc=$?
    [[ $rc -eq 0 ]] && return 0
    echo "$(date '+%F %T') the window ended with $rc after $((SECONDS - start)) s" >> "$WINDOW_LOG"
    [[ $((SECONDS - start)) -ge 20 ]]
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
# Report a problem: the diagnostics report, then the bug form (version filled in) to attach it to.
BUG_FORM="https://github.com/AstronautCheetah/frame-tweaks/issues/new?template=bug_report.yml"
cmd_report() {
    cmd_debug_info
    echo
    t 'The bug form, with your version filled in: %s' "$BUG_FORM&version=${FT_BUILD//+/%2B}"; echo
}

cmd_debug_info() {
    local out; out="$HOME/frame-tweaks-debug-$(date +%Y%m%d-%H%M%S).txt"
    # Your phone's name too (Android Mirror's PHONE_NAME), escaped for sed -E ("Galaxy S24+ (Bob)").
    local phone; phone=$(bash -c '. "$HOME/.config/frame-tweaks/phone.conf" 2>/dev/null; printf %s "${PHONE_NAME:-}"' |
                         sed 's/[][\.*^$/&|(){}+?]/\\&/g')       # (read as phone does: it's shell-quoted)
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
        echo; echo "## links opened from the window (lib/browser.py), last 20"
        tail -20 "$LOGS/links.log" 2>/dev/null || true
        echo; echo "## Arrow Pad's Unstick: what it found, last 20"
        tail -20 "$LOGS/unstick.log" 2>/dev/null || true
        echo; echo "## the full window: setting it up and opening it, last 40"
        tail -40 "$WINDOW_LOG" 2>/dev/null || true
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
    gui)         shift; cmd_gui "$@" ;;
    # ("all" is every tweak, for the migrations as for the installs)
    install)     shift; take_lock; start_log install "$@"; [[ ${1:-} == all ]] && set -- "${IDS[@]}"; run_migrations "$@"; cmd_install "$@" ;;
    uninstall|remove) shift; take_lock; start_log uninstall "$@"; cmd_uninstall "$@" ;;
    reinstall)   shift; take_lock; start_log reinstall "$@"; run_migrations "$@"; cmd_reinstall_ids "$@" ;;
    status|check) shift; cmd_status "$@" ;;
    update)      shift; take_lock; start_log update "$@"; cmd_update "$@" ;;
    _reinstall)  take_lock; start_log reinstall; cmd_reinstall ;;
    _setup-window) cmd_setup_window ;;
    hold|unhold) cmd_hold "$@" ;;
    channel)     shift; cmd_channel "$@" ;;
    debug-info)  cmd_debug_info ;;
    report)      cmd_report ;;
    check-system) cmd_check_system ;;
    _deps)       shift; [[ ${1:-} == all ]] && set -- "${IDS[@]}"; check_ids "$@"; with_deps "$@" | tr "\n" " "; echo ;;
    list)        cmd_list ;;
    # The installer window's other buttons, through the same code (lib/sft.py) or tools it uses.
    info|hide|unhide|hide-group|unhide-group|settings|mods) python3 lib/sft.py "$@" ;;
    run)         shift; [[ $# -eq 1 ]] || { echo "$(t 'run what?')" >&2; exit 1; }; check_ids "$1"
                 [[ -n $(python3 lib/sft.py run-label "$1") ]] || { echo "$(t '%s has nothing to run' "$1")" >&2; exit 1; }
                 if [[ -f ${DIR[$1]}/run.sh ]]; then setsid -f bash "${DIR[$1]}/run.sh" >/dev/null 2>&1 </dev/null
                 else setsid -f bash "$REPO_DIR/lib/link.sh" run "$1" >/dev/null 2>&1 </dev/null; fi ;;
    wallet)      shift; case ${1:-} in
                     lock) exec "$HOME/.local/bin/wallet-unlock" --lock ;;
                     unlock) exec "$HOME/.local/bin/wallet-unlock" ;;
                     status) exec "$HOME/.local/bin/wallet-unlock" --status ;;
                     *) echo "wallet lock|unlock|status" >&2; exit 1 ;;
                 esac ;;
    wallet-apps) shift; exec "$HOME/.local/bin/wallet-launcher" "${@:---list}" ;;
    timers)      shift; exec "$HOME/.local/bin/app-timers" "${@:---list}" ;;
    forget-settings) shift; take_lock; start_log forget-settings "$@"; cmd_forget_settings "$@" ;;
    uninstall-self) shift; take_lock; start_log uninstall-self "$@"; cmd_uninstall_self "$@" ;;
    menu)        if [[ ${2:-} == --remove ]]; then remove_menu_entry; echo "$(t "Removed 'Frame Tweaks' from the app menu.")"
                 else ensure_menu_entry; echo "$(t "Added 'Frame Tweaks' to the app menu.")"; fi ;;
    -h|--help|help) usage ;;
    --version|version) echo "$FT_BUILD" ;;
    *)           take_lock; start_log install "$@"; [[ $1 == all ]] && set -- "${IDS[@]}"; run_migrations "$@"; cmd_install "$@" ;;
esac
