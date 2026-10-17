#!/bin/bash
# Bootstrap: install (or update) Frame Tweaks into ~/frame-tweaks, add a
# "Frame Tweaks" entry to the app menu, and open the installer.
#   curl -fsSL https://raw.githubusercontent.com/AstronautCheetah/frame-tweaks/main/get.sh | bash
# Test releases too (testers): ... | FRAME_TWEAKS_CHANNEL=beta bash (kept for later updates).
set -euo pipefail

# Its few words come before Frame Tweaks (and its translations) are here, so they carry their own
# translations: dev/i18n.py update writes them below from locale/*.po. The language is picked as
# Frame Tweaks picks it (lib/i18n.py), without the keyboard: FRAME_TWEAKS_LANGUAGE, the one chosen
# in ⚙ Preferences, LANGUAGE, LC_ALL, LC_MESSAGES, Steam's own interface language (SteamOS keeps
# LANG at en_US whatever language the Frame was set up in), then LANG. Once Frame Tweaks is here,
# its own (keyboard included) takes over.
texts() {
    # BEGIN translations (dev/i18n.py update; don't edit by hand)
    GET_LANGS="es_419 fr nl_BE"
    declare -gA GET_TR=(
        [$'es_419|Couldn\'t find a release of %s']=$'No se encontró ninguna versión de %s'
        [$'es_419|FRAME_TWEAKS_CHANNEL: stable or beta']=$'FRAME_TWEAKS_CHANNEL: stable o beta'
        [$'es_419|Installing %s into %s']=$'Instalando %s en %s'
        [$'es_419|Release channel: %s']=$'Canal de versiones: %s'
        [$'es_419|Some tweaks didn\'t update (see above); the window shows which.']=$'Algunos ajustes no se actualizaron (ver arriba); la ventana muestra cuáles.'
        [$'es_419|Updating %s (./install.sh update)']=$'Actualizando %s (./install.sh update)'
        [$'fr|Couldn\'t find a release of %s']=$'Impossible de trouver une version de %s'
        [$'fr|FRAME_TWEAKS_CHANNEL: stable or beta']=$'FRAME_TWEAKS_CHANNEL : stable ou beta'
        [$'fr|Installing %s into %s']=$'Installation de %s dans %s'
        [$'fr|Release channel: %s']=$'Canal des versions : %s'
        [$'fr|Some tweaks didn\'t update (see above); the window shows which.']=$'Certains ajustements n\'ont pas été mis à jour (voir ci-dessus) ; la fenêtre indique lesquels.'
        [$'fr|Updating %s (./install.sh update)']=$'Mise à jour de %s (./install.sh update)'
        [$'nl_BE|Couldn\'t find a release of %s']=$'Geen versie van %s gevonden'
        [$'nl_BE|FRAME_TWEAKS_CHANNEL: stable or beta']=$'FRAME_TWEAKS_CHANNEL: stable of beta'
        [$'nl_BE|Installing %s into %s']=$'%s installeren in %s'
        [$'nl_BE|Release channel: %s']=$'Versiekanaal: %s'
        [$'nl_BE|Some tweaks didn\'t update (see above); the window shows which.']=$'Sommige aanpassingen zijn niet bijgewerkt (zie hierboven); het venster toont welke.'
        [$'nl_BE|Updating %s (./install.sh update)']=$'%s bijwerken (./install.sh update)'
    )
    # END translations
}
steam_language() {
    [ "${FRAME_TWEAKS_KEYBOARD:-}" = 0 ] && return 0
    local l
    l=$(sed -n '/^[[:space:]]*"Steam"[[:space:]]*$/,/}/s/^[[:space:]]*"language"[[:space:]]*"\([^"]*\)".*/\1/p' \
        "$HOME/.steam/registry.vdf" 2>/dev/null | head -1) || true
    case $l in
        latam) echo es_419 ;; spanish) echo es ;; french) echo fr ;; dutch) echo nl ;; german) echo de ;;
        brazilian) echo pt_BR ;; portuguese) echo pt ;; italian) echo it ;; polish) echo pl ;;
    esac
}
pick_language() {
    local x l chosen
    chosen=$(cat "${FRAME_TWEAKS_PREFERENCE_FILE:-$HOME/.config/frame-tweaks/language}" 2>/dev/null) || true
    for x in "${FRAME_TWEAKS_LANGUAGE:-}" "$chosen" "${LANGUAGE:-}" "${LC_ALL:-}" "${LC_MESSAGES:-}" \
             "$(steam_language)" "${LANG:-}"; do
        x=${x%%:*} x=${x%%.*} x=${x%%@*}
        case $x in ""|C|POSIX|keyboard) continue ;; esac
        break
    done
    GET_LANG=
    case $x in ""|C|POSIX|keyboard|en|en_*) return 0 ;; esac
    for l in $GET_LANGS; do [ "$l" = "$x" ] && GET_LANG=$l && return 0; done
    for l in $GET_LANGS; do [ "${l%%_*}" = "${x%%_*}" ] && GET_LANG=$l && return 0; done
    return 0
}
t() {      # t TEXT ARGS...: TEXT in GET_LANG, printf-style (lib/i18n.sh's t, once it's here)
    local f=$1
    shift
    [ -z "${GET_LANG:-}" ] || f=${GET_TR["$GET_LANG|$f"]:-$f}
    # shellcheck disable=SC2059   # (the text is the format, as with printf)
    printf -- "$f" "$@"
}
installed_texts() {    # Frame Tweaks is here: its own translations, as its scripts use them
    # shellcheck source=/dev/null
    [ -f "$1/lib/i18n.sh" ] && source "$1/lib/i18n.sh"
    return 0
}

# All in one function, called on the last line: a download cut short runs nothing.
main() {
    texts
    pick_language
    REPO=${FRAME_TWEAKS_REPO:-https://github.com/AstronautCheetah/frame-tweaks.git}
    DIR=${FRAME_TWEAKS_DIR:-$HOME/frame-tweaks}
    [ -z "${FRAME_TWEAKS_DIR:-}" ] && [ -d "$HOME/steam-frame-tweaks/.git" ] && DIR=$HOME/steam-frame-tweaks   # its old name
    DIR=$(realpath -m "$DIR")       # (a relative one: install.sh is run by its full path)
    # A channel given here is kept (./install.sh channel), so later updates take the same releases.
    case ${FRAME_TWEAKS_CHANNEL:-} in
        "") ;;
        stable|beta) mkdir -p "$HOME/.config/frame-tweaks"; echo "$FRAME_TWEAKS_CHANNEL" > "$HOME/.config/frame-tweaks/channel"
                     echo "$(t 'Release channel: %s' "$FRAME_TWEAKS_CHANNEL")" ;;
        *) echo "$(t 'FRAME_TWEAKS_CHANNEL: stable or beta')" >&2; exit 1 ;;
    esac

    if [ -d "$DIR/.git" ]; then
        # Already installed: so this is an update, done as ./install.sh update does it: the newest
        # release, but only one signed by the release key this copy already has, and the installed
        # tweaks' installers run again if it's a new one (or an update didn't finish). (A plain
        # checkout here skipped both.)
        installed_texts "$DIR"
        echo "$(t 'Updating %s (./install.sh update)' "$DIR")"
        # (3: updated, but a tweak didn't install again: no reason to stop, the window, opened
        # below, shows which. Anything else: it couldn't update, so the old version isn't opened.)
        rc=0
        (cd "$DIR" && ./install.sh update) || rc=$?
        [ "$rc" -eq 0 ] || [ "$rc" -eq 3 ] || exit "$rc"
        [ "$rc" -eq 0 ] || echo "$(t "Some tweaks didn't update (see above); the window shows which.")"
    else
        # The newest release (a vX.Y.Z tag), not whatever is on main right now. Stable releases
        # only (vX.Y.Z); beta (FRAME_TWEAKS_CHANNEL=beta, or kept from before in
        # ~/.config/frame-tweaks/channel) also takes pre-releases (vX.Y.Z-rc1), ranked below the
        # release they lead up to ("-" → "~" sorts before the final version).
        channel=${FRAME_TWEAKS_CHANNEL:-$(cat "$HOME/.config/frame-tweaks/channel" 2>/dev/null || true)}
        pattern='^v[0-9]+\.[0-9]+\.[0-9]+$'
        [ "$channel" = beta ] && pattern='^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$'
        # (|| true: with no release found, or GitHub out of reach, set -e would stop here without a word.)
        TAG=$(git ls-remote --tags --refs "$REPO" 'v*' | sed 's|.*refs/tags/||' | grep -E "$pattern" |
              sed 's/-/~/' | sort -V | sed 's/~/-/' | tail -1) || true
        [ -n "$TAG" ] || { echo "$(t "Couldn't find a release of %s" "$REPO")" >&2; exit 1; }
        echo "$(t 'Installing %s into %s' "$TAG" "$DIR")"
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
