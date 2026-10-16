#!/bin/bash
# Bootstrap: install (or update) Frame Tweaks into ~/frame-tweaks, add a
# "Frame Tweaks" entry to the app menu, and open the installer.
#   curl -fsSL https://raw.githubusercontent.com/AstronautCheetah/frame-tweaks/main/get.sh | bash
# Test releases too (testers): ... | FRAME_TWEAKS_CHANNEL=beta bash (kept for later updates).
set -euo pipefail
# All in one function, called on the last line: a download cut short runs nothing.
main() {
    REPO=${FRAME_TWEAKS_REPO:-https://github.com/AstronautCheetah/frame-tweaks.git}
    DIR=${FRAME_TWEAKS_DIR:-$HOME/frame-tweaks}
    [ -z "${FRAME_TWEAKS_DIR:-}" ] && [ -d "$HOME/steam-frame-tweaks/.git" ] && DIR=$HOME/steam-frame-tweaks   # its old name
    # A channel given here is kept (./install.sh channel), so later updates take the same releases.
    case ${FRAME_TWEAKS_CHANNEL:-} in
        "") ;;
        stable|beta) mkdir -p "$HOME/.config/frame-tweaks"; echo "$FRAME_TWEAKS_CHANNEL" > "$HOME/.config/frame-tweaks/channel"
                     echo "Release channel: $FRAME_TWEAKS_CHANNEL" ;;
        *) echo "FRAME_TWEAKS_CHANNEL: stable or beta" >&2; exit 1 ;;
    esac

    if [ -d "$DIR/.git" ]; then
        # Already installed: so this is an update, done as ./install.sh update does it: the newest
        # release, but only one signed by the release key this copy already has, and the installed
        # tweaks' installers run again if it's a new one (or an update didn't finish). (A plain
        # checkout here skipped both.)
        echo "Updating $DIR (./install.sh update)"
        (cd "$DIR" && ./install.sh update)
    else
        # The newest release (a vX.Y.Z tag), not whatever is on main right now. Stable releases
        # only (vX.Y.Z); FRAME_TWEAKS_CHANNEL=beta also takes pre-releases (vX.Y.Z-rc1), ranked
        # below the release they lead up to ("-" → "~" sorts before the final version).
        pattern='^v[0-9]+\.[0-9]+\.[0-9]+$'
        [ "${FRAME_TWEAKS_CHANNEL:-stable}" = beta ] && pattern='^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$'
        # (|| true: with no release found, or GitHub out of reach, set -e would stop here without a word.)
        TAG=$(git ls-remote --tags --refs "$REPO" 'v*' | sed 's|.*refs/tags/||' | grep -E "$pattern" |
              sed 's/-/~/' | sort -V | sed 's/~/-/' | tail -1) || true
        [ -n "$TAG" ] || { echo "Couldn't find a release of $REPO" >&2; exit 1; }
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
