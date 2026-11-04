# shellcheck shell=bash
# Shared helpers for frame-tweaks installers. Source, don't execute.
# Everything installs into the user's home (~/.local), so SteamOS's read-only
# root and system updates are never touched.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/i18n.sh
source "$REPO_DIR/lib/i18n.sh"      # t 'Text %s' VALUE: in the user's language
# The exact build, for people and logs: 0.5.0 at its release tag, 0.5.0+3.abc1234 three commits
# after it, 0.5.0+abc1234 when that tag isn't in this clone, -dirty with local changes; the
# VERSION file alone without git. VERSION is the one source of the number (migrations and update
# checks compare it): `git describe` named whichever tag it reached first, an older one when the
# release tag sat on a branch not merged yet, and then disagreed with VERSION. (lib/sft.py
# build_version says the same.)
ft_version() {
    local v head n dirty=""
    v=$(cat "$REPO_DIR/VERSION" 2>/dev/null) || v=dev
    head=$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null) || { echo "$v"; return; }
    [ -z "$(git -C "$REPO_DIR" status --porcelain --untracked-files=no 2>/dev/null)" ] || dirty=-dirty
    if n=$(git -C "$REPO_DIR" rev-list --count "refs/tags/v$v..HEAD" 2>/dev/null); then
        if [ "$n" = 0 ]; then echo "$v$dirty"; else echo "$v+$n.$head$dirty"; fi
    else
        echo "$v+$head$dirty"
    fi
}
# The folder of the tweak whose script sourced this file (its own files), and tweak_dir <id> for
# another tweak's: the installer passes the folders it found (FRAME_TWEAKS_DIRS, "id=folder"
# lines, user packs included); a script run on its own falls back to the official packs.
# (A script run by a relative path that changes folder before sourcing this, as install.sh does
# when run as frame-tweaks/install.sh, can't be found from here: then it's the folder it's in now,
# rather than a cd that failed and, with set -e, stopped it.)
TWEAK_DIR="$(cd "$(dirname "${BASH_SOURCE[1]:-$0}")" 2>/dev/null && pwd || pwd)"
tweak_dir() {
    local line
    while IFS= read -r line; do
        [ "${line%%=*}" = "$1" ] && { echo "${line#*=}"; return; }
    done <<<"${FRAME_TWEAKS_DIRS:-}"
    local pack
    for pack in core integrations third-party; do
        [ -d "$REPO_DIR/packs/$pack/$1" ] && { echo "$REPO_DIR/packs/$pack/$1"; return; }
    done
    echo "$REPO_DIR/packs/core/$1"
}
export FRAME_TWEAKS_LIB="$REPO_DIR/lib"     # (for the scripts a tweak runs in turn, wherever they are)
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
# HTTPS mirrors only (the main mirror's certificate doesn't match its name, so it isn't used);
# every package is signature-checked too.
ALARM_MIRROR="${ALARM_MIRROR:-https://fl.us.mirror.archlinuxarm.org/aarch64}"
ALARM_FALLBACK="https://de3.mirror.archlinuxarm.org/aarch64"
mkdir -p "$BIN" "$APPS"

say()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(uname -m)" = aarch64 ] || warn "$(t "These tweaks target the Steam Frame (aarch64); you're on %s." "$(uname -m)")"

# The user systemd/D-Bus env can be missing in nested desktop-mode shells.
XDG_RUNTIME_DIR_USER="/run/user/$(id -u)"
export XDG_RUNTIME_DIR_USER
sysctl_user() {
    XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR_USER" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR_USER/bus" \
    systemctl --user "$@"
}
# busctl --user on the same bus as sysctl_user: the VR session's, also from desktop mode, whose
# own bus (nested Plasma's) is another.
busctl_user() {
    XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR_USER" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR_USER/bus" \
    busctl --user "$@"
}
# systemd-run --user through the same bus as sysctl_user (desktop mode's XDG_RUNTIME_DIR,
# /run/user/<uid>/nested_plasma, has no systemd in it). Give the program its environment with
# --setenv (session_env_args): what this prefix sets is systemd-run's own, not the program's.
systemd_run_user() {
    XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR_USER" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR_USER/bus" \
    systemd-run --user "$@"
}
# units_usable: systemd-run is there and the user's service manager answers (not in a container
# or a sandbox without one, as in the tests and dev/fresh-install.sh).
units_usable() { command -v systemd-run >/dev/null && sysctl_user show-environment >/dev/null 2>&1; }

# The caller's session, for a program run as a unit: a unit gets the user manager's environment,
# which is the Steam session's (DISPLAY=:0, /run/user/<uid>), not desktop mode's (its own
# XDG_RUNTIME_DIR with its Wayland socket, DISPLAY=:2, XAUTHORITY, and its own D-Bus for
# notifications and the tray). Each is passed as the caller has it; the display variables the
# caller doesn't have are unset in the unit too, so a program started from VR doesn't find
# DISPLAY=:0 and one from desktop mode doesn't pick up the Steam session's leftovers.
FT_SESSION_ENV=(WAYLAND_DISPLAY DISPLAY XAUTHORITY XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS
                XDG_SESSION_TYPE XDG_CURRENT_DESKTOP XDG_DATA_DIRS XDG_CONFIG_DIRS PATH TERM COLORTERM
                LANG LANGUAGE LC_ALL LC_CTYPE LC_MESSAGES LC_NUMERIC LC_TIME LC_COLLATE LC_MONETARY
                FRAME_TWEAKS_LANGUAGE FRAME_TWEAKS_LANG_RESOLVED FRAME_TWEAKS_LIB)
FT_SESSION_UNSET=(WAYLAND_DISPLAY DISPLAY XAUTHORITY)
# session_env_args: those as systemd-run options, in the array SESSION_ENV_ARGS.
session_env_args() {
    local v
    SESSION_ENV_ARGS=()
    for v in "${FT_SESSION_ENV[@]}"; do
        if [ -n "${!v+x}" ]; then SESSION_ENV_ARGS+=("--setenv=$v=${!v}")
        elif [[ " ${FT_SESSION_UNSET[*]} " == *" $v "* ]]; then SESSION_ENV_ARGS+=(-p "UnsetEnvironment=$v"); fi
    done
}

# run_unit TWEAK NAME [--memory SIZE] [--tasks N] -- COMMAND...: start a tweak's long-running
# program as a transient user service, ft-TWEAK-NAME (NAME: letters and digits, no "-", so
# stop_units can tell ft-vr-x, tweak vr, from ft-vr-dashboard-x). Its own cgroup gives it a memory
# limit (MemoryMax, 800M unless --memory; MemorySwapMax so it can't grow on in swap instead),
# TasksMax, no way to gain privileges (no sudo or setuid helper from inside it: don't use this for
# a program that needs one), and stopping the unit stops whatever it started too (an orphan used
# to keep running after setsid -f, and only processes: patterns found it). In app-ft.slice,
# inside app.slice, where VR memory guard's limit for apps applies (as app-ftmirror.slice).
# Its output goes to the journal (journalctl --user -u ft-TWEAK-NAME).
# Returns 3, starting nothing, when that unit is running already: the caller decides (hand the
# program a "toggle", say). Without a usable systemd (units_usable), the program is started as
# before: setsid -f, in the background.
run_unit() {
    local tweak=${1:-} name=${2:-} mem=800M tasks=128 unit
    shift 2 || die "run_unit TWEAK NAME [--memory SIZE] [--tasks N] -- COMMAND..."
    while [ $# -gt 0 ]; do
        case $1 in
            --memory) mem=$2; shift 2 ;;
            --tasks) tasks=$2; shift 2 ;;
            --) shift; break ;;
            *) die "run_unit: unknown option $1" ;;
        esac
    done
    [ $# -gt 0 ] || die "run_unit: no command"
    [[ $tweak =~ ^[a-z0-9][a-z0-9-]*$ && $name =~ ^[a-z0-9]+$ ]] || die "run_unit: bad name ft-$tweak-$name"
    unit="ft-$tweak-$name"
    if ! units_usable; then
        (cd "$HOME" && setsid -f "$@" >/dev/null 2>&1 </dev/null)
        return 0
    fi
    sysctl_user is-active --quiet "$unit.service" && return 3
    # (one that failed and was not collected yet would make systemd-run refuse the name)
    sysctl_user reset-failed "$unit.service" >/dev/null 2>&1 || true
    session_env_args
    # IgnoreSIGPIPE=no: as when started from a shell (a service ignores SIGPIPE by default, and a
    # program writing to a closed pipe then gets errors it never expected instead of ending).
    systemd_run_user --quiet --collect --unit="$unit" --slice=app-ft.slice \
        --working-directory="$HOME" \
        -p MemoryMax="$mem" -p MemorySwapMax=256M -p TasksMax="$tasks" \
        -p NoNewPrivileges=yes -p KillMode=control-group -p IgnoreSIGPIPE=no \
        "${SESSION_ENV_ARGS[@]}" -- "$@"
}

# stop_units TWEAK: stop the tweak's run_unit programs (ft-TWEAK-NAME); true if there were any.
stop_units() {
    local tweak=$1 u found=()
    units_usable || return 1
    # (grep: a failed unit's line starts with a "●")
    while read -r u; do
        # (ft-TWEAK-NAME exactly: NAME has no "-", so tweak vr's glob leaves vr-dashboard's units)
        [[ ${u%-*} == "ft-$tweak" ]] && found+=("$u")
    done < <(sysctl_user list-units --all --plain --no-legend --type=service "ft-$tweak-*" 2>/dev/null |
             grep -o 'ft-[a-z0-9-]*\.service')
    [ ${#found[@]} -gt 0 ] || return 1
    sysctl_user stop "${found[@]}" 2>/dev/null || true
    return 0
}

BREW=/home/linuxbrew/.linuxbrew/bin/brew
# brew_cmd NAME: the path of a command on PATH or in Homebrew (which a status check's PATH may
# not have); fails without it.
brew_cmd() { command -v "$1" 2>/dev/null || { [ -x "${BREW%/brew}/$1" ] && echo "${BREW%/brew}/$1"; }; }

# ask <question>: yes/no in the terminal, or a dialog when there's no terminal. [y/N] is in the
# reader's language, its first letter that language's yes ([s/N], [o/N], [j/N]): an answer starting
# with it counts as yes, and so does y in every language (wallet-tool's yes() does the same).
ask() {
    if [ -t 0 ]; then
        local a keys mine; keys=$(t '[y/N]'); mine=${keys:1:1}
        read -rp "$1 $keys " a
        [[ ${a,,} == y* || ( -n $mine && ${a,,} == "${mine,,}"* ) ]]
    elif command -v kdialog >/dev/null && [ -n "${WAYLAND_DISPLAY:-${DISPLAY:-}}" ]; then
        kdialog --title "Frame Tweaks" --yesno "$1"
    else
        return 1
    fi
}

# drop_sudo: forget the sudo password just typed (sudo -k), right after the step it was asked for:
# sudo would otherwise let anything run from the same terminal in the next minutes use it without
# asking (what this tweak runs next, the next tweak in the same run, whatever it starts). Never
# asks; nothing happens if sudo wasn't used.
drop_sudo() { if command -v sudo >/dev/null; then sudo -k 2>/dev/null || true; fi; }

# need_brew: make sure Homebrew is available, offering to install it if it isn't.
# user_has_password: whether your user has a password, which sudo needs. A new Frame's user has
# none (set one with passwd). False only when passwd says so (NP); when it can't tell, true, and
# sudo says for itself.
user_has_password() { ! passwd -S "$USER" 2>/dev/null | grep -q '^[^ ]* NP '; }
no_password_how() { t "Set one: open a terminal (Konsole), type passwd and press Enter, then choose a password (nothing shows as you type it). Or use Set a password… in the Frame Tweaks window."; }

need_brew() {
    if command -v brew >/dev/null || [ -x "$BREW" ]; then
        eval "$("${BREW_BIN:-$(command -v brew || echo "$BREW")}" shellenv)"
        return 0
    fi
    printf '\n%s\n' "$(t "This tweak needs Homebrew, a package manager that installs into /home/linuxbrew.
That folder is outside SteamOS's system partition, so updates don't remove it.
Homebrew's installer asks for your sudo (admin) password once, to create that folder.")"
    user_has_password || die "$(t "Your user has no password yet, so sudo can't work.") $(no_password_how)"
    ask "$(t 'Install Homebrew now?')" || die "$(t 'Homebrew is required for this tweak. Install it from https://brew.sh and re-run.')"
    # Homebrew's installer at a pinned commit, checked against homebrew/pin's hash before it runs.
    # (Downloaded first, so the password is asked for just before it runs, and forgotten as soon
    # as it ends: drop_sudo.)
    local brew_installer ok=1; brew_installer=$(mktemp)
    fetch_pinned homebrew "$brew_installer"
    sudo -v || { rm -f "$brew_installer"; die "$(t 'sudo failed.')"; }
    NONINTERACTIVE=1 /bin/bash "$brew_installer" || ok=
    drop_sudo
    rm -f "$brew_installer"
    [ -n "$ok" ] || die "$(t "Homebrew's installer failed (see above).")"
    [ -x "$BREW" ] || die "$(t "Homebrew didn't end up in /home/linuxbrew.")"
    # shellcheck disable=SC2016   # (single quotes on purpose: .bashrc expands it when it runs, not now)
    grep -qs 'linuxbrew/bin/brew shellenv' "$HOME/.bashrc" ||
        append_line "$HOME/.bashrc" 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"'
    ensure_path                          # (~/.local/bin ahead of Homebrew's bin again: see there)
    eval "$("$BREW" shellenv)"
    say "$(t 'Homebrew installed.')"
}

# Before 0.5 a few files lived under the project's old name, and before 0.6 some settings sat
# loose in ~/.config: move them (once; install.sh runs it, and those programs check themselves).
migrate_legacy_dirs() {
    local old="$HOME/.config/steam-frame-tweaks" f
    if [ -d "$old" ]; then
        mkdir -p "$HOME/.config/frame-tweaks/installer"
        [ -f "$old/channel" ] && mv -n "$old/channel" "$HOME/.config/frame-tweaks/channel"
        for f in "$old"/*; do [ -e "$f" ] && mv -n "$f" "$HOME/.config/frame-tweaks/installer/"; done
        rmdir "$old" 2>/dev/null || true
    fi
    # (0.6: the phone mirror's and dictation's settings joined them)
    for f in phone dictate; do
        if [ -f "$HOME/.config/$f.conf" ] && [ ! -e "$HOME/.config/frame-tweaks/$f.conf" ]; then
            mkdir -p "$HOME/.config/frame-tweaks" && mv "$HOME/.config/$f.conf" "$HOME/.config/frame-tweaks/$f.conf"
        fi
    done
    old="$HOME/.local/state/steam-frame-tweaks"
    if [ -d "$old" ]; then
        mkdir -p "$HOME/.local/state/frame-tweaks"
        # (sft-dashboard-restore stays while a SteamVR stop hook still names it there)
        if ! grep -qs "$old/sft-dashboard-restore" "$HOME/.config/systemd/user/steamvr.service.d/"*.conf; then
            rm -f "$old/sft-dashboard-restore"
        fi
        for f in "$old"/*; do
            [ -e "$f" ] && [ "${f##*/}" != sft-dashboard-restore ] && mv -n "$f" "$HOME/.local/state/frame-tweaks/"
        done
        rmdir "$old" 2>/dev/null || true
    fi
    return 0
}

# append_line FILE LINE: LINE at the end of FILE, on a line of its own (appended to a file whose
# last line has no newline, it was glued onto that line).
append_line() {
    [ ! -s "$1" ] || [ -z "$(tail -c1 "$1")" ] || echo >> "$1"
    printf '%s\n' "$2" >> "$1"
}

# Make sure ~/.local/bin is on PATH for terminals and the desktop session, ahead of Homebrew's
# bin: the wallet's gh wrapper lives in ~/.local/bin and the real gh in Homebrew, and `brew
# shellenv` puts Homebrew's bin first. With its line below ours in ~/.bashrc, terminals ran
# Homebrew's gh, which saved its token in plain text; ours goes last.
ensure_path() {
    # (the file itself: write_file on a link from a dotfiles repo would replace the link)
    local rc line='export PATH="$HOME/.local/bin:$PATH"'
    rc=$(readlink -f "$HOME/.bashrc" 2>/dev/null) && [ -n "$rc" ] || rc=$HOME/.bashrc
    if ! grep -qs 'HOME/.local/bin' "$rc"; then
        append_line "$rc" "$line"
    elif [ "$(grep -nxF "$line" "$rc" | tail -1 | cut -d: -f1)" -lt "$(grep -n 'brew shellenv' "$rc" | tail -1 | cut -d: -f1)" ] 2>/dev/null; then
        grep -vxF "$line" "$rc" | write_file "$rc"       # (only our own line moves; one of yours stays)
        append_line "$rc" "$line"
    fi
    mkdir -p "$HOME/.config/environment.d"
    [ -f "$HOME/.config/environment.d/10-local-bin.conf" ] ||
        echo 'PATH=$HOME/.local/bin:$PATH' > "$HOME/.config/environment.d/10-local-bin.conf"
}

# alarm_fetch <repo> <pkgname> <dest-dir>
# Download the current Arch Linux ARM package <pkgname> and extract it into <dest-dir>.
# SteamOS is Arch-based, so ALARM aarch64 binaries run as-is.
alarm_fetch() {
    # Newest <name> package from Arch Linux ARM, verified against ALARM's build key (shipped in
    # lib/keys, fingerprint 68B3537F39A313B3E574D06777193F152BDBE6A6) before it's unpacked.
    # (Over HTTPS only, redirects included: --proto.)
    local repo=$1 name=$2 dest=$3 file t mirror https=(--proto '=https' --proto-redir '=https')
    for mirror in "$ALARM_MIRROR" $ALARM_FALLBACK; do
        file=$(curl "${https[@]}" -fsSL --max-time 20 "$mirror/$repo/" |
            grep -oE "\"$name-[0-9][^\"/]*-aarch64\.pkg\.tar\.(xz|zst)\"" | tr -d '"' | sort -V | tail -1) || true
        [ -n "$file" ] && break
    done
    [ -n "$file" ] || die "package $name not found in ALARM $repo"
    say "$(t 'Fetching %s' "$file")"
    t=$(mktemp -d)
    curl "${https[@]}" -fsSL -o "$t/$file" "$mirror/$repo/$file" &&
        curl "${https[@]}" -fsSL -o "$t/$file.sig" "$mirror/$repo/$file.sig" ||
        { rm -rf "$t"; die "download of $file failed"; }
    gpgv --keyring "$REPO_DIR/lib/keys/archlinuxarm.gpg" "$t/$file.sig" "$t/$file" 2>/dev/null ||
        { rm -rf "$t"; die "$file: bad or missing Arch Linux ARM signature; not installing it"; }
    # The signature proves ALARM built it, not that it's the package asked for, for this Frame, or
    # not an older one: check the signed package's own name and architecture (aarch64, or any),
    # and refuse a version older than the last one installed (a mirror replaying an old,
    # vulnerable build) or, on a first install too, than the one this release was tested with
    # (lib/tested-versions). ALARM_ALLOW_DOWNGRADE=1 overrides the version checks.
    local info got arch ver tested seen="$HOME/.local/state/frame-tweaks/alarm/$name"
    info=$(bsdtar -xOf "$t/$file" .PKGINFO 2>/dev/null) || true
    got=$(sed -n 's/^pkgname = //p' <<<"$info"); ver=$(sed -n 's/^pkgver = //p' <<<"$info")
    arch=$(sed -n 's/^arch = //p' <<<"$info")
    [ "$got" = "$name" ] || { rm -rf "$t"; die "$file: contains package '$got', not $name; not installing it"; }
    [ "$arch" = aarch64 ] || [ "$arch" = any ] ||
        { rm -rf "$t"; die "$(t "%s is built for '%s', not aarch64; not installing it" "$file" "$arch")"; }
    tested=$(sed -n "s/^$name=//p" "$REPO_DIR/lib/tested-versions" 2>/dev/null) || true
    if [ "${ALARM_ALLOW_DOWNGRADE:-}" != 1 ]; then
        if [ -f "$seen" ] && [ "$(vercmp "$ver" "$(cat "$seen")")" -lt 0 ]; then
            rm -rf "$t"; die "$name $ver is older than the $(cat "$seen") installed before; not installing it"
        fi
        if [ -n "$tested" ] && [ "$(vercmp "$ver" "$tested")" -lt 0 ]; then
            rm -rf "$t"; die "$(t '%s %s is older than the %s this release was tested with; not installing it' "$name" "$ver" "$tested")"
        fi
    fi
    mkdir -p "$(dirname "$seen")" && printf '%s\n' "$ver" > "$seen"
    mkdir -p "$dest"
    bsdtar -xf "$t/$file" -C "$dest"
    rm -rf "$t"
}

# runs_here <binary> [library-dir]: whether the system can load it (ldd finds every library,
# at a recent enough version). A newer Arch Linux ARM build can need a newer glibc or library
# than SteamOS has; installers then keep the copy that works. Prints what's missing. (For a
# program linked to libraries, as every one installed this way is: one ldd can't load at all,
# "not a dynamic executable" (a build for another architecture, say), doesn't run here either.)
runs_here() {
    local out missing=
    out=$(LD_LIBRARY_PATH="${2:-}${2:+${LD_LIBRARY_PATH:+:}}${LD_LIBRARY_PATH:-}" ldd "$1" 2>&1) || missing=${out:-ldd failed}
    [ -n "$missing" ] || missing=$(grep 'not found' <<<"$out" || true)
    [ -z "$missing" ] || { sed 's/^[[:space:]]*//' <<<"$missing" | paste -sd ';' -; return 1; }
}

# fetch_pinned <id> <out-file> [pin-name]: download <id>/pin's (or <id>/<pin-name>'s) url and
# check it against the hash recorded in the pin (not one fetched alongside it), so a changed
# upstream file is refused. If upstream's file is gone or changed, the pin's mirror= is used:
# Frame Tweaks' own copy (an asset of this repo's "mirror" release, dev/mirror-pins.sh),
# checked against the same hash.
fetch_pinned() {
    local pin url sha mirror
    pin="$(tweak_dir "$1")/${3:-pin}"
    url=$(sed -n 's/^url=//p' "$pin"); sha=$(sed -n 's/^sha256=//p' "$pin"); mirror=$(sed -n 's/^mirror=//p' "$pin")
    if curl -fL# -o "$2" "$url" && sha_ok "$sha" "$2"; then return 0; fi
    [ -n "$mirror" ] || die "$(basename "$url"): download failed, or it differs from the pinned file; not installing it"
    warn "$(basename "$url") isn't available unchanged from upstream; using Frame Tweaks' copy"
    fetch_mirror "$mirror" "$sha" "$2"
}
# fetch_mirror <url> <sha256> <out-file>: Frame Tweaks' copy of a pinned file, checked
fetch_mirror() {
    { curl -fL# -o "$3" "$1" && sha_ok "$2" "$3"; } ||
        die "$(basename "$1"): Frame Tweaks' copy failed too (download or checksum); not installing it"
}
# Translations for installed programs (they don't run from this folder): lib/i18n.py, lib/i18n.sh
# and locale/*.po in ~/.local/share/frame-tweaks/i18n. A Python program adds that folder to
# sys.path and imports _ from i18n; a bash program sources its i18n.sh (see arrowpad, adb-scrcpy).
# (and the Python modules the programs share: lib/ftconf.py, settings files and logs; lib/vrkit.py,
# SteamVR poses, grips and haptics; lib/needs.py, "this needs a tweak that isn't installed";
# lib/xkb.py, keys on the desktop's keyboard layout)
# (a drop-in translation, ~/.config/frame-tweaks/locale, isn't copied: lib/i18n.py reads it
# from there in every program, so one saved there counts at once, without an install)
SHARED_LIB=(i18n.py i18n.sh ftconf.py vrkit.py needs.py xkb.py menuedits.py tooltips.py)
install_i18n() {
    local d="$HOME/.local/share/frame-tweaks/i18n"
    mkdir -p "$d/locale"
    install -m644 "${SHARED_LIB[@]/#/$REPO_DIR/lib/}" "$d/"
    find "$d/locale" -name '*.po' -delete
    find "$REPO_DIR/locale" -maxdepth 1 -name '*.po' -exec install -m644 -t "$d/locale" {} +
}
# shared_current: the copies install_i18n made are those of this checkout (files and translations).
shared_current() {
    local d="$HOME/.local/share/frame-tweaks/i18n" f
    for f in "${SHARED_LIB[@]}"; do cmp -s "$REPO_DIR/lib/$f" "$d/$f" || return 1; done
    for f in "$REPO_DIR"/locale/*.po; do [ -e "$f" ] || continue; cmp -s "$f" "$d/locale/${f##*/}" || return 1; done
    return 0
}
# (a file not there yet is no match, quietly: sha256sum said "FAILED open or read" for each, on stdout)
sha_ok() { [ -n "$1" ] && [ -f "$2" ] && echo "$1  $2" | sha256sum -c --quiet - >/dev/null 2>&1; }
# settings_applied: the settings this tweak's Apply applies (its manifest's settings: actions: keys:)
# are applied now, as chosen: its script says so at the end, from an install or the Apply button, and
# the window dims Apply until one of them changes (lib/sft.py record_applied).
settings_applied() {
    python3 "$REPO_DIR/lib/sft.py" settings-applied "$(basename "$TWEAK_DIR")" >/dev/null 2>&1 || true
}
# settings_unapplied: its uninstall says nothing of it is applied any more (the record goes).
settings_unapplied() {
    python3 "$REPO_DIR/lib/sft.py" settings-applied --forget "$(basename "$TWEAK_DIR")" >/dev/null 2>&1 || true
}
# newest_tag: the newest release tag from the tag names on stdin. Stable (vX.Y.Z) only, unless
# the channel is beta (FRAME_TWEAKS_CHANNEL=beta, or "beta" in ~/.config/frame-tweaks/channel),
# which adds pre-releases (vX.Y.Z-rc1) ranked below their final version.
release_channel() {
    local c=${FRAME_TWEAKS_CHANNEL:-}
    [ -n "$c" ] || c=$(cat "$HOME/.config/frame-tweaks/channel" 2>/dev/null || true)
    [ "$c" = beta ] && echo beta || echo stable
}
newest_tag() {
    local pattern='^v[0-9]+\.[0-9]+\.[0-9]+$'
    [ "$(release_channel)" = beta ] && pattern='^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$'
    grep -E "$pattern" | rank_tags | tail -1
}
rank_tags() { sed 's/-/~/' | sort -V | sed 's/~/-/'; }      # oldest first; vX.Y.Z-rc.N before vX.Y.Z
# tag_newer A B: release tag A is newer than B (ranked as newest_tag ranks them)
tag_newer() { [ "$1" != "$2" ] && [ "$(printf '%s\n%s\n' "$1" "$2" | rank_tags | tail -1)" = "$1" ]; }
pin_version() { sed -n 's/^version=//p' "$(tweak_dir "$1")/pin"; }

# Steam's "+" menu resolves Icon= only in the hicolor theme and rescans when the
# applications/icon directories' mtime changes (writing an existing file doesn't change it).
ICONS="$HOME/.local/share/icons/hicolor"
LAUNCHER_ORIGINALS="$HOME/.local/share/frame-tweaks/launcher-originals"
LAUNCHER_BUILT="$HOME/.local/share/frame-tweaks/launcher-built"     # (wallet-launcher's wrappers as it built them)
MENU_BUILT="$HOME/.local/share/frame-tweaks/menu-built"     # (install_desktop's entries as it wrote them)

# install_icon <name>: <name>.png from the tweak's folder (or the repo's icons/) into hicolor
# (256x256).
install_icon() {
    local src="$TWEAK_DIR/$1.png"
    [ -f "$src" ] || src="$REPO_DIR/icons/$1.png"
    mkdir -p "$ICONS/256x256/apps"
    install -m644 "$src" "$ICONS/256x256/apps/$1.png"
    touch "$ICONS"
}

# install_desktop <file.desktop>: copy into the app menu, expanding @BIN@. What you've changed in
# the entry since it was last written (a new name or icon from KDE's menu editor) goes into the
# new version (lib/menuedits.py: menu-built keeps each entry as written). If the entry is
# wrapped by wallet-launcher (shared wallet / password gate), the new version becomes the
# wrapper's original and the wrapper is re-applied, so the gate isn't silently dropped.
# remove_desktop <file.desktop>...: install_desktop's undo: the entry, the copy of it as written
# and those kept while wallet-launcher wraps it (launcher-originals, launcher-built), then the
# menu refreshed. Not on a reinstall (↻, FRAME_TWEAKS_REINSTALL): install_desktop, next, then
# re-applies the wrapper to the new version.
# (Without the kept copy it wrote a plain entry: the password gate was gone.)
remove_desktop() {
    [ -z "${FRAME_TWEAKS_REINSTALL:-}" ] || return 0
    local name
    for name in "$@"; do
        remove_files "$APPS/$name" "$MENU_BUILT/$name" "$LAUNCHER_ORIGINALS/$name" "$LAUNCHER_BUILT/$name"
    done
    update-desktop-database "$APPS" 2>/dev/null || true
    touch "$APPS" 2>/dev/null || true
}

# remove_icon <name>: install_icon's undo.
remove_icon() {
    remove_files "$ICONS/256x256/apps/$1.png"
    touch "$ICONS" 2>/dev/null || true
}

install_desktop() {
    local name entry mine; name=$(basename "$1")
    # (with its name and comment in each translated language: lib/i18n.py desktop. Made first, then
    # written whole, in English if translating it fails: piped straight in, a failure there left
    # the entry empty, and the tweak's install stopped.)
    entry=$(sed "s|@BIN@|$BIN|g" "$1" | python3 "$REPO_DIR/lib/i18n.py" desktop) && [ -n "$entry" ] ||
        entry=$(sed "s|@BIN@|$BIN|g" "$1")
    if [ -f "$LAUNCHER_ORIGINALS/$name" ] && [ -x "$BIN/wallet-launcher" ]; then
        printf '%s\n' "$entry" | write_file "$LAUNCHER_ORIGINALS/$name"
        "$BIN/wallet-launcher" --reapply "${name%.desktop}" >/dev/null     # (keeps your edits itself)
    else
        mine=$(printf '%s\n' "$entry" | python3 "$REPO_DIR/lib/menuedits.py" keep "$APPS/$name" "$MENU_BUILT/$name") &&
            [ -n "$mine" ] || mine=$entry
        printf '%s\n' "$mine" | write_file "$APPS/$name"
    fi
    printf '%s\n' "$entry" | write_file "$MENU_BUILT/$name"
    update-desktop-database "$APPS" 2>/dev/null || true
    touch "$APPS"
    # (its name in the keyboard's language, as for every entry: install.sh ensure_menu_language)
    sysctl_user start --no-block frame-tweaks-menus.service 2>/dev/null || true
}

# pip_pinned <venv> <package>...: install at the tested versions (lib/python-constraints.txt),
# tried twice (a dropped connection). A tested version these packages need that PyPI has no build
# of for this Python and system (say, after a SteamOS update moved Python on) is replaced by the
# newest that has one, with a warning: working beats exact. Only that one: the other tested
# versions stay. Not when PyPI couldn't be reached, nor when that version is gone from PyPI (a
# hijacked account could delete it, to have its own newer one taken), nor for any other failure:
# then it fails, and says which.
pip_pinned() {
    local venv=$1 quiet=(-q) tmp pin name code why=other needs=() missing=() cons="$REPO_DIR/lib/python-constraints.txt"
    shift
    # (FRAME_TWEAKS_PIP_PROGRESS: show pip's download progress, for a setup someone is watching)
    [ -z "${FRAME_TWEAKS_PIP_PROGRESS:-}" ] || quiet=()
    # (pip's messages are kept to tell why it failed; these are its words for a connection lost,
    # refused or failing)
    local offline='Retrying \(Retry|[Cc]onnection|timed out|name resolution|[Uu]nreachable|SSL|[Pp]roxy|[Mm]ax retries'
    offline+='|not enough bytes|[Ii]ncomplete|HTTP error|Server Error'
    tmp=$(mktemp -d)
    for _ in 1 2; do
        if "$venv/bin/pip" install "${quiet[@]}" -c "$cons" "$@" 2>"$tmp/said"; then
            cat "$tmp/said" >&2; rm -rf "$tmp"; return 0
        fi
        cat "$tmp/said" >&2
    done
    # Not the connection? Then which tested versions do these need (pip resolves them, at the
    # newest, as built packages: the kind that install here), and has PyPI no build of one here?
    # Asked for each on its own, pip lists the versions it has instead, or names the Python one needs.
    if grep -qE "$offline" "$tmp/said"; then why=offline
    elif "$venv/bin/pip" install -q --dry-run --ignore-installed --only-binary :all: --report "$tmp/needs" "$@" \
            >/dev/null 2>"$tmp/said"; then
        mapfile -t needs < <("$venv/bin/python" -c 'import json, re, sys
n = lambda s: re.sub(r"[-_.]+", "-", s).lower()
got = {n(p["metadata"]["name"]) for p in json.load(open(sys.argv[1]))["install"]}
for pin in open(sys.argv[2]).read().split("\n"):
    if "==" in pin and not pin.startswith("#") and n(pin.split("==")[0]) in got: print(pin)' "$tmp/needs" "$cons")
        why=
        for pin in "${needs[@]}"; do
            "$venv/bin/pip" install -q --dry-run --no-deps --only-binary :all: "$pin" >/dev/null 2>"$tmp/said" && continue
            if grep -qiE '\(from versions: [0-9]|Requires-Python|requires? a different python' "$tmp/said"; then
                missing+=("$pin")
            else
                why=other; grep -qE "$offline" "$tmp/said" && why=offline; break
            fi
        done
        [ ${#missing[@]} -gt 0 ] || why=${why:-other}
    elif grep -qE "$offline" "$tmp/said"; then why=offline
    fi
    # Still on PyPI? One that isn't was deleted: no reason to take another. (Nor if PyPI can't say.)
    for pin in "${missing[@]}"; do
        [ -z "$why" ] || break
        name=${pin%%==*}; name=${name,,}
        code=$(curl --proto '=https' --proto-redir '=https' -sL --max-time 30 --retry 2 -o /dev/null -w '%{http_code}' \
            "https://pypi.org/pypi/${name//[_.]/-}/${pin#*==}/json" 2>/dev/null) || true
        if [ "$code" = 404 ]; then why="gone $pin"; elif [ "$code" != 200 ]; then why=offline; fi
    done
    case $why in
        offline) warn "$(t "Couldn't reach PyPI to install %s: check the Internet connection, then try again." "$*")" ;;
        gone\ *) warn "$(t "%s, the tested version, is no longer on PyPI, so %s isn't installed: a deleted release isn't replaced by another one. Please report this." \
                     "${why#gone }" "$*")" ;;
        other) warn "$(t "Couldn't install %s (see above)." "$*")" ;;
        *) grep -vxF -f <(printf '%s\n' "${missing[@]}") "$cons" > "$tmp/cons" || true
           warn "$(t "PyPI has no build of %s for this Python (%s) and system; installing the newest %s that has one instead. The other tested versions stay." \
               "${missing[*]}" "$("$venv/bin/python" -V 2>&1)" "${missing[*]%%==*}")"
           if "$venv/bin/pip" install "${quiet[@]}" -c "$tmp/cons" "$@"; then rm -rf "$tmp"; return 0; fi ;;
    esac
    rm -rf "$tmp"; return 1
}

# new_venv DIR: a venv on SteamOS's own Python, whatever python3 comes first on the PATH: Homebrew
# brings its own (python@3.15, a dependency of the tweaks' formulae), newer than the pinned packages
# have builds for (onnxruntime 1.31 has none for 3.15: Parakeet's runtime couldn't install). A venv
# there on another Python, or one cut short, is made anew (--clear); FRAME_TWEAKS_PYTHON overrides.
new_venv() {
    local py=${FRAME_TWEAKS_PYTHON:-/usr/bin/python3}
    [ -x "$py" ] || py=python3
    "$py" -m venv --clear "$1"
}

# ---- a SteamOS build with another Python: the venvs moved to it (heal_venvs) -----------------
# A venv runs SteamOS's /usr/bin/python3 through a link, but its packages sit in
# lib/pythonX.Y/site-packages for the Python it was made with: when an update moves Python on
# (SteamOS 0.5.7's beta went from 3.12 to 3.14), every package is gone at once and each tool on
# the venv fails at its first import, its service restarting until systemd gives up. Their
# tweaks' manifests rightly say they survive SteamOS updates (all of it is in the home folder),
# so repair alone would leave them; heal_venvs runs first, there and at each login
# (frame-tweaks-heal.service).
system_python_version() {
    local py=${FRAME_TWEAKS_PYTHON:-/usr/bin/python3}
    [ -x "$py" ] || py=python3
    "$py" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null
}
# venv_python_version DIR: the X.Y its packages are for (its lib/pythonX.Y; pyvenv.cfg's version
# says the same, but the folder is what Python looks in). Nothing for no venv there.
venv_python_version() {
    local d
    [ -f "$1/pyvenv.cfg" ] || return 1
    for d in "$1"/lib/python3.*/site-packages; do
        [ -d "$d" ] || continue
        d=${d%/site-packages}; echo "${d##*/python}"; return 0
    done
    return 1
}
# venv_stale DIR: a venv there, made for another Python than SteamOS's now.
venv_stale() {
    local have now
    have=$(venv_python_version "$1") || return 1
    now=$(system_python_version) && [ -n "$now" ] || return 1
    [ "$have" != "$now" ]
}
# The venvs Frame Tweaks makes (a tweak's own folder of them: add it here).
ft_venvs() {
    printf '%s\n' "$TWEAKS_VENV" "$QT_VENV" "$HOME/.local/share/frame-tweaks/parakeet/venv"
}
# venv_lock DIR / venv_unlock: one setup of a venv at a time. The login service can be
# installing PyQt6 again (heal_venv, minutes over a slow connection) when the window opens and
# finds PyQt6 missing: without this its ensure_qt_venv made the venv anew (--clear) under the
# install going on. Whoever waited checks again, and finds it done. (The lock files sit in
# Frame Tweaks' state folder, named after the venv's path: none is left in a tweak's folder.)
venv_lock() {
    local d="${XDG_STATE_HOME:-$HOME/.local/state}/frame-tweaks/locks" name=${1%/}
    mkdir -p "$d" || return 1
    name=${name#/}
    exec {VENV_LOCK_FD}>"$d/venv-${name//\//_}.lock" && flock "$VENV_LOCK_FD"
}
venv_unlock() {
    [ -z "${VENV_LOCK_FD:-}" ] || exec {VENV_LOCK_FD}>&-
    VENV_LOCK_FD=
}
# heal_venv DIR: the venv made again on SteamOS's Python, with the packages it had. Moved over
# as they are when none has a compiled part tied to one Python (pure Python, or abi3 like PyQt6's:
# offline, in a second, at a login with no network yet); else installed again with pip_pinned at
# the tested versions. Either way each package must import afterwards.
heal_venv() {
    local rc
    venv_lock "$1" || return 1
    venv_stale "$1" && { heal_venv_locked "$1"; rc=$?; } || rc=0     # (healed meanwhile: nothing to do)
    venv_unlock
    return $rc
}
heal_venv_locked() {
    local venv=$1 site have tmp names=() mods=() d n m offline=1
    have=$(venv_python_version "$venv") || return 0
    site="$venv/lib/python$have/site-packages"
    # (the packages asked for, not what they pulled in: pip marks those REQUESTED)
    for d in "$site"/*.dist-info; do
        [ -f "$d/REQUESTED" ] || continue
        n=$(sed -n 's/^Name: *//p' "$d/METADATA" 2>/dev/null | head -1 | tr -d '\r')
        [ -n "$n" ] || continue
        case ${n,,} in pip|setuptools|wheel) continue ;; esac
        names+=("$n")
        if [ -f "$d/top_level.txt" ]; then
            while IFS= read -r m; do [ -n "$m" ] && mods+=("$m"); done < "$d/top_level.txt"
        else
            mods+=("${n//-/_}")
        fi
    done
    # (a compiled part for one Python: name.cpython-312-aarch64-linux-gnu.so; abi3 and pure ones move)
    find "$site" -name '*.cpython-3*.so' -print -quit 2>/dev/null | grep -q . && offline=
    tmp=$(mktemp -d "${venv%/}.heal.XXXXXX") || return 1
    mv "$site" "$tmp/site-packages" || { rm -rf "$tmp"; return 1; }
    if ! new_venv "$venv" >/dev/null; then
        warn "$(t "Couldn't make %s again on this Python." "$venv")"; rm -rf "$tmp"; return 1
    fi
    site="$venv/lib/python$(venv_python_version "$venv")/site-packages"
    if [ -n "$offline" ]; then
        for d in "$tmp/site-packages"/* "$tmp/site-packages"/.[!.]*; do
            [ -e "$d" ] || continue
            case ${d##*/} in pip|pip-*.dist-info|_distutils_hack|distutils-precedence.pth|setuptools|setuptools-*.dist-info) continue ;; esac
            rm -rf "${site:?}/${d##*/}"; mv "$d" "$site/"
        done
        find "$site" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
        if [ ${#mods[@]} -eq 0 ] || "$venv/bin/python" -c 'import importlib, sys
for m in sys.argv[1:]: importlib.import_module(m)' "${mods[@]}" 2>/dev/null; then
            rm -rf "$tmp"; return 0
        fi
        # (moved but not importing: start again, from PyPI)
        new_venv "$venv" >/dev/null || { rm -rf "$tmp"; return 1; }
    fi
    rm -rf "$tmp"
    [ ${#names[@]} -eq 0 ] || pip_pinned "$venv" "${names[@]}" || return 1
}
# heal_venvs: every stale venv of Frame Tweaks' healed, saying which (one line each); 1 if one
# couldn't be. Then the openvr bindings linked again to SteamVR's library (heal_venv moves the
# link with the package, but a reinstall makes the folder anew), and the tweaks' services on them
# started again (heal_units).
heal_venvs() {
    local venv bad=0 have now healed=()
    now=$(system_python_version)
    while IFS= read -r venv; do
        venv_stale "$venv" || continue
        have=$(venv_python_version "$venv")
        say "$(t 'SteamOS has Python %s now: moving %s from Python %s to it' "$now" "${venv/#$HOME/\~}" "$have")"
        if heal_venv "$venv"; then
            healed+=("$venv")
            "$venv/bin/python" -c 'import importlib.util,sys; sys.exit(0 if importlib.util.find_spec("openvr") else 1)' 2>/dev/null &&
                { ensure_openvr "$venv" || true; }
        else
            warn "$(t "%s couldn't be moved to Python %s: ./install.sh repair tries again." "${venv/#$HOME/\~}" "$now")"; bad=1
        fi
    done < <(ft_venvs)
    [ ${#healed[@]} -eq 0 ] || heal_units "${healed[@]}"
    return $bad
}
# heal_units VENV...: the user services whose program runs on one of these venvs (its #! line),
# out of their failed or restarting state: started again where what starts them runs (a
# WantedBy= that's active: default.target at a login, steamvr.service while SteamVR runs).
heal_units() {
    local f unit prog line wanted venv on
    for f in "$HOME"/.config/systemd/user/*.service; do
        [ -f "$f" ] || continue
        prog=$(sed -n 's/^ExecStart=[-@+!]*//p' "$f" | head -1); prog=${prog%% *}
        prog=${prog/#%h/$HOME}
        [ -f "$prog" ] || continue
        IFS= read -r line < "$prog" || continue
        on=
        for venv in "$@"; do [[ $line == "#!$venv/bin/python"* ]] && on=1; done
        [ -n "$on" ] || continue
        unit=${f##*/}
        sysctl_user reset-failed "$unit" 2>/dev/null || true
        if sysctl_user is-active --quiet "$unit" ||
           [ "$(sysctl_user show -p SubState --value "$unit" 2>/dev/null)" = auto-restart ]; then
            sysctl_user restart --no-block "$unit" 2>/dev/null || true
            continue
        fi
        sysctl_user is-enabled --quiet "$unit" 2>/dev/null || continue
        for wanted in $(sed -n 's/^WantedBy=//p' "$f"); do
            if sysctl_user is-active --quiet "$wanted" 2>/dev/null; then
                sysctl_user start --no-block "$unit" 2>/dev/null || true; break
            fi
        done
    done
}

# Shared venv for the small Python tools that talk D-Bus (jeepney, pure Python).
TWEAKS_VENV="$HOME/.local/share/frame-tweaks/venv"
# ensure_qt_venv [TITLE [DETAILS]]: PyQt6 in QT_VENV (~280 MB, shared by Arrow Pad, Screen snip,
# the NordVPN tray and the installer window), saying what it is as it starts; fails if it couldn't
# be installed. TITLE is short (the splash's status bar shows it; DETAILS go on the next line), and
# says nothing of how long it takes: that's the user's Internet connection. (QtWidgets, not just
# PyQt6: a setup cut short can leave PyQt6 there without the parts the window needs.)
ensure_qt_venv() {
    local rc=0
    "$QT_VENV/bin/python" -c 'import PyQt6.QtWidgets' 2>/dev/null && return 0
    venv_lock "$QT_VENV" || return 1
    if ! "$QT_VENV/bin/python" -c 'import PyQt6.QtWidgets' 2>/dev/null; then     # (not made meanwhile)
        say "${1:-$(t 'Setting up PyQt6, a window toolkit')}"
        echo "    ${2:-$(t 'About 280 MB to download, shared by the installer window and the tweaks that use it.')}"
        new_venv "$QT_VENV" && pip_pinned "$QT_VENV" PyQt6; rc=$?
    fi
    venv_unlock
    return $rc
}

ensure_tweaks_venv() {
    local rc=0
    "$TWEAKS_VENV/bin/python" -c 'import jeepney' 2>/dev/null && return 0
    venv_lock "$TWEAKS_VENV" || return 1
    if ! "$TWEAKS_VENV/bin/python" -c 'import jeepney' 2>/dev/null; then
        say "$(t 'Creating Python venv with jeepney')"
        new_venv "$TWEAKS_VENV"
        pip_pinned "$TWEAKS_VENV" jeepney; rc=$?
    fi
    venv_unlock
    return $rc
}

# ensure_openvr <venv>: the openvr bindings in that venv, on SteamVR's own arm64 library (the
# wheel only bundles an x86 one). Returns 1 (and changes nothing) without SteamVR's library.
VR_LIB=${FRAME_TWEAKS_VR_LIB:-/opt/steamvr/bin/linuxarm64/libopenvr_api.so}     # (another: for tests)
ensure_openvr() {
    [ -f "$VR_LIB" ] || return 1
    "$1/bin/python" -c 'import importlib.util,sys; sys.exit(0 if importlib.util.find_spec("openvr") else 1)' ||
        pip_pinned "$1" openvr
    local ovr
    ovr=$("$1/bin/python" -c 'import importlib.util,os; print(os.path.dirname(importlib.util.find_spec("openvr").origin))')
    ln -sf "$VR_LIB" "$ovr/libopenvr_api_64.so"
}

# install_py_tool <src> : install a Python tool into ~/.local/bin, running on the shared venv.
install_py_tool() {
    sed "1s|.*|#!$TWEAKS_VENV/bin/python|" "$1" | write_file "$BIN/$(basename "$1")" 755
}

# write_file <dest> [mode] < content: replace dest with stdin by renaming a finished copy over
# it (mode 644 unless given). Writing into the file instead would change it under anything
# running it: bash reads a script as it goes, so a wrapper being run could run half of each.
# (install -m and cp to a new name are fine; cp or > onto an existing program is not.)
write_file() {
    local dest=$1 tmp
    mkdir -p "$(dirname "$dest")"
    tmp=$(mktemp "$dest.new.XXXXXX") || return 1
    if cat > "$tmp" && chmod "${2:-644}" "$tmp" && mv -f "$tmp" "$dest"; then return 0; fi
    rm -f "$tmp"; return 1
}

# --- backups of user files a tweak changes -------------------------------------------------
# Never back up files that hold secrets in plain text (Signal's config.json before migration,
# gh's hosts.yml): a backup would recreate the leak the tweak removes.
BACKUPS="$HOME/.local/state/frame-tweaks/backups"

# backup_file <tweak> <file>: keep the file as it was before this tweak first changed it.
backup_file() {
    local dest="$BACKUPS/$1/${2#"$HOME"/}"
    [ -e "$dest" ] || [ -e "$dest.absent" ] && return 0
    mkdir -p "$(dirname "$dest")"
    if [ -e "$2" ]; then cp -p "$2" "$dest"; else : > "$dest.absent"; fi
}
# restore_file <tweak> <file>: put it back as it was (or remove it if it didn't exist).
restore_file() {
    local dest="$BACKUPS/$1/${2#"$HOME"/}"
    if [ -e "$dest" ]; then cp -p "$dest" "$2" && rm -f "$dest" && say "$(t 'restored %s' "$2")"
    elif [ -e "$dest.absent" ]; then rm -f "$2" "$dest.absent" && say "$(t "removed %s (it didn't exist before)" "$2")"
    fi
}
# KDE settings change key by key, so only those keys are recorded and restored (the rest of the
# file may have changed since):  save_kconfig <tweak> <file> <group> <key>...
save_kconfig() {
    local tweak=$1 file=$2 group=$3 key rec; shift 3
    rec="$BACKUPS/$tweak/kconfig"; mkdir -p "$(dirname "$rec")"
    for key in "$@"; do
        grep -qF "$file	$group	$key	" "$rec" 2>/dev/null && continue    # first value wins
        if kreadconfig6 --file "$file" --group "$group" --key "$key" --default "<unset>" | grep -qx "<unset>"; then
            printf '%s\t%s\t%s\t%s\n' "$file" "$group" "$key" "<unset>" >> "$rec"
        else
            printf '%s\t%s\t%s\t%s\n' "$file" "$group" "$key" "$(kreadconfig6 --file "$file" --group "$group" --key "$key")" >> "$rec"
        fi
    done
}
restore_kconfig() {
    local rec="$BACKUPS/$1/kconfig" file group key value
    [ -f "$rec" ] || return 0
    while IFS=$'\t' read -r file group key value; do
        if [ "$value" = "<unset>" ]; then kwriteconfig6 --file "$file" --group "$group" --key "$key" --delete
        else kwriteconfig6 --file "$file" --group "$group" --key "$key" -- "$value"; fi     # (--: a value like -1)
    done < "$rec"
    rm -f "$rec"; say "$(t 'restored KDE settings changed by %s' "$1")"
}

# clear_stuck_modifiers: make the desktop forget modifiers our virtual keyboard may have left
# "held" (a program that crashes while holding Ctrl/Alt/Super/Shift can't send the release, and
# the Steam session then adds it to every key). A release alone is dropped when the kernel
# already thinks the key is up, so each gets a full press+release; Super and Alt wrap F24 (bound
# to nothing) so the release isn't a lone tap that opens the app menu or a menu bar.
# Never Right Ctrl (97): in the nested desktop it toggles KWin's input grab ("Press right control
# to grab input"), which changes how windows and clicks behave. Nothing types Right Ctrl here.
CLEAR_MODIFIERS="42:1 42:0 54:1 54:0 29:1 29:0 56:1 194:1 194:0 56:0 125:1 194:1 194:0 125:0"
clear_stuck_modifiers() {
    [ -x "$BIN/ydotool" ] || return 0
    # shellcheck disable=SC2086   # (split on purpose: one ydotool argument per key event)
    YDOTOOL_SOCKET="/run/user/$(id -u)/.ydotool_socket" "$BIN/ydotool" key $CLEAR_MODIFIERS 2>/dev/null || true
}

# --- status.sh helpers: print one line, exit 0 = installed/OK, 1 = not installed, 2 = needs attention
status_ok()      { printf 'ok       %s\n' "$*"; exit 0; }
status_missing() { printf 'missing  %s\n' "$*"; exit 1; }
status_warn()    { printf 'warning  %s\n' "$*"; exit 2; }
# Installed, but SteamVR loads it only as it starts: needs attention (2), and the installer window
# offers to restart SteamVR on its row.
status_restart() { printf 'restart  %s\n' "$*"; exit 2; }
# Uninstalled, but SteamVR keeps running what it loaded as it started: not installed (1), and the
# installer window still offers to restart SteamVR on its row.
status_unload()  { printf 'restart  %s\n' "$*"; exit 1; }
# vr_started_before FILE: SteamVR's server runs and started before FILE last changed, so what was
# installed then (a driver, a setting it reads as it starts) isn't loaded yet.
vr_started_before() {
    local pid age
    [ -e "$1" ] && pid=$(pgrep -xo vrserver) && age=$(ps -o etimes= -p "$pid") || return 1
    [ $(( $(date +%s) - age )) -lt "$(stat -c %Y "$1")" ]
}

# remove_files <path>...: delete if present, saying what went. (With a menu entry, the copy of it
# as written goes too, unsaid: install_desktop's, for a tweak that removes its entry this way.)
remove_files() {
    local f
    for f in "$@"; do
        if [ -e "$f" ] || [ -L "$f" ]; then rm -rf -- "$f" && say "$(t 'removed %s' "$f")"; fi
        [[ $f != "$APPS"/*.desktop ]] || rm -f -- "$MENU_BUILT/${f##*/}"
    done
}

export QT_VENV="$HOME/.local/share/arrowpad/venv"   # PyQt6, shared by arrowpad and nordvpn-tray

# remove_qt_venv: QT_VENV is shared by Arrow Pad, Screen snip, the NordVPN tray and the full
# installer window (install.sh gui, which runs it as bin/sft-python): the last of them to go
# removes it. Kept on a reinstall (↻), rather than downloaded again. (Unticking one of them in
# the window used to delete the window's own Python while it ran.)
remove_qt_venv() {
    [ -z "${FRAME_TWEAKS_REINSTALL:-}" ] || return 0
    [ ! -e "$QT_VENV/bin/sft-python" ] || return 0
    local p
    for p in arrowpad frame-snip nordvpn-tray; do [ ! -x "$BIN/$p" ] || return 0; done
    remove_files "$QT_VENV"
}

# --- SteamVR dashboard patches (packs/core/vr-dashboard/) ---------------------------------------------
# A VR environment tweak is one patch file; vr-dashboard's watcher injects it while SteamVR runs.
VR_DASHBOARD="$HOME/.local/share/frame-tweaks/vr-dashboard"
install_dashboard_patch() {    # install_dashboard_patch NAME FILE
    [ -x "$VR_DASHBOARD/sft-dashboard" ] || "$(tweak_dir vr-dashboard)/install.sh" || return 1
    mkdir -p "$VR_DASHBOARD/patches"
    install -m644 "$2" "$VR_DASHBOARD/patches/$1.js"
    if sysctl_user is-active --quiet sft-dashboard.service; then
        # The watcher looks every 5 s: wait for it, so the status shown next is the real one.
        local _ s=
        for _ in 1 2 3 4 5 6 7 8 9 10; do
            s=$("$VR_DASHBOARD/sft-dashboard" status "$1" 2>/dev/null) || true
            [[ $s == *": patched" ]] && break
            sleep 1
        done
        # ("Active now." only once it is: it said so after these 10 looks either way. Otherwise what
        # the watcher says, "SteamVR changed (missing: …)" say.)
        if [[ $s == *": patched" ]]; then say "$(t 'Active now.')"
        else say "$(t 'Not active yet: %s' "${s:-$(t 'the dashboard patch service did not answer')}")"; fi
    elif sysctl_user is-active --quiet steamvr.service; then
        say "$(t 'Active from the next SteamVR start (reboot, or restart SteamVR from its menu).')"
    else
        say "$(t 'Active from the next SteamVR start.')"
    fi
}
remove_dashboard_patch() {     # remove_dashboard_patch NAME: the watcher stops it in the dashboard
    remove_files "$VR_DASHBOARD/patches/$1.js"
}
dashboard_patch_status() {     # dashboard_patch_status NAME OK-TEXT
    [ -f "$VR_DASHBOARD/patches/$1.js" ] || status_missing "$(t 'not installed')"
    sysctl_user is-active --quiet steamvr.service || status_ok "$(t 'installed (active while SteamVR runs)')"
    local s
    s=$(timeout 8 "$VR_DASHBOARD/sft-dashboard" status "$1" 2>/dev/null) || true
    case "$s" in
        *": patched") status_ok "$2" ;;
        *port*closed*) status_restart "$(t 'waiting for a SteamVR restart (restart SteamVR or reboot once)')" ;;
        *) status_warn "${s:-$(t 'not responding')}" ;;
    esac
}

# release_signed DIR TAG SIGNERS: TAG is SSH-signed by a key in the file SIGNERS. An SSH signature
# only (git checks a PGP or X.509 one against the user's own keyrings, not this file), on a tag
# that carries the name asked for (so an older signed release can't come back under a newer one's name).
release_signed() {
    [[ $(git -C "$1" for-each-ref --format='%(tag)' "refs/tags/$2" 2>/dev/null) == "$2" ]] &&
        git -C "$1" -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$3" -c gpg.program=false \
            -c gpg.x509.program=false verify-tag "refs/tags/$2" >/dev/null 2>&1
}

# release_trusted DIR TAG SIGNERS: TAG is signed by a key in SIGNERS, or its cosign-TAG is and
# points at the same commit. While an old release key is being retired, releases are signed with
# it (copies that know only that key accept nothing else) and cosigned with the new one: a copy
# that has the new key takes the cosign, without trusting the old key again.
release_trusted() {
    release_signed "$1" "$2" "$3" && return 0
    release_signed "$1" "cosign-$2" "$3" &&
        [[ $(git -C "$1" rev-parse -q --verify "refs/tags/cosign-$2^{commit}") == \
           $(git -C "$1" rev-parse -q --verify "refs/tags/$2^{commit}") ]]
}

# verify_release DIR TAG: the checkout DIR's release TAG is signed (or cosigned) by a key in
# dev/release-signers *as installed now* (so a tampered release can't bring its own key), as
# handed on by the releases in between: those newer than this copy's VERSION and older than TAG
# are walked oldest first, and one trusted so far hands on its own dev/release-signers. So a copy
# that skipped the release introducing a new key still gets there, and a key a release in between
# dropped isn't trusted for TAG. vX.Y.Z-bridge tags are skipped: they list an old key again, for
# copies from before cosigning (0.6.22), which have no other way to accept a release signed with it.
# Checkouts from before signing have no such file and skip this.
# FRAME_TWEAKS_ALLOW_UNSIGNED=1 overrides, for an emergency.
verify_release() {
    [[ -f $1/dev/release-signers ]] || return 0
    local signers; signers=$(mktemp)
    cp "$1/dev/release-signers" "$signers"
    local current t
    current=v$(cat "$1/VERSION" 2>/dev/null || true)
    while read -r t; do
        tag_newer "$t" "$current" && tag_newer "$2" "$t" || continue
        release_trusted "$1" "$t" "$signers" || continue
        git -C "$1" show "refs/tags/$t:dev/release-signers" > "$signers.next" 2>/dev/null || continue
        cmp -s "$signers.next" "$signers" ||
            echo "Release $t: signature verified; its release keys are trusted from here on."
        mv "$signers.next" "$signers"
    done < <(git -C "$1" tag -l 'v*' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$' | grep -v -- '-bridge$' | rank_tags)
    rm -f "$signers.next"
    if release_trusted "$1" "$2" "$signers"; then
        # ("signature verified": dev/update-check.sh release-test looks for these words)
        rm -f "$signers"; echo "Release $2: signature verified."; return 0
    fi
    rm -f "$signers"
    if [[ ${FRAME_TWEAKS_ALLOW_UNSIGNED:-} == 1 ]]; then
        echo "warning: $(t "release %s isn't signed by Frame Tweaks' release key; continuing (FRAME_TWEAKS_ALLOW_UNSIGNED=1)" "$2")" >&2
        return 0
    fi
    echo "Release $2 isn't signed by Frame Tweaks' release key, so it wasn't installed." >&2
    echo "$(t 'This can mean it was tampered with. Check %s' https://github.com/AstronautCheetah/frame-tweaks/releases)" >&2
    return 1
}
