# shellcheck shell=bash
# Translations for shell scripts (lib/i18n.py; locale/README.md). Source it, then
#   t 'Text, with %s for each value' VALUE...
# prints the text in the user's language (no newline), as printf would: say "$(t 'Fetching %s' "$name")".
# Write the text in single quotes, or in double quotes without $: dev/i18n.py collects it from
# there, and the values go in as arguments. A text given no values is printed as it is.
# lib/common.sh sources this; installed programs source their copy, from
# ~/.local/share/frame-tweaks/i18n (install_i18n).
declare -gA FT_TR=()
if [ "${FRAME_TWEAKS_LANG_RESOLVED:-}" != en ]; then
    # (one python3 run per script; "en": a script started by one that found no translation)
    eval "$(python3 "$(dirname "${BASH_SOURCE[0]}")/i18n.py" bash 2>/dev/null)" || true
fi
t() {
    local f=$1
    [ -z "$f" ] || f=${FT_TR[$1]:-$1}
    shift
    if [ $# -eq 0 ]; then
        printf '%s' "$f"
    else
        # shellcheck disable=SC2059   # (the text is the format, as with printf)
        printf -- "$f" "$@"
    fi
}
