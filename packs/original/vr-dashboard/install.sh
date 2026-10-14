#!/bin/bash
# SteamVR dashboard patching: the shared part of the VR environment tweaks (Curved world windows,
# Back to the previous window). Turns on the dashboard's local DevTools port while SteamVR runs
# and injects each installed tweak's patch; installing or removing a tweak adds or removes its patch.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
D="$HOME/.local/share/frame-tweaks/vr-dashboard"
U="$HOME/.config/systemd/user"
mkdir -p "$D/patches" "$U/steamvr.service.d" "$HOME/.config/frame-tweaks"
install_i18n
install -m755 "$TWEAK_DIR/sft-dashboard" "$D/sft-dashboard"
install -m644 "$TWEAK_DIR/lib.js" "$D/lib.js"            # helpers the patches share

# Older versions: this lived inside Curved world windows (sft-curvature). Move its patch over.
OLD="$HOME/.local/share/frame-tweaks/curvature"
if [ -f "$U/sft-curvature.service" ] || [ -d "$OLD" ]; then
    sysctl_user stop sft-curvature.service 2>/dev/null || true
    [ -f "$OLD/sft-curvature.js" ] && install -m644 "$(tweak_dir curvature)/patch.js" "$D/patches/curvature.js"
    remove_files "$OLD" "$U/sft-curvature.service" "$U/steamvr.service.d/sft-curvature.conf"
fi

# Before every SteamVR start: turn its dashboard DevTools port on (put back when it stops).
cat > "$U/sft-vr-debugger.service" <<UNIT
[Unit]
Description=Turn on SteamVR's dashboard DevTools port until SteamVR stops (Frame Tweaks)
Before=steamvr.service

[Service]
Type=oneshot
ExecStart=$D/sft-dashboard arm
# Sandboxing: it only edits SteamVR's settings file and its own note of the previous value.
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=%h/.config/openvr %h/.local/state
PrivateTmp=yes
PrivateNetwork=yes
RestrictAddressFamilies=AF_UNIX
LockPersonality=yes
RestrictRealtime=yes
RestrictNamespaces=yes
SystemCallArchitectures=native
UNIT
# While SteamVR runs: inject the patches (and again after a dashboard reload).
cat > "$U/sft-dashboard.service" <<UNIT
[Unit]
Description=SteamVR dashboard patches: VR environment tweaks (Frame Tweaks)
After=steamvr.service
PartOf=steamvr.service

[Service]
ExecStart=$D/sft-dashboard watch
Restart=on-failure
RestartSec=10
# Sandboxing: reads SteamVR's dashboard files and the patches, talks to 127.0.0.1:8087, writes
# one status file; runs ydotool (its socket is in %t) for the scroll strips' keys.
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=read-only
# %h/.config/frame-tweaks: settings saved from a gear panel in VR (sftConfig).
ReadWritePaths=%t %h/.config/frame-tweaks
PrivateTmp=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
IPAddressAllow=localhost
IPAddressDeny=any
LockPersonality=yes
RestrictRealtime=yes
RestrictNamespaces=yes
SystemCallArchitectures=native
UNIT
# Wants=, not Requires=: SteamVR starts normally even if these fail.
cat > "$U/steamvr.service.d/sft-dashboard.conf" <<UNIT
[Unit]
Wants=sft-vr-debugger.service sft-dashboard.service
After=sft-vr-debugger.service

[Service]
ExecStopPost=-$D/sft-dashboard restore
UNIT
sysctl_user daemon-reload

if sysctl_user is-active --quiet steamvr.service; then
    if ! timeout 8 "$D/sft-dashboard" status 2>&1 | grep -q "port closed"; then
        sysctl_user restart sft-dashboard.service
        say "$(t 'Dashboard patches active.')"
    else
        while IFS= read -r line; do say "$line"; done <<< "$(t 'Installed. It starts working the next time SteamVR starts (reboot, or restart SteamVR
from its menu): SteamVR opens the port it needs only at startup.')"
    fi
else
    say "$(t 'Installed; active from the next SteamVR start.')"
fi
