#!/usr/bin/env bash
# Install → status → uninstall each offline-testable tweak in a throwaway home folder, with
# stand-ins for systemctl, flatpak, brew, kdialog and friends (they log and succeed; nothing
# reaches the network or the real system). Fails if a step fails, if a tweak writes outside the
# fake home, or if uninstall leaves files behind that aren't the settings it promises to keep.
#
#   dev/test-tweaks.sh            the default set (runs anywhere, CI included)
#   dev/test-tweaks.sh cursor     just these
set -euo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
DEFAULT=(cursor tools curvature menu-icons homebrew)
TWEAKS=("${@:-${DEFAULT[@]}}")
# Settings uninstall deliberately keeps (relative to the fake home), per tweak.
# tools: the shared "~/.local/bin on PATH" setup (ensure_path) stays; other tweaks rely on it.
declare -A KEEP=([curvature]="" [menu-icons]="" [cursor]="" [tools]=".bashrc .config/environment.d/10-local-bin.conf" [homebrew]="")

work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
stubs="$work/stubs"; mkdir -p "$stubs"
for cmd in systemctl flatpak brew kdialog notify-send nmcli kwriteconfig6 qdbus gtk-launch sudo; do
    cat > "$stubs/$cmd" <<STUB
#!/bin/bash
echo "$cmd \$*" >> "$work/calls.log"
case "$cmd \$1 \$2" in "systemctl --user is-active"*|"systemctl is-active"*) exit 3 ;; esac
case "$cmd" in brew) [ "\$1" = --version ] && echo "Homebrew 0.0-test"; [ "\$1" = shellenv ] && echo ":";
                     [ "\$1" = --prefix ] && echo /home/linuxbrew/.linuxbrew; [ "\$1" = list ] && true ;; esac
exit 0
STUB
    chmod +x "$stubs/$cmd"
done
cat > "$stubs/curl" <<'STUB'
#!/bin/bash
echo "test: no network in dev/test-tweaks.sh (curl $*)" >&2; exit 7
STUB
chmod +x "$stubs/curl"

snapshot() { (cd "$1" && find . -mindepth 1 \( -type f -o -type l \) | sort); }
fail=0
for t in "${TWEAKS[@]}"; do
    home="$work/home-$t"; mkdir -p "$home/.local/share/applications" "$home/.config" "$home/.local/bin"
    # homebrew's checks look for the real binary path; give it a fake one
    run() { env -i HOME="$home" PATH="$stubs:/usr/bin:/bin" USER="test" BREW_BIN="$stubs/brew" \
            FRAME_TWEAKS_YES=1 bash "$REPO/$t/$1" >>"$work/$t.log" 2>&1; }
    before=$(snapshot "$home")
    marker="$work/marker"; touch "$marker"; sleep 1
    step=install
    if run install.sh && { step=status; run status.sh; rc=$?; [ $rc -ne 1 ]; } && step=uninstall && run uninstall.sh; then
        after=$(snapshot "$home")
        left=$(comm -13 <(echo "$before") <(echo "$after") | grep -vxF -f <(printf '%s\n' ${KEEP[$t]:-} | sed 's|^|./|') || true)
        outside=$(find /tmp /var/tmp "$REPO" -newer "$marker" -type f 2>/dev/null |
                  grep -v "^$work/" | grep -v "^$REPO/\.git/" | grep -v "^/tmp/claude" || true)
        if [ -n "$left" ]; then
            echo "FAIL $t: uninstall left files behind:"; echo "$left" | sed 's/^/    /'; fail=1
        elif [ -n "$outside" ]; then
            echo "FAIL $t: wrote outside the test home:"; echo "$outside" | sed 's/^/    /'; fail=1
        else
            echo "ok   $t"
        fi
    else
        echo "FAIL $t: $step failed"; sed 's/^/    /' "$work/$t.log" | tail -15; fail=1
    fi
done
exit $fail
