# shellcheck shell=bash
# Shared helpers for steam-frame-tweaks installers. Source, don't execute.
# Everything installs into the user's home (~/.local), so SteamOS's read-only
# root and system updates are never touched.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
# HTTPS mirrors first (the main mirror's certificate doesn't match its name); every package is
# signature-checked anyway.
ALARM_MIRROR="${ALARM_MIRROR:-https://fl.us.mirror.archlinuxarm.org/aarch64}"
ALARM_FALLBACK="https://de3.mirror.archlinuxarm.org/aarch64 http://mirror.archlinuxarm.org/aarch64"
mkdir -p "$BIN" "$APPS"

say()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(uname -m)" = aarch64 ] || warn "These tweaks target the Steam Frame (aarch64); you're on $(uname -m)."

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
    cat <<MSG

This tweak needs Homebrew, a package manager that installs into /home/linuxbrew.
That folder is outside SteamOS's system partition, so updates don't remove it.
Homebrew's installer asks for your sudo (admin) password once, to create that folder.
MSG
    if passwd -S "$USER" 2>/dev/null | grep -q " NP "; then
        die "Your user has no password, so sudo can't work. Set one with 'passwd', then re-run."
    fi
    ask "Install Homebrew now?" || die "Homebrew is required for this tweak. Install it from https://brew.sh and re-run."
    sudo -v || die "sudo failed."
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" ||
        die "Homebrew's installer failed (see above)."
    [ -x "$BREW" ] || die "Homebrew didn't end up in /home/linuxbrew."
    # shellcheck disable=SC2016
    grep -qs 'linuxbrew/bin/brew shellenv' "$HOME/.bashrc" ||
        echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> "$HOME/.bashrc"
    eval "$("$BREW" shellenv)"
    say "Homebrew installed."
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
    say "Fetching $file"
    t=$(mktemp -d)
    curl -fsSL -o "$t/$file" "$mirror/$repo/$file" && curl -fsSL -o "$t/$file.sig" "$mirror/$repo/$file.sig" ||
        { rm -rf "$t"; die "download of $file failed"; }
    gpgv --keyring "$REPO_DIR/lib/keys/archlinuxarm.gpg" "$t/$file.sig" "$t/$file" 2>/dev/null ||
        { rm -rf "$t"; die "$file: bad or missing Arch Linux ARM signature; not installing it"; }
    mkdir -p "$dest"
    bsdtar -xf "$t/$file" -C "$dest"
    rm -rf "$t"
}

# fetch_pinned <id> <out-file>: download <id>/pin's url and check it against the hash recorded
# in the pin (not one fetched alongside it), so a changed upstream file is refused.
fetch_pinned() {
    local pin="$REPO_DIR/$1/pin" url sha
    url=$(sed -n 's/^url=//p' "$pin"); sha=$(sed -n 's/^sha256=//p' "$pin")
    curl -fL# -o "$2" "$url" || die "download failed: $url"
    echo "$sha  $2" | sha256sum -c --quiet - || die "$(basename "$url"): checksum differs from the pinned one; not installing it"
}
# newest_tag: the newest release tag from the tag names on stdin. Stable (vX.Y.Z) only, unless
# the channel is beta (FRAME_TWEAKS_CHANNEL=beta, or "beta" in ~/.config/steam-frame-tweaks/channel),
# which adds pre-releases (vX.Y.Z-rc1) ranked below their final version.
release_channel() {
    local c=${FRAME_TWEAKS_CHANNEL:-}
    [ -n "$c" ] || c=$(cat "$HOME/.config/steam-frame-tweaks/channel" 2>/dev/null || true)
    [ "$c" = beta ] && echo beta || echo stable
}
newest_tag() {
    local pattern='^v[0-9]+\.[0-9]+\.[0-9]+$'
    [ "$(release_channel)" = beta ] && pattern='^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$'
    grep -E "$pattern" | sed 's/-/~/' | sort -V | sed 's/~/-/' | tail -1
}
pin_version() { sed -n 's/^version=//p' "$REPO_DIR/$1/pin"; }

# Steam's "+" menu resolves Icon= only in the hicolor theme and rescans when the
# applications/icon directories' mtime changes (writing an existing file doesn't change it).
ICONS="$HOME/.local/share/icons/hicolor"
LAUNCHER_ORIGINALS="$HOME/.local/share/frame-tweaks/launcher-originals"

# install_icon <name>: icons/<name>.png from this repo into hicolor (256x256).
install_icon() {
    mkdir -p "$ICONS/256x256/apps"
    install -m644 "$REPO_DIR/icons/$1.png" "$ICONS/256x256/apps/$1.png"
    touch "$ICONS"
}

# install_desktop <file.desktop>: copy into the app menu, expanding @BIN@. If the entry is
# wrapped by wallet-launcher (shared wallet / password gate), the new version becomes the
# wrapper's original and the wrapper is re-applied, so the gate isn't silently dropped.
install_desktop() {
    local name; name=$(basename "$1")
    if [ -f "$LAUNCHER_ORIGINALS/$name" ] && [ -x "$BIN/wallet-launcher" ]; then
        sed "s|@BIN@|$BIN|g" "$1" > "$LAUNCHER_ORIGINALS/$name"
        "$BIN/wallet-launcher" --reapply "${name%.desktop}" >/dev/null
    else
        sed "s|@BIN@|$BIN|g" "$1" > "$APPS/$name"
    fi
    update-desktop-database "$APPS" 2>/dev/null || true
    touch "$APPS"
}

# Shared venv for the small Python tools that talk D-Bus (jeepney, pure Python).
TWEAKS_VENV="$HOME/.local/share/frame-tweaks/venv"
ensure_tweaks_venv() {
    if ! "$TWEAKS_VENV/bin/python" -c 'import jeepney' 2>/dev/null; then
        say "Creating Python venv with jeepney"
        python3 -m venv "$TWEAKS_VENV"
        "$TWEAKS_VENV/bin/pip" install -q jeepney
    fi
}

# install_py_tool <src> : install a Python tool into ~/.local/bin, running on the shared venv.
install_py_tool() {
    sed "1s|.*|#!$TWEAKS_VENV/bin/python|" "$1" > "$BIN/$(basename "$1")"
    chmod 755 "$BIN/$(basename "$1")"
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
    if [ -e "$dest" ]; then cp -p "$dest" "$2" && rm -f "$dest" && say "restored $2"
    elif [ -e "$dest.absent" ]; then rm -f "$2" "$dest.absent" && say "removed $2 (it didn't exist before)"
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
        else kwriteconfig6 --file "$file" --group "$group" --key "$key" "$value"; fi
    done < "$rec"
    rm -f "$rec"; say "restored KDE settings changed by $1"
}

# --- status.sh helpers: print one line, exit 0 = installed/OK, 1 = not installed, 2 = needs attention
status_ok()      { printf 'ok       %s\n' "$*"; exit 0; }
status_missing() { printf 'missing  %s\n' "$*"; exit 1; }
status_warn()    { printf 'warning  %s\n' "$*"; exit 2; }

# remove_files <path>...: delete if present, saying what went
remove_files() {
    local f
    for f in "$@"; do
        if [ -e "$f" ] || [ -L "$f" ]; then rm -rf -- "$f" && say "removed $f"; fi
    done
}

export QT_VENV="$HOME/.local/share/arrowpad/venv"   # PyQt6, shared by arrowpad and nordvpn-tray
