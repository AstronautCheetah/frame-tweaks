# shellcheck shell=bash
# Shared helpers for steam-frame-tweaks installers. Source, don't execute.
# Everything installs into the user's home (~/.local), so SteamOS's read-only
# root and system updates are never touched.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
ALARM_MIRROR="${ALARM_MIRROR:-http://mirror.archlinuxarm.org/aarch64}"
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
        kdialog --title "Steam Frame Tweaks" --yesno "$1"
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
    local repo=$1 name=$2 dest=$3 file
    file=$(curl -fsSL "$ALARM_MIRROR/$repo/" |
        grep -oE "\"$name-[0-9][^\"/]*-aarch64\.pkg\.tar\.(xz|zst)\"" | tr -d '"' | sort -V | tail -1)
    [ -n "$file" ] || die "package $name not found in ALARM $repo"
    say "Fetching $file"
    mkdir -p "$dest"
    curl -fsSL "$ALARM_MIRROR/$repo/$file" | bsdtar -xf - -C "$dest"
}

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
