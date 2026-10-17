#!/bin/bash
# A fresh install of Frame Tweaks, as a new user gets it, without touching yours: the one-liner
# runs in a throwaway home inside a sandbox (bubblewrap for the folders and processes, pasta for
# the network), and its window opens on your desktop.
#
#   dev/fresh-install.sh                  the one-liner from GitHub (main's get.sh, the newest release)
#   dev/fresh-install.sh --beta           the testers' one-liner (… | FRAME_TWEAKS_CHANNEL=beta bash): the
#                                         newest test release (vX.Y.Z-rc.N), or release if that's newer
#   dev/fresh-install.sh --from checkout  this checkout as it is now (changes to tracked files
#                                         included, committed or not), as release v<VERSION>-local
#                                         on the test-release channel (fresh installs take tags)
#   dev/fresh-install.sh --from v0.6.9    that release (or a test release, v0.6.9-rc1)
#
#   --real         actions really happen (inside the sandbox). Default: a dry run
#                  (FRAME_TWEAKS_DRY_RUN=1): installing, removing and Run only say what they'd do.
#   --reuse-pyqt   lend the window a PyQt6 set up once (~/.cache/frame-tweaks/fresh-install-pyqt)
#                  instead of downloading ~280 MB each time. Without it, as for a new user, that
#                  setup runs in this terminal under the installer's splash (lib/splash.py, in
#                  releases after 0.6.11).
#   --keep         keep the throwaway home afterwards (it says where); otherwise it's deleted
#   --again DIR    open a kept one's window again (with --real or not, as you choose this time)
#   --shell        a shell in the sandbox instead of the one-liner, to look around (commands from
#                  stdin when it isn't a terminal)
#
# In the sandbox (so nothing in it can change your setup, and a new user's view is what you see):
# - your home is an empty folder, at the same path, so it looks like a new user's;
# - /run/user/<uid> is empty but for your desktop's display (so windows appear on your desktop)
#   and a D-Bus of its own: your wallet, your systemd user services and your desktop's D-Bus
#   are out of reach;
# - it has its own process list: pgrep and pkill see only its own, and nothing it starts outlives it;
# - Homebrew (/home/linuxbrew), system Flatpaks (/var/lib/flatpak) and the system D-Bus are hidden,
#   /dev/uinput is masked and the desktop's X11 display left out (nothing in it can type into your
#   desktop), and your services' control groups are read-only (nothing in it can stop them);
# - the network works, but this Frame's own services (127.0.0.1: SteamVR's dashboard, adb, …)
#   aren't reachable; /tmp, /var/tmp and /dev/shm are its own.
# Stand-ins: systemctl and systemd-run log and succeed (services report inactive), sudo and pkexec
# refuse, steamvr logs. Their calls: calls.log in the sandbox folder (kept with --keep).
#
# What it can't show: tweaks working in VR or in your desktop session, Homebrew, and anything
# needing sudo. With --real, Flatpak apps install into the throwaway home (downloads included).
set -euo pipefail
cd "$(dirname "$0")/.."
die() { echo "fresh-install: $*" >&2; exit 1; }

from=github beta="" real="" pyqt="" keep="" again="" shell=""
while [ $# -gt 0 ]; do
    case $1 in
        --from) from=${2:?--from: github, checkout or a tag}; shift ;;
        --beta) beta=1 ;;
        --real) real=1 ;;
        --reuse-pyqt) pyqt=1 ;;
        --keep) keep=1 ;;
        --again) again=$(realpath -e "${2:?--again: the folder --keep printed}"); keep=1; shift ;;
        --shell) shell=1 ;;
        -h|--help) sed -n '2,/^set -euo/p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
        *) die "unknown option $1 (--help)" ;;
    esac
    shift
done
command -v bwrap >/dev/null || die "needs bwrap (bubblewrap; SteamOS has it)"
command -v pasta >/dev/null || die "needs pasta (passt; SteamOS has it)"
[ -n "${WAYLAND_DISPLAY:-${DISPLAY:-}}" ] || die "run it in desktop mode: the window opens on your desktop"

uid=$(id -u)
run=/run/user/$uid
if [ -n "$again" ]; then
    work=$again
    [ -d "$work/home" ] && [ -f "$work/sandbox/inner.sh" ] || die "$work isn't a kept fresh install"
else
    mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}/frame-tweaks"
    work=$(mktemp -d "${XDG_CACHE_HOME:-$HOME/.cache}/frame-tweaks/fresh-install.XXXXXX")
    mkdir -p "$work/home" "$work/sandbox/stubs"
fi
# (outside the sandbox's own folder, which it can write: the pid in it is killed on the way out)
info=$work/bwrap-info.json
cleanup() {
    # The sandbox ends with this script (Ctrl+C included): its first process, and with it
    # everything in it. (Ending only the window ends too soon: under 20 s, Frame Tweaks takes that
    # as a window that couldn't open and offers its simple checklist instead.)
    local pid
    pid=$(sed -n 's/.*"child-pid": *\([0-9]*\).*/\1/p' "$info" 2>/dev/null || true)
    if [ -n "$pid" ]; then kill -KILL "$pid" 2>/dev/null || true; fi
    if [ -n "${sandbox:-}" ]; then kill "$sandbox" 2>/dev/null || true; fi
    rm -f "$info"
    if [ -n "$keep" ]; then
        echo "Kept: $work/home (the throwaway home). Its window again: dev/fresh-install.sh --again $work"
    else
        rm -rf -- "$work"
    fi
}
trap cleanup EXIT
trap 'exit 130' INT TERM
box=$run/fresh-install         # $work/sandbox, as the sandbox sees it

# What it installs from, and the one-liner: as written in the README, or the same get.sh run
# against a release made here (get.sh takes the newest vX.Y.Z tag of FRAME_TWEAKS_REPO).
if [ -z "$again" ]; then
    oneliner='curl -fsSL https://raw.githubusercontent.com/AstronautCheetah/frame-tweaks/main/get.sh | bash'
    channel=""
    case $from in
        github)
            # (the channel for bash, which runs get.sh, not for curl)
            if [ -n "$beta" ]; then oneliner=${oneliner/%| bash/| FRAME_TWEAKS_CHANNEL=beta bash}; fi ;;
        checkout)
            # (on main after a test release, VERSION is X.Y.Z-rc.N: one more "-" and get.sh found no release)
            tag="v$(cat VERSION)"; if [[ $tag == *-* ]]; then tag="$tag.local"; else tag="$tag-local"; fi; channel=beta
            src=$work/sandbox/src
            mkdir -p "$src"
            git ls-files -z | tar --null --no-recursion --ignore-failed-read -T - -cf - 2>/dev/null | tar -C "$src" -xf -
            git -C "$src" init -q
            git -C "$src" add -A
            git -C "$src" -c user.name="fresh install" -c user.email=fresh@localhost commit -qm "$tag (from $(git describe --tags --dirty))"
            git -C "$src" tag "$tag"
            git clone -q --bare "$src" "$work/sandbox/release.git"
            rm -rf -- "$src"
            oneliner="FRAME_TWEAKS_REPO=file://$box/release.git bash $box/get.sh"
            cp get.sh "$work/sandbox/get.sh" ;;
        v[0-9]*)
            [ -z "$beta" ] || die "--beta: the newest test release from GitHub; a tag is the release it names"
            git init -q --bare "$work/sandbox/release.git"
            git -C "$work/sandbox/release.git" fetch -q --depth 1 https://github.com/AstronautCheetah/frame-tweaks.git \
                "refs/tags/$from:refs/tags/$from" || die "no release $from on GitHub"
            git -C "$work/sandbox/release.git" show "$from:get.sh" > "$work/sandbox/get.sh"
            if [[ $from == *-* ]]; then channel=beta; fi
            oneliner="FRAME_TWEAKS_REPO=file://$box/release.git bash $box/get.sh" ;;
        *) die "--from: github, checkout or a tag (vX.Y.Z)" ;;
    esac
    if [ -n "$channel" ]; then oneliner="FRAME_TWEAKS_CHANNEL=$channel $oneliner"; fi
    # Run inside: its own session D-Bus (where FT looks for the VR session's bus, too), then the
    # one-liner, from the new home, as a user pasting it into Konsole.
    cat > "$work/sandbox/inner.sh" <<EOF
#!/bin/bash
dbus-daemon --session --address="unix:path=$run/bus" --nofork --nopidfile 2>>"$box/dbus.log" &
for _ in \$(seq 50); do [ -S "$run/bus" ] && break; sleep 0.1; done
cd "\$HOME"
if [ -n "\${FRESH_SHELL:-}" ]; then
    if [ -t 0 ]; then exec bash -i; else exec bash; fi
fi
# (--again: the window of what's installed, as its menu entry opens it. The one-liner again would
# be an update, which takes only signed releases: not a --from checkout one.)
if [ -n "\${FRESH_AGAIN:-}" ]; then exec ~/frame-tweaks/install.sh gui; fi
echo "\$ $oneliner"
$oneliner
EOF
    # Stand-ins (the sandbox can't reach your systemd or the system's anyway: these keep tweak
    # installs from failing on it, and log what they'd have done).
    for cmd in systemctl systemd-run sudo pkexec steamvr; do
        cat > "$work/sandbox/stubs/$cmd" <<EOF
#!/bin/bash
echo "$cmd \$*" >> "$box/calls.log"
case "$cmd" in
    sudo|pkexec) echo "fresh-install sandbox: no administrator rights in here ($cmd \$*)" >&2; exit 1 ;;
    systemctl) case " \$* " in *" is-active "*|*" is-failed "*) echo inactive; exit 3 ;;
                               *" is-enabled "*) echo disabled; exit 1 ;; esac ;;
esac
exit 0
EOF
        chmod +x "$work/sandbox/stubs/$cmd"
    done
fi

# The sandbox. Sources of binds are this machine's paths (bwrap reads them before anything is
# hidden); targets are what the sandbox sees.
args=(--dev-bind / / --unshare-user --uid "$uid" --gid "$(id -g)" --unshare-pid --proc /proc
      --die-with-parent
      --bind "$work/home" "$HOME"
      --perms 0700 --tmpfs "$run"
      --bind "$work/sandbox" "$box"
      --tmpfs /tmp --tmpfs /var/tmp --tmpfs /dev/shm
      --ro-bind /sys/fs/cgroup /sys/fs/cgroup
      --ro-bind /dev/null /dev/uinput)
if [ -z "$shell" ]; then args+=(--new-session); fi
for d in /home/linuxbrew /var/lib/flatpak /run/dbus; do
    if [ -d "$d" ]; then args+=(--tmpfs "$d"); fi
done
env=(HOME="$HOME" USER="$USER" LOGNAME="$USER" SHELL=/bin/bash TERM="${TERM:-xterm-256color}" COLORTERM="${COLORTERM:-}"
     LANG="${LANG:-C.UTF-8}" PATH="$box/stubs:/usr/local/bin:/usr/bin:/bin"
     XDG_RUNTIME_DIR="$run" DBUS_SESSION_BUS_ADDRESS="unix:path=$run/bus"
     XDG_CURRENT_DESKTOP=KDE XDG_SESSION_DESKTOP=KDE KDE_FULL_SESSION=true KDE_SESSION_VERSION=6)
# The desktop's display: its Wayland socket, and XWayland for X apps.
if [ -n "${WAYLAND_DISPLAY:-}" ]; then
    wl=$WAYLAND_DISPLAY; [[ $wl == /* ]] || wl=${XDG_RUNTIME_DIR:-$run}/$wl
    [ -S "$wl" ] || die "no Wayland socket at $wl"
    args+=(--bind "$wl" "$run/wayland-0")
    env+=(WAYLAND_DISPLAY=wayland-0 XDG_SESSION_TYPE=wayland)
fi
# (X11 only without Wayland: an X program can type into the other X windows)
if [ -z "${WAYLAND_DISPLAY:-}" ] && [ -n "${DISPLAY:-}" ] && [ -d /tmp/.X11-unix ]; then
    args+=(--bind /tmp/.X11-unix /tmp/.X11-unix)
    env+=(DISPLAY="$DISPLAY")
    if [ -f "${XAUTHORITY:-}" ]; then
        args+=(--ro-bind "$XAUTHORITY" "$run/xauthority")
        env+=(XAUTHORITY="$run/xauthority")
    fi
fi
if [ -z "$real" ]; then env+=(FRAME_TWEAKS_DRY_RUN=1); fi
if [ -n "$shell" ]; then env+=(FRESH_SHELL=1); fi
if [ -n "$again" ]; then env+=(FRESH_AGAIN=1); fi
if [ -n "$pyqt" ]; then
    # Not yours (yours may be on Homebrew's Python, hidden in here): one set up as a fresh install
    # does (the system's python3, the tested versions), once, kept for later runs, and lent
    # read-only where the window looks for it (QT_VENV in lib/common.sh). With the copy of the
    # interpreter the window runs as (open_window in install.sh), which it can't write in here.
    lent=${XDG_CACHE_HOME:-$HOME/.cache}/frame-tweaks/fresh-install-pyqt
    if ! "$lent/bin/python" -c 'import PyQt6.QtWidgets' 2>/dev/null; then
        echo "Setting up PyQt6 for fresh installs, once (~280 MB): $lent"
        rm -rf -- "$lent"
        /usr/bin/python3 -m venv "$lent"
        nice -n 19 ionice -c3 "$lent/bin/pip" install -q --disable-pip-version-check -c lib/python-constraints.txt PyQt6
        install -m755 "$(readlink -f "$lent/bin/python")" "$lent/bin/sft-python"
    fi
    args+=(--ro-bind "$lent" "$HOME/.local/share/arrowpad/venv")
fi
args+=(--clearenv)
for e in "${env[@]}"; do args+=(--setenv "${e%%=*}" "${e#*=}"); done

echo "Fresh install in $work/home ($([ -n "$real" ] && echo "for real, inside the sandbox" || echo "dry run: actions only say what they'd do"))"
# pasta: the network without this machine's loopback services (-T/-U none: none of its ports
# forwarded in; --no-map-gw: its address doesn't lead to them either). (DNS works through
# systemd-resolved's socket; pasta's note that it found no nameserver it can forward to is
# dropped.)
# (In the background, waited for, so Ctrl+C reaches the trap at once; its input kept: --shell.
# The info file is opened inside: pasta closes the descriptors it doesn't know.)
echo "Close the window to end it (or press Ctrl+C here)."
pasta --config-net --no-map-gw -t none -u none -T none -U none --quiet -- \
    bash -c 'info=$1; shift; exec bwrap --info-fd 3 "$@" 3>"$info"' _ "$info" "${args[@]}" -- bash "$box/inner.sh" 0<&0 \
    2> >(grep -v "Couldn't get any nameserver address" >&2) &
sandbox=$!
rc=0
wait "$sandbox" || rc=$?
sandbox=""; rm -f "$info"       # (ended by itself: nothing left to stop, and its number may be reused)
if [ -s "$work/sandbox/calls.log" ]; then
    echo "Stand-ins called: $(wc -l < "$work/sandbox/calls.log") (calls.log; --keep keeps it)"
fi
exit "$rc"
