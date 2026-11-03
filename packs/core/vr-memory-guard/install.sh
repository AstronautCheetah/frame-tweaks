#!/bin/bash
# VR memory guard: Flatpak apps leave memory free for SteamVR, each can have a limit of its own
# (Firefox's 5 GB by default), and SteamVR is the last thing the kernel stops when memory runs
# out. Limits in ~/.config/frame-tweaks/vr-memory-guard.conf and, each app's own,
# vr-memory-guard-apps.conf; see README.md.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
CONF="$HOME/.config/frame-tweaks/vr-memory-guard.conf"
UNITS="$HOME/.config/systemd/user"
DROPIN=frame-tweaks-vr-memory-guard.conf
mkdir -p "${CONF%/*}"
[ -f "$CONF" ] || install -m644 "$TWEAK_DIR/vr-memory-guard.conf" "$CONF"

get() { sed -n "s/^$1=//p" "$CONF" | tail -1 | tr -d '[:space:]'; }
# mib SIZE: a size written as 5G or 512M (or 0) in MiB; fails on anything else. (vr-memory-guard-tool's
# mib reads sizes the same way: change both together.)
mib() {
    case $1 in
        0) echo 0 ;;
        [1-9]*[Gg]) [[ ${1%?} =~ ^[0-9]+$ ]] && echo $(( ${1%?} * 1024 )) ;;
        [1-9]*[Mm]) [[ ${1%?} =~ ^[0-9]+$ ]] && echo "${1%?}" ;;
        *) return 1 ;;
    esac
}
size() {     # size NAME: the setting in MiB, or stop and say which line is wrong
    local v; v=$(mib "$(get "$1")") && [ -n "$v" ] ||
        die "$(t '%s in %s should be a size such as 5G or 512M (it is "%s").' "$1" "$CONF" "$(get "$1")")"
    echo "$v"
}
# size_or NAME DEFAULT: as size, but a limits file from before the setting existed gets the default
size_or() { if [ -z "$(get "$1")" ]; then mib "$2"; else size "$1"; fi; }
dict=$(size_or dictation_max 2500M); mirror=$(size_or mirror_max 1G)
# The apps' shared limit (app.slice) and each app's own are vr-memory-guard-tool's, which the
# installer window's Memory limits page runs too: one program writes them, so both read the
# settings alike. Checked before anything is written; it says what's wrong.
install_i18n         # (first: the check's messages in your language)
python3 "$TWEAK_DIR/vr-memory-guard-tool" check || exit 1
ensure_path
mkdir -p "$BIN"
install -m755 "$TWEAK_DIR/vr-memory-guard-tool" "$BIN/"

# dropin UNIT TEXT: our drop-in for UNIT.
dropin() { mkdir -p "$UNITS/$1.d"; printf '%s\n' "$2" > "$UNITS/$1.d/$DROPIN"; }
# Frame Tweaks' own heavy helpers, outside Flatpak: Dictation's services (its button's runs Whisper
# for each dictation; its engine kept loaded) and Android Mirror's scrcpy, which phone runs in a
# scope of this slice (app-ftmirror.slice, inside app.slice: also within the apps' limit). Opened
# from Steam's + menu it ran in steam.service, which nothing limits, and a drop-in there would
# limit Steam itself. (No MemoryHigh, as for the apps: see vr-memory-guard-tool's apply.)
for unit in frame-tweaks-dictate-engine.service frame-tweaks-dictate-button.service; do
    dropin "$unit" "[Service]
MemoryMax=${dict}M
MemorySwapMax=512M"
done
dropin app-ftmirror.slice "[Slice]
MemoryMax=${mirror}M
MemorySwapMax=256M"
# (100 is the lowest a user's own service may set, the user manager's own value; apps run at 200,
# so when memory runs out anyway the kernel stops an app before SteamVR.)
dropin steamvr.service "[Service]
OOMScoreAdjust=100"
# The apps' drop-ins, then daemon-reload (for the ones above too) and the apps open now.
"$BIN/vr-memory-guard-tool" apply || exit 1

for unit in frame-tweaks-dictate-engine.service frame-tweaks-dictate-button.service; do
    ! sysctl_user is-active --quiet "$unit" ||
        sysctl_user set-property --runtime "$unit" MemoryMax="${dict}M" MemorySwapMax=512M || true
done
say "$(t 'Dictation: up to %s MB; Android Mirror: up to %s MB (from its next start).' "$dict" "$mirror")"
if sysctl_user is-active --quiet steamvr.service; then
    say "$(t 'SteamVR is given priority from its next start.')"
fi
