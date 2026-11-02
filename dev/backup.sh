#!/usr/bin/env bash
# dev/backup.sh: a snapshot of this checkout on another drive (an SD card), for the maintainer's
# own copy: everything in the folder, the .git folder with commits not pushed and stashes, local
# packs, notes and whatever else git ignores, but not what can be made again (__pycache__,
# *.pyc, .venv, .cache, tmp, editor backups). Each run makes DEST/<date-time>/ hardlinked against
# the snapshot before it (rsync --link-dest: an unchanged file takes no new space), points
# DEST/latest at it, and keeps the newest 48. Nothing happens while DEST's drive isn't mounted.
#   dev/backup.sh [DEST]              a snapshot now
#   dev/backup.sh --timer [DEST]      that, and every hour from now on (a user systemd timer;
#                                     also a few minutes after each login)
#   dev/backup.sh --remove-timer      stop the hourly snapshots
# DEST: the argument, else $FRAME_TWEAKS_BACKUP, else frame-tweaks-backup on the first drive
# mounted under /run/media/$USER.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
KEEP=48
UNIT=frame-tweaks-backup

dest_default() {
    if [ -n "${FRAME_TWEAKS_BACKUP:-}" ]; then echo "$FRAME_TWEAKS_BACKUP"; return; fi
    local d
    for d in /run/media/"$USER"/*/; do
        [ -d "$d" ] && mountpoint -q "$d" && { echo "${d}frame-tweaks-backup"; return; }
    done
    echo "dev/backup.sh: no drive mounted under /run/media/$USER; give the backup folder: dev/backup.sh DEST" >&2
    return 1
}

snapshot() {
    local dest=$1 stamp link=() new
    # (the drive gone: say so quietly, for the timer; a folder on the root drive would fill it)
    mountpoint -q "$(dirname "$dest")" || mountpoint -q "$(dirname "$(dirname "$dest")")" ||
        { echo "dev/backup.sh: $dest isn't on a mounted drive; no snapshot" >&2; return 0; }
    mkdir -p "$dest"
    stamp=$(date +%Y-%m-%d_%H%M%S)
    new="$dest/$stamp"
    [ -d "$dest/latest/" ] && link=(--link-dest="$dest/latest/")
    rsync -a --delete "${link[@]}" \
        --exclude='__pycache__/' --exclude='*.pyc' --exclude='/.venv/' --exclude='/.cache/' --exclude='/tmp/' \
        --exclude='*.swp' --exclude='*~' \
        "$repo/" "$new.part/"
    mv "$new.part" "$new"
    ln -sfn "$stamp" "$dest/latest"
    # (the oldest beyond KEEP go; latest is a link, not counted)
    find "$dest" -mindepth 1 -maxdepth 1 -type d -name '20*' | sort | head -n -"$KEEP" | while read -r old; do rm -rf "$old"; done
    echo "snapshot: $new ($(du -sh --apparent-size "$new" | cut -f1); $(find "$dest" -mindepth 1 -maxdepth 1 -type d -name '20*' | wc -l) kept)"
}

user_systemctl() {
    XDG_RUNTIME_DIR="/run/user/$(id -u)" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus" systemctl --user "$@"
}

install_timer() {
    local dest=$1 units="$HOME/.config/systemd/user"
    mkdir -p "$units"
    cat > "$units/$UNIT.service" <<UNIT
[Unit]
Description=Frame Tweaks checkout: snapshot to $dest (dev/backup.sh)

[Service]
Type=oneshot
ExecStart=/bin/bash "$repo/dev/backup.sh" "$dest"
Nice=19
IOSchedulingClass=idle
UNIT
    cat > "$units/$UNIT.timer" <<UNIT
[Unit]
Description=Frame Tweaks checkout: hourly snapshot (dev/backup.sh)

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Persistent=true

[Install]
WantedBy=timers.target
UNIT
    user_systemctl daemon-reload
    user_systemctl enable --now "$UNIT.timer"
    echo "timer: hourly snapshots to $dest ($UNIT.timer; dev/backup.sh --remove-timer stops them)"
}

case ${1:-} in
    --remove-timer)
        user_systemctl disable --now "$UNIT.timer" 2>/dev/null || true
        rm -f "$HOME/.config/systemd/user/$UNIT".{service,timer}
        user_systemctl daemon-reload
        echo "timer removed (snapshots already made stay)" ;;
    --timer)
        dest=${2:-$(dest_default)}
        snapshot "$dest"
        install_timer "$dest" ;;
    -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//' ;;
    *)
        dest=${1:-$(dest_default)}
        snapshot "$dest" ;;
esac
