#!/bin/bash
# Bootstrap: install (or update) Frame Tweaks into ~/frame-tweaks, add a
# "Frame Tweaks" entry to the app menu, and open the installer.
#   curl -fsSL https://raw.githubusercontent.com/AstronautCheetah/frame-tweaks/main/get.sh | bash
set -euo pipefail
# All in one function, called on the last line: a download cut short runs nothing.
main() {
    REPO=${FRAME_TWEAKS_REPO:-https://github.com/AstronautCheetah/frame-tweaks.git}
    DIR=${FRAME_TWEAKS_DIR:-$HOME/frame-tweaks}
    [ -z "${FRAME_TWEAKS_DIR:-}" ] && [ -d "$HOME/steam-frame-tweaks/.git" ] && DIR=$HOME/steam-frame-tweaks   # its old name

    # Install the newest release (a vX.Y.Z tag), not whatever is on main right now.
    # Stable releases only (vX.Y.Z); FRAME_TWEAKS_CHANNEL=beta also takes pre-releases (vX.Y.Z-rc1),
    # ranked below the release they lead up to ("-" → "~" sorts before the final version).
    pattern='^v[0-9]+\.[0-9]+\.[0-9]+$'
    [ "${FRAME_TWEAKS_CHANNEL:-stable}" = beta ] && pattern='^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$'
    # (|| true: with no release found, or GitHub out of reach, set -e would stop here without a word.)
    TAG=$(git ls-remote --tags --refs "$REPO" 'v*' | sed 's|.*refs/tags/||' | grep -E "$pattern" |
          sed 's/-/~/' | sort -V | sed 's/~/-/' | tail -1) || true
    [ -n "$TAG" ] || { echo "Couldn't find a release of $REPO" >&2; exit 1; }
    if [ -d "$DIR/.git" ]; then
        echo "Updating $DIR to $TAG"
        # (Two commands, not an && list: there a failed fetch doesn't stop set -e, and the old
        # version would open as if updated.)
        git -C "$DIR" fetch --quiet --force --tags origin
        git -C "$DIR" -c advice.detachedHead=false checkout --quiet "refs/tags/$TAG"
    else
        echo "Installing $TAG into $DIR"
        git -c advice.detachedHead=false clone --quiet --depth 1 --branch "$TAG" "$REPO" "$DIR"
    fi

    "$DIR/install.sh" menu

    if [ -n "${WAYLAND_DISPLAY:-${DISPLAY:-}}" ] && command -v kdialog >/dev/null; then
        exec "$DIR/install.sh" gui
    else
        exec "$DIR/install.sh"
    fi
}
main "$@"
