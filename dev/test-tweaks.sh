#!/usr/bin/env bash
# Install → status → uninstall each offline-testable tweak in a throwaway home folder, with
# stand-ins for systemctl, flatpak, brew, kdialog and friends (they log and succeed; nothing
# reaches the network or the real system). Fails if a step fails, if a tweak writes outside the
# fake home, or if uninstall leaves files behind that aren't the settings it promises to keep.
#
#   dev/test-tweaks.sh            the default set (runs anywhere, CI included)
#   (TEST_IGNORE=REGEX: files outside the test home that other programs write meanwhile)
#   dev/test-tweaks.sh cursor     just these
set -euo pipefail
cd "$(dirname "$0")/.."
DEFAULT=(cursor tools vr-dashboard curvature float-return float-grab scroll-strips menu-icons homebrew ydotool dictation wallet memcap)
# Screen reader needs Orca and KDE's config tools (the Frame has them, CI doesn't).
command -v orca >/dev/null && command -v kreadconfig6 >/dev/null && DEFAULT+=(screen-reader)
TWEAKS=("${@:-${DEFAULT[@]}}")
# Settings uninstall deliberately keeps (relative to the fake home), per tweak.
# tools: the shared "~/.local/bin on PATH" setup (ensure_path) stays; other tweaks rely on it.
# dictation, wallet: settings they promise to keep, the shared PATH setup, shared dependencies.
PATHSET=".bashrc .config/environment.d/10-local-bin.conf"
YDOTOOL=".local/bin/ydotool .local/bin/ydotoold .config/systemd/user/ydotoold.service"   # a dependency other tweaks share
VRDASH=".local/share/frame-tweaks/vr-dashboard/sft-dashboard .config/systemd/user/sft-vr-debugger.service .config/systemd/user/sft-dashboard.service .config/systemd/user/steamvr.service.d/sft-dashboard.conf"   # shared by the VR windows tweaks
# memcap keeps your limits file; KDE settings files stay (only the changed keys are restored).
declare -A KEEP=([curvature]="$VRDASH" [float-return]="$VRDASH" [float-grab]="$VRDASH" [scroll-strips]="$VRDASH $YDOTOOL .config/frame-tweaks/scroll-strips.json" [vr-dashboard]="" [menu-icons]="" [cursor]="" [tools]="$PATHSET" [homebrew]="" [ydotool]=""
                 [dictation]="$PATHSET .config/dictate.conf $YDOTOOL" [wallet]="$PATHSET .config/kwalletrc"
                 [memcap]="$PATHSET .config/frame-tweaks/memcap.conf" [screen-reader]=".config/kaccessrc")

work=${TEST_WORK:-$(mktemp -d)}; [ -n "${TEST_WORK:-}" ] || trap 'rm -rf "$work"' EXIT
# Run from a copy of the repo, so pins can point at the fixtures below without any checksum
# bypass in the real scripts.
REPO="$work/repo"; mkdir -p "$REPO"
tar -C "$PWD" --exclude=./.git --exclude=./references --exclude=./tmp -cf - . | tar -C "$REPO" -xf -
stubs="$work/stubs"; mkdir -p "$stubs"
# KDE's config tools are real when present (they only write into the fake home), else stubbed.
stub_cmds=(systemctl flatpak brew kdialog notify-send nmcli qdbus qdbus6 busctl gtk-launch sudo gpgv)
command -v kwriteconfig6 >/dev/null || stub_cmds+=(kwriteconfig6)
for cmd in "${stub_cmds[@]}"; do
    cat > "$stubs/$cmd" <<STUB
#!/bin/bash
echo "$cmd \$*" >> "$work/calls.log"
case "$cmd \$1 \$2" in "systemctl --user is-active"*|"systemctl is-active"*) exit 3 ;; esac
case "$cmd \$1" in "flatpak info"|"busctl "*) exit 1 ;; esac    # nothing installed / running
case "$cmd" in brew) [ "\$1" = --version ] && echo "Homebrew 0.0-test"; [ "\$1" = shellenv ] && echo ":";
                     [ "\$1" = --prefix ] && echo /home/linuxbrew/.linuxbrew; [ "\$1" = list ] && true ;; esac
exit 0
STUB
    chmod +x "$stubs/$cmd"
done
# A fake network: curl serves fixtures for the URLs the tested tweaks fetch, refuses the rest.
# (gpgv above is a stand-in too: the fixture package isn't signed. alarm_fetch's real signature
# check is exercised separately, against a real package, when pins or keys change.)
fx="$work/fixtures"; mkdir -p "$fx/pkg/usr/bin"
printf '#!/bin/sh\nexit 0\n' > "$fx/pkg/usr/bin/ydotool"; cp "$fx/pkg/usr/bin/ydotool" "$fx/pkg/usr/bin/ydotoold"
chmod +x "$fx/pkg/usr/bin/"*
printf 'pkgname = ydotool\npkgver = 1.0.4-2\n' > "$fx/pkg/.PKGINFO"
(cd "$fx/pkg" && tar -cJf "$fx/ydotool.pkg.tar.xz" .PKGINFO usr)
echo '<a href="ydotool-1.0.4-2-aarch64.pkg.tar.xz">' > "$fx/listing.html"
head -c 1024 /dev/zero > "$fx/model.bin"; : > "$fx/sig"
sed -i "s/^sha256=.*/sha256=$(sha256sum "$fx/model.bin" | cut -c1-64)/" "$REPO/dictation/pin"
cat > "$stubs/curl" <<STUB
#!/bin/bash
out=""; url=""
while [ \$# -gt 0 ]; do case "\$1" in -o) out=\$2; shift ;; http*) url=\$1 ;; esac; shift; done
case "\$url" in
    */aarch64/*/)                  src=$fx/listing.html ;;
    */ydotool-*.pkg.tar.xz)        src=$fx/ydotool.pkg.tar.xz ;;
    */ydotool-*.pkg.tar.xz.sig)    src=$fx/sig ;;
    *huggingface.co/*ggml-*.bin)   src=$fx/model.bin ;;
    *) echo "test: no network (curl \$url)" >&2; exit 7 ;;
esac
if [ -n "\$out" ]; then cp "\$src" "\$out"; else cat "\$src"; fi
STUB
chmod +x "$stubs/curl"
touch "$work/uinput"     # stands in for /dev/uinput

snapshot() { (cd "$1" && find . -mindepth 1 \( -type f -o -type l \) | sort); }
fail=0
for t in "${TWEAKS[@]}"; do
    home="$work/home-$t"; mkdir -p "$home/.local/share/applications" "$home/.config" "$home/.local/bin"
    # homebrew's checks look for the real binary path; give it a fake one
    run() { env -i HOME="$home" PATH="$stubs:/usr/bin:/bin" USER="test" BREW_BIN="$stubs/brew" \
            FRAME_TWEAKS_YES=1 FRAME_TWEAKS_UINPUT="$work/uinput" bash "$REPO/$t/$1" >>"$work/$t.log" 2>&1; }
    # The shared Python venv (wallet's tools): pre-seeded with a stand-in jeepney instead of pip.
    if [[ " wallet vr-dashboard curvature float-return float-grab scroll-strips " == *" $t "* ]]; then
        python3 -m venv "$home/.local/share/frame-tweaks/venv"
        sp=$("$home/.local/share/frame-tweaks/venv/bin/python" -c 'import site; print(site.getsitepackages()[0])')
        mkdir -p "$sp/jeepney" && : > "$sp/jeepney/__init__.py"
    fi
    before=$(snapshot "$home")
    marker="$work/marker"; touch "$marker"; sleep 1
    step=install
    if run install.sh && { step=status; run status.sh; rc=$?; [ $rc -ne 1 ]; } && step=uninstall && run uninstall.sh; then
        after=$(snapshot "$home")
        # (caches that desktop tools regenerate don't count)
        left=$(comm -13 <(echo "$before") <(echo "$after") | grep -vxF -f <(printf '%s\n' ${KEEP[$t]:-} | sed 's|^|./|') |
               grep -vE '/mimeinfo\.cache$|/__pycache__/|/icon-theme\.cache$|^\./\.cache/' |
               grep -vE '^\./\.local/state/frame-tweaks/alarm/' || true)   # (kept on purpose: no downgrades)
        outside=$(find /tmp /var/tmp "$REPO" -newer "$marker" -type f 2>/dev/null |
                  grep -v "^$work/" | grep -v "^$REPO/\.git/" | { if [ -n "${TEST_IGNORE:-}" ]; then grep -vE "$TEST_IGNORE"; else cat; fi; } || true)
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
