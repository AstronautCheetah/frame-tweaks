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
export XDG_RUNTIME_DIR_USER="/run/user/$(id -u)"
sysctl_user() {
    XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR_USER" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR_USER/bus" \
    systemctl --user "$@"
}

need_brew() {
    command -v brew >/dev/null || die "Homebrew is required: https://brew.sh (works on SteamOS aarch64)"
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

# install_desktop <file.desktop>: copy into the app menu, expanding @BIN@.
install_desktop() {
    sed "s|@BIN@|$BIN|g" "$1" > "$APPS/$(basename "$1")"
    update-desktop-database "$APPS" 2>/dev/null || true
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

QT_VENV="$HOME/.local/share/arrowpad/venv"   # PyQt6, shared by arrowpad and nordvpn-tray
