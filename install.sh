#!/bin/bash
# steam-frame-tweaks: install, check, update and remove desktop-mode tweaks for the Steam Frame.
#
#   ./install.sh                     graphical checklist (in desktop mode), else this help
#   ./install.sh install ID... | all install components (dependencies are added automatically)
#   ./install.sh uninstall ID...     remove components
#   ./install.sh status [ID...]      health check of installed components (changes nothing)
#   ./install.sh update              git pull, then re-run the installer of everything installed
#   ./install.sh list                components and what they do
#   ./install.sh menu                (re)create the "Steam Frame Tweaks" app-menu entry
#   ./install.sh ID...               same as "install ID..."
#
# Everything installs into your home directory; nothing touches SteamOS's read-only system
# partition, so OS updates don't undo it. Every installer is safe to re-run.
set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")" || exit 1
VERSION=$(cat VERSION 2>/dev/null || echo dev)

# components.tsv: id <TAB> title <TAB> depends (space-separated) <TAB> description
declare -A TITLE DEPS DESC
IDS=()
# (Tabs become \x1f first: read merges empty fields between whitespace separators like tab.)
while IFS=$'\x1f' read -r id title deps desc _source; do
    [[ -z $id || $id == \#* ]] && continue
    IDS+=("$id"); TITLE[$id]=$title; DEPS[$id]=$deps; DESC[$id]=$desc
done < <(tr '\t' '\037' < components.tsv)

# The installer's own app-menu entry (desktop menu and Steam's VR "+" menu).
ensure_menu_entry() {
    local apps="$HOME/.local/share/applications" icons="$HOME/.local/share/icons/hicolor"
    mkdir -p "$apps" "$icons/256x256/apps"
    install -m644 icons/frame-tweaks.png "$icons/256x256/apps/frame-tweaks.png"
    cat > "$apps/steam-frame-tweaks.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Steam Frame Tweaks
Comment=Install, check and remove Steam Frame desktop-mode tweaks
Exec=env FRAME_TWEAKS_GUI=1 $PWD/install.sh gui
Icon=frame-tweaks
Terminal=false
Categories=Settings;Utility;
DESKTOP
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
        if ! "./$id/install.sh"; then failed+=("$id"); echo "!! $id failed" >&2; fi
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
    for id in "$@"; do bold "── removing $id"; "./$id/uninstall.sh"; echo; done
}

cmd_update() {
    if [[ -d .git ]]; then
        bold "Updating the checkout"; git pull --ff-only || { echo "git pull failed; not reinstalling" >&2; exit 1; }
        exec ./install.sh _reinstall      # re-exec so the new version of this script runs
    fi
    cmd_reinstall
}

cmd_reinstall() {
    local id installed=()
    for id in "${IDS[@]}"; do status_of "$id" >/dev/null; [[ $? -ne 1 ]] && installed+=("$id"); done
    [[ ${#installed[@]} -eq 0 ]] && { echo "Nothing installed yet."; return; }
    cmd_install "${installed[@]}"
}

cmd_gui() {
    ensure_menu_entry
    # The full window (hide rows, live status) needs PyQt6, shared with Arrow Pad and the
    # NordVPN tray. Offer to set it up; otherwise fall back to kdialog's plain checklist.
    local qt="$HOME/.local/share/arrowpad/venv"
    if ! "$qt/bin/python" -c 'import PyQt6' 2>/dev/null &&
       kdialog --title "Steam Frame Tweaks" --yesno "Set up the full installer window? It needs PyQt6 (about 280 MB, shared with Arrow Pad and the NordVPN tray).\n\nNo = use the simple checklist."; then
        python3 -m venv "$qt" && "$qt/bin/pip" install -q PyQt6 ||
            kdialog --sorry "Couldn't install PyQt6; using the simple checklist."
    fi
    if "$qt/bin/python" -c 'import PyQt6' 2>/dev/null; then
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
    picked=$(kdialog --title "Steam Frame Tweaks $VERSION" --geometry 900x560 --separate-output \
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

usage() { sed -n '2,15s/^# \{0,1\}//p' "$0"; }

case ${1:-} in
    "")          if [[ ! -t 0 || -n ${FRAME_TWEAKS_GUI:-} ]] && command -v kdialog >/dev/null && [[ -n ${WAYLAND_DISPLAY:-${DISPLAY:-}} ]]; then cmd_gui
                 else usage; echo; cmd_status; fi ;;
    gui)         cmd_gui ;;
    install)     shift; cmd_install "$@" ;;
    uninstall|remove) shift; cmd_uninstall "$@" ;;
    status|check) shift; cmd_status "$@" ;;
    update)      cmd_update ;;
    _reinstall)  cmd_reinstall ;;
    _deps)       shift; [[ ${1:-} == all ]] && set -- "${IDS[@]}"; check_ids "$@"; with_deps "$@" | tr "\n" " "; echo ;;
    list)        cmd_list ;;
    menu)        ensure_menu_entry; echo "Added 'Steam Frame Tweaks' to the app menu." ;;
    -h|--help|help) usage ;;
    --version|version) echo "$VERSION" ;;
    *)           cmd_install "$@" ;;
esac
