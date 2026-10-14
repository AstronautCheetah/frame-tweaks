# shellcheck shell=bash
# Shared helpers for frame-tweaks installers. Source, don't execute.
# Everything installs into the user's home (~/.local), so SteamOS's read-only
# root and system updates are never touched.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/i18n.sh
source "$REPO_DIR/lib/i18n.sh"      # t 'Text %s' VALUE: in the user's language
# The exact build, for people and logs: 0.5.0 at a release tag, 0.5.0+3.abc1234 three commits
# after it, -dirty with local changes; the VERSION file without git. (VERSION itself stays the
# release number that migrations and update checks compare.)
ft_version() {
    local d
    d=$(git -C "$REPO_DIR" describe --tags --match 'v[0-9]*' --dirty 2>/dev/null) ||
        { cat "$REPO_DIR/VERSION" 2>/dev/null || echo dev; return; }
    d=${d#v}
    [[ $d =~ ^(.+)-([0-9]+)-g([0-9a-f]+)(-dirty)?$ ]] &&
        d="${BASH_REMATCH[1]}+${BASH_REMATCH[2]}.${BASH_REMATCH[3]}${BASH_REMATCH[4]}"
    echo "$d"
}
# The folder of the tweak whose script sourced this file (its own files), and tweak_dir <id> for
# another tweak's: the installer passes the folders it found (FRAME_TWEAKS_DIRS, "id=folder"
# lines, user packs included); a script run on its own falls back to the official packs.
TWEAK_DIR="$(cd "$(dirname "${BASH_SOURCE[1]:-$0}")" && pwd)"
tweak_dir() {
    local line
    while IFS= read -r line; do
        [ "${line%%=*}" = "$1" ] && { echo "${line#*=}"; return; }
    done <<<"${FRAME_TWEAKS_DIRS:-}"
    local pack
    for pack in original integrations third-party; do
        [ -d "$REPO_DIR/packs/$pack/$1" ] && { echo "$REPO_DIR/packs/$pack/$1"; return; }
    done
    echo "$REPO_DIR/packs/original/$1"
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

BREW=/home/linuxbrew/.linuxbrew/bin/brew

# ask <question>: yes/no in the terminal, or a dialog when there's no terminal.
ask() {
    if [ -t 0 ]; then
        local a; read -rp "$1 [y/N] " a; [[ $a == [yY]* ]]
    elif command -v kdialog >/dev/null && [ -n "${WAYLAND_DISPLAY:-${DISPLAY:-}}" ]; then
        kdialog --title "Frame Tweaks" --yesno "$1"
    else
        return 1
    fi
}

# need_brew: make sure Homebrew is available, offering to install it if it isn't.
need_brew() {
    if command -v brew >/dev/null || [ -x "$BREW" ]; then
        eval "$("${BREW_BIN:-$(command -v brew || echo "$BREW")}" shellenv)"
        return 0
    fi
    printf '\n%s\n' "$(t "This tweak needs Homebrew, a package manager that installs into /home/linuxbrew.
That folder is outside SteamOS's system partition, so updates don't remove it.
Homebrew's installer asks for your sudo (admin) password once, to create that folder.")"
    if passwd -S "$USER" 2>/dev/null | grep -q " NP "; then
        die "$(t "Your user has no password, so sudo can't work. Set one with 'passwd', then re-run.")"
    fi
    ask "$(t 'Install Homebrew now?')" || die "$(t 'Homebrew is required for this tweak. Install it from https://brew.sh and re-run.')"
    sudo -v || die "$(t 'sudo failed.')"
    # Homebrew's installer at a pinned commit, checked against homebrew/pin's hash before it runs.
    local brew_installer; brew_installer=$(mktemp)
    fetch_pinned homebrew "$brew_installer"
    NONINTERACTIVE=1 /bin/bash "$brew_installer" || { rm -f "$brew_installer"; die "$(t "Homebrew's installer failed (see above).")"; }
    rm -f "$brew_installer"
    [ -x "$BREW" ] || die "$(t "Homebrew didn't end up in /home/linuxbrew.")"
    # shellcheck disable=SC2016
    grep -qs 'linuxbrew/bin/brew shellenv' "$HOME/.bashrc" ||
        echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> "$HOME/.bashrc"
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

# Make sure ~/.local/bin is on PATH for terminals and the desktop session.
ensure_path() {
    grep -qs 'HOME/.local/bin' "$HOME/.bashrc" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
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
    local repo=$1 name=$2 dest=$3 file t mirror
    for mirror in "$ALARM_MIRROR" $ALARM_FALLBACK; do
        file=$(curl -fsSL --max-time 20 "$mirror/$repo/" |
            grep -oE "\"$name-[0-9][^\"/]*-aarch64\.pkg\.tar\.(xz|zst)\"" | tr -d '"' | sort -V | tail -1) || true
        [ -n "$file" ] && break
    done
    [ -n "$file" ] || die "package $name not found in ALARM $repo"
    say "$(t 'Fetching %s' "$file")"
    t=$(mktemp -d)
    curl -fsSL -o "$t/$file" "$mirror/$repo/$file" && curl -fsSL -o "$t/$file.sig" "$mirror/$repo/$file.sig" ||
        { rm -rf "$t"; die "download of $file failed"; }
    gpgv --keyring "$REPO_DIR/lib/keys/archlinuxarm.gpg" "$t/$file.sig" "$t/$file" 2>/dev/null ||
        { rm -rf "$t"; die "$file: bad or missing Arch Linux ARM signature; not installing it"; }
    # The signature proves ALARM built it, not that it's the package asked for or not an older
    # one: check the signed package's own name, and refuse a version older than the last one
    # installed (a mirror replaying an old, vulnerable build). ALARM_ALLOW_DOWNGRADE=1 overrides.
    local info got ver seen="$HOME/.local/state/frame-tweaks/alarm/$name"
    info=$(bsdtar -xOf "$t/$file" .PKGINFO 2>/dev/null) || true
    got=$(sed -n 's/^pkgname = //p' <<<"$info"); ver=$(sed -n 's/^pkgver = //p' <<<"$info")
    [ "$got" = "$name" ] || { rm -rf "$t"; die "$file: contains package '$got', not $name; not installing it"; }
    if [ -f "$seen" ] && [ "$(vercmp "$ver" "$(cat "$seen")")" -lt 0 ] && [ "${ALARM_ALLOW_DOWNGRADE:-}" != 1 ]; then
        rm -rf "$t"; die "$name $ver is older than the $(cat "$seen") installed before; not installing it"
    fi
    mkdir -p "$(dirname "$seen")" && printf '%s\n' "$ver" > "$seen"
    mkdir -p "$dest"
    bsdtar -xf "$t/$file" -C "$dest"
    rm -rf "$t"
}

# runs_here <binary> [library-dir]: whether the system can load it (ldd finds every library,
# at a recent enough version). A newer Arch Linux ARM build can need a newer glibc or library
# than SteamOS has; installers then keep the copy that works. Prints what's missing.
runs_here() {
    local missing
    missing=$(LD_LIBRARY_PATH="${2:-}${2:+${LD_LIBRARY_PATH:+:}}${LD_LIBRARY_PATH:-}" ldd "$1" 2>&1 | grep 'not found' || true)
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
install_i18n() {
    local d="$HOME/.local/share/frame-tweaks/i18n"
    mkdir -p "$d/locale"
    install -m644 "$REPO_DIR/lib/i18n.py" "$REPO_DIR/lib/i18n.sh" "$d/"
    find "$d/locale" -name '*.po' -delete
    find "$REPO_DIR/locale" -maxdepth 1 -name '*.po' -exec install -m644 -t "$d/locale" {} +
}
sha_ok() { [ -n "$1" ] && echo "$1  $2" | sha256sum -c --quiet - 2>/dev/null; }
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
    grep -E "$pattern" | sed 's/-/~/' | sort -V | sed 's/~/-/' | tail -1
}
pin_version() { sed -n 's/^version=//p' "$(tweak_dir "$1")/pin"; }

# Steam's "+" menu resolves Icon= only in the hicolor theme and rescans when the
# applications/icon directories' mtime changes (writing an existing file doesn't change it).
ICONS="$HOME/.local/share/icons/hicolor"
LAUNCHER_ORIGINALS="$HOME/.local/share/frame-tweaks/launcher-originals"

# install_icon <name>: <name>.png from the tweak's folder (or the repo's icons/) into hicolor
# (256x256).
install_icon() {
    local src="$TWEAK_DIR/$1.png"
    [ -f "$src" ] || src="$REPO_DIR/icons/$1.png"
    mkdir -p "$ICONS/256x256/apps"
    install -m644 "$src" "$ICONS/256x256/apps/$1.png"
    touch "$ICONS"
}

# install_desktop <file.desktop>: copy into the app menu, expanding @BIN@. If the entry is
# wrapped by wallet-launcher (shared wallet / password gate), the new version becomes the
# wrapper's original and the wrapper is re-applied, so the gate isn't silently dropped.
install_desktop() {
    local name; name=$(basename "$1")
    # (with its name and comment in each translated language: lib/i18n.py desktop)
    if [ -f "$LAUNCHER_ORIGINALS/$name" ] && [ -x "$BIN/wallet-launcher" ]; then
        sed "s|@BIN@|$BIN|g" "$1" | python3 "$REPO_DIR/lib/i18n.py" desktop | write_file "$LAUNCHER_ORIGINALS/$name"
        "$BIN/wallet-launcher" --reapply "${name%.desktop}" >/dev/null
    else
        sed "s|@BIN@|$BIN|g" "$1" | python3 "$REPO_DIR/lib/i18n.py" desktop | write_file "$APPS/$name"
    fi
    update-desktop-database "$APPS" 2>/dev/null || true
    touch "$APPS"
    # (its name in the keyboard's language, as for every entry: install.sh ensure_menu_language)
    sysctl_user start --no-block frame-tweaks-menus.service 2>/dev/null || true
}

# pip_pinned <venv> <package>...: install at the tested versions (lib/python-constraints.txt).
# If pip can't (no build of those versions for this Python, say after a SteamOS update moved
# Python on), fall back to the newest versions with a warning: working beats exact.
pip_pinned() {
    local venv=$1; shift
    "$venv/bin/pip" install -q -c "$REPO_DIR/lib/python-constraints.txt" "$@" && return
    warn "$(t "The tested versions of %s don't install on this Python (%s); trying the newest." "$*" "$("$venv/bin/python" -V 2>&1)")"
    "$venv/bin/pip" install -q "$@"
}

# Shared venv for the small Python tools that talk D-Bus (jeepney, pure Python).
TWEAKS_VENV="$HOME/.local/share/frame-tweaks/venv"
ensure_tweaks_venv() {
    if ! "$TWEAKS_VENV/bin/python" -c 'import jeepney' 2>/dev/null; then
        say "$(t 'Creating Python venv with jeepney')"
        python3 -m venv "$TWEAKS_VENV"
        pip_pinned "$TWEAKS_VENV" jeepney
    fi
}

# ensure_openvr <venv>: the openvr bindings in that venv, on SteamVR's own arm64 library (the
# wheel only bundles an x86 one). Returns 1 (and changes nothing) without SteamVR's library.
VR_LIB=/opt/steamvr/bin/linuxarm64/libopenvr_api.so
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
    # shellcheck disable=SC2086
    YDOTOOL_SOCKET="/run/user/$(id -u)/.ydotool_socket" "$BIN/ydotool" key $CLEAR_MODIFIERS 2>/dev/null || true
}

# --- status.sh helpers: print one line, exit 0 = installed/OK, 1 = not installed, 2 = needs attention
status_ok()      { printf 'ok       %s\n' "$*"; exit 0; }
status_missing() { printf 'missing  %s\n' "$*"; exit 1; }
status_warn()    { printf 'warning  %s\n' "$*"; exit 2; }

# remove_files <path>...: delete if present, saying what went
remove_files() {
    local f
    for f in "$@"; do
        if [ -e "$f" ] || [ -L "$f" ]; then rm -rf -- "$f" && say "$(t 'removed %s' "$f")"; fi
    done
}

export QT_VENV="$HOME/.local/share/arrowpad/venv"   # PyQt6, shared by arrowpad and nordvpn-tray

# --- SteamVR dashboard patches (packs/original/vr-dashboard/) ---------------------------------------------
# A VR environment tweak is one patch file; vr-dashboard's watcher injects it while SteamVR runs.
VR_DASHBOARD="$HOME/.local/share/frame-tweaks/vr-dashboard"
install_dashboard_patch() {    # install_dashboard_patch NAME FILE
    [ -x "$VR_DASHBOARD/sft-dashboard" ] || "$(tweak_dir vr-dashboard)/install.sh" || return 1
    mkdir -p "$VR_DASHBOARD/patches"
    install -m644 "$2" "$VR_DASHBOARD/patches/$1.js"
    if sysctl_user is-active --quiet sft-dashboard.service; then
        # The watcher looks every 5 s: wait for it, so the status shown next is the real one.
        local _
        for _ in 1 2 3 4 5 6 7 8 9 10; do
            "$VR_DASHBOARD/sft-dashboard" status "$1" 2>/dev/null | grep -q ": patched$" && break
            sleep 1
        done
        say "$(t 'Active now.')"
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
        *port*closed*) status_warn "$(t 'waiting for a SteamVR restart (restart SteamVR or reboot once)')" ;;
        *) status_warn "${s:-$(t 'not responding')}" ;;
    esac
}

# verify_release DIR TAG: the checkout DIR's release TAG is signed by a key in dev/release-signers *as installed now*
# (so a tampered release can't bring its own key). Checkouts from before signing have no such
# file and skip this. FRAME_TWEAKS_ALLOW_UNSIGNED=1 overrides, for an emergency.
verify_release() {
    [[ -f $1/dev/release-signers ]] || return 0
    local signers; signers=$(mktemp)
    cp "$1/dev/release-signers" "$signers"
    # An SSH signature only (git checks a PGP or X.509 one against the user's own keyrings, not
    # this file), on a tag that carries the name asked for (so an older signed release can't come
    # back under a newer one's name).
    if [[ $(git -C "$1" for-each-ref --format='%(tag)' "refs/tags/$2" 2>/dev/null) == "$2" ]] &&
       git -C "$1" -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$signers" -c gpg.program=false \
           -c gpg.x509.program=false verify-tag "refs/tags/$2" 2>/dev/null; then
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
