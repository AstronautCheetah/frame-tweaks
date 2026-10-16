#!/bin/bash
# Desktop Recovery: restart-plasmashell (the Restart taskbar button), and taskbar-guard, which runs
# it by itself when the taskbar closes while desktop mode goes on.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ensure_path
install_i18n
install -m755 "$TWEAK_DIR/restart-plasmashell" "$TWEAK_DIR/taskbar-guard" "$BIN/"
say "$(t 'Installed %s' restart-plasmashell)"
# The watch starts with desktop mode (KDE autostart: in its environment, as plasmashell needs).
printf '%s\n' "[Desktop Entry]" "Type=Application" "Name=Taskbar watch" \
    "Comment=Brings the taskbar back if it closes (Frame Tweaks, Desktop Recovery)" \
    "Exec=systemd-cat -t taskbar-guard $BIN/taskbar-guard" "X-KDE-autostart-phase=2" "NoDisplay=true" |
    write_file "$HOME/.config/autostart/frame-tweaks-taskbar-guard.desktop"
# And now, if desktop mode is running.
if src=$(pgrep -u "$(id -u)" -x ksmserver | head -1) && [ -n "$src" ]; then
    mapfile -d '' envs < "/proc/$src/environ"
    (cd "$HOME" && env -i "${envs[@]}" setsid -f systemd-cat -t taskbar-guard "$BIN/taskbar-guard" >/dev/null 2>&1 </dev/null)
    say "$(t 'Watching the taskbar: if it closes while desktop mode runs, it comes back by itself.')"
else
    say "$(t 'The taskbar watch starts with desktop mode.')"
fi
