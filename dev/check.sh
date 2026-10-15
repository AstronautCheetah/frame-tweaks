#!/usr/bin/env bash
# The checks, as CI runs them (.github/workflows/ci.yml calls this, one check per step), so a
# change can be checked before it's sent (CONTRIBUTING.md, "Checks"). Any Linux PC will do; none
# of it needs a Frame.
#   dev/check.sh                every check
#   dev/check.sh docs tests     just these: shell python i18n commits manifests tests metadata
#                               docs tweaks
# A check whose tool is missing is skipped, with a note on how to get it (in CI, where every tool
# is installed, a missing one fails instead). PYTHON=… picks the interpreter for the unit tests;
# otherwise the first of .venv/bin/python, python3 and Arrow Pad's venv that has PyQt6.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
ALL=(shell python i18n commits manifests tests metadata docs tweaks)
SKIP=125        # a check's status when it was skipped (no tool uses it)

# Files git would commit (tracked, and new ones not ignored: what CI's checkout holds) with a
# line matching $1; not Markdown, whose code examples can start a line with a shebang.
files_with() { git ls-files -co --exclude-standard -z -- ':!*.md' | xargs -0 -r grep -lE "$1" -- 2>/dev/null; }
missing() {     # missing WHAT HINT: skip this check (fail it in CI, where everything is installed)
    if [ -n "${CI:-}" ]; then echo "  $1 is missing"; return 1; fi
    echo "  skipped: needs $1 ($2)"; return $SKIP
}

check_shell() {
    command -v shellcheck >/dev/null || { missing shellcheck "apt, dnf or brew install shellcheck"; return; }
    # Scripts by their shebang, and the sourced libraries (lib/common.sh) by their shellcheck
    # directive (-x doesn't report what's wrong in a sourced file).
    # shellcheck disable=SC2046   # (file names without spaces, one per line)
    shellcheck -x -S warning $(files_with '^(#!(/bin/(ba)?sh|/usr/bin/env bash)|# shellcheck shell=)') || return 1
    # Programs are replaced, not written into (lib/common.sh write_file): a running program keeps
    # its old file. A redirect or a cp onto ~/.local/bin is the mistake this looks for.
    if grep -nE '(>|\bcp\b[^|]*) *"\$(BIN|HOME/\.local/bin)/' packs/*/*/*.sh lib/common.sh | grep -v write_file; then
        echo "  use write_file (lib/common.sh) for the lines above"; return 1
    fi
}

check_python() {
    local f bad=0
    for f in $(files_with '^#!/usr/bin/env python3') gui/*.py lib/*.py packs/*/*/*.py; do
        python3 -m py_compile "$f" || bad=1
    done
    return $bad
}

check_i18n() { python3 dev/i18n.py check; }       # the translation template is current

check_commits() {
    # Outside CI, only this checkout's own commits when there's an origin/main to compare with.
    local range=HEAD
    [ -z "${CI:-}" ] && git rev-parse -q --verify origin/main >/dev/null && range=origin/main..HEAD
    dev/check-commit-msg.sh --all "$range"
}

check_manifests() {
    local pack pin
    # Every tweak's manifest (README.md front matter) is valid and names its scripts, the
    # example's too (dev/test-tweaks.sh would leave a broken one out, unseen).
    for pack in packs/core packs/integrations packs/third-party examples/hello-pack; do
        python3 lib/sft.py mods check "$pack" >/dev/null || { python3 lib/sft.py mods check "$pack"; return 1; }
    done
    ./install.sh list >/dev/null && ./install.sh _deps all >/dev/null || return 1
    ./install.sh _deps signal | grep -q '^wallet signal' || { echo "  signal should depend on wallet"; return 1; }
    # Every pin names a version, an https URL, and a SHA256 (files) or a commit (git)...
    for pin in packs/*/*/pin packs/*/*/*.pin; do
        [ -f "$pin" ] || continue      # (a pattern that matched nothing)
        grep -qE '^version=.+' "$pin" && grep -qE '^url=https://' "$pin" &&
            grep -qE '^(sha256=[0-9a-f]{64}|rev=[0-9a-f]{40})$' "$pin" || { echo "  incomplete $pin"; return 1; }
    done
    # ... and Frame Tweaks' copy (mirror=, with its licence and licence texts; a git commit's
    # archive with its own sha256), or why there's none (nomirror=).
    for pin in packs/*/*/pin packs/*/*/*.pin; do
        [ -f "$pin" ] || continue
        if grep -q '^mirror=' "$pin"; then
            grep -qE '^mirror=https://github.com/AstronautCheetah/frame-tweaks/releases/download/mirror/[^/]+$' "$pin" &&
                grep -qE '^license=.+' "$pin" && grep -qE '^license_file=https://' "$pin" &&
                { grep -q '^sha256=' "$pin" || grep -qE '^mirror_sha256=[0-9a-f]{64}$' "$pin"; } ||
                { echo "  bad mirror in $pin"; return 1; }
        else
            grep -qE '^nomirror=.+' "$pin" || { echo "  $pin: no mirror= and no nomirror= reason"; return 1; }
        fi
    done
    if grep -vE '^(#|$|[A-Za-z0-9_.-]+==[0-9][0-9A-Za-z.]*$)' lib/python-constraints.txt; then
        echo "  lib/python-constraints.txt: exact versions only"; return 1
    fi
}

check_tests() {
    local py
    for py in "${PYTHON:-}" .venv/bin/python python3 "$HOME/.local/share/arrowpad/venv/bin/python"; do
        [ -n "$py" ] && "$py" -c 'import PyQt6.QtWidgets' 2>/dev/null && break
        py=
    done
    if [ -z "$py" ]; then
        missing "a Python with PyQt6, for the installer window's tests" \
            "once: python3 -m venv .venv && .venv/bin/pip install -c lib/python-constraints.txt PyQt6 pyyaml"
        return
    fi
    QT_QPA_PLATFORM=offscreen "$py" -m unittest discover -s tests ${CI:+-v}
}

check_metadata() {      # the AppStream metadata and the desktop entry
    command -v appstreamcli >/dev/null || { missing appstreamcli "apt install appstream"; return; }
    command -v desktop-file-validate >/dev/null || { missing desktop-file-validate "apt install desktop-file-utils"; return; }
    appstreamcli validate --no-net share/metainfo/*.metainfo.xml || return 1
    local tmp f rc=0; tmp=$(mktemp -d)
    for f in share/applications/*.desktop; do
        sed 's|@REPO@|/opt/x|' "$f" > "$tmp/${f##*/}" && desktop-file-validate "$tmp/${f##*/}" || rc=1
    done
    rm -rf "$tmp"; return $rc
}

check_docs() { python3 dev/check-docs.py && python3 dev/gen-docs.py --check; }

check_tweaks() {        # install → status → uninstall in a throwaway home (dev/test-tweaks.sh)
    command -v bsdtar >/dev/null || { missing bsdtar "apt install libarchive-tools"; return; }
    [ -n "${CI:-}" ] || python3 -c 'import ensurepip, venv' 2>/dev/null ||
        { missing "Python's venv module" "apt install python3-venv"; return; }
    dev/test-tweaks.sh
}

checks=("${@:-${ALL[@]}}")
for c in "${checks[@]}"; do
    [[ " ${ALL[*]} " == *" $c "* ]] || { echo "unknown check: $c (one of: ${ALL[*]})" >&2; exit 2; }
done
failed=() skipped=()
for c in "${checks[@]}"; do
    echo "== $c"
    "check_$c"
    case $? in 0) ;; "$SKIP") skipped+=("$c") ;; *) failed+=("$c") ;; esac
done
echo
[ ${#skipped[@]} -eq 0 ] || echo "skipped (a tool is missing, see above): ${skipped[*]}"
[ ${#failed[@]} -eq 0 ] || { echo "FAILED: ${failed[*]}"; exit 1; }
echo "passed: $(( ${#checks[@]} - ${#skipped[@]} )) of ${#checks[@]} checks"
