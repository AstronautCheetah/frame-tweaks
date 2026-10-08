#!/bin/bash
# Windows floated into the world start curved: a small SteamVR dashboard patch.
source "$(dirname "$0")/../lib/common.sh"
D="$HOME/.local/share/frame-tweaks/curvature"
U="$HOME/.config/systemd/user"
mkdir -p "$D" "$U/steamvr.service.d"
install -m755 "$REPO_DIR/curvature/sft-curvature" "$D/sft-curvature"
install -m644 "$REPO_DIR/curvature/patch.js" "$D/sft-curvature.js"

# Before every SteamVR start: turn its dashboard DevTools port on (put back when it stops).
cat > "$U/sft-vr-debugger.service" <<UNIT
[Unit]
Description=Turn on SteamVR's dashboard DevTools port until SteamVR stops (steam-frame-tweaks)
Before=steamvr.service

[Service]
Type=oneshot
ExecStart=$D/sft-curvature arm
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
# While SteamVR runs: inject the patch (and again after a dashboard reload).
cat > "$U/sft-curvature.service" <<UNIT
[Unit]
Description=Curve world windows by default (steam-frame-tweaks)
After=steamvr.service
PartOf=steamvr.service

[Service]
ExecStart=$D/sft-curvature watch
Restart=on-failure
RestartSec=10
# Sandboxing: reads SteamVR's dashboard files, talks to 127.0.0.1:8087, writes one status file.
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=%t
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
cat > "$U/steamvr.service.d/sft-curvature.conf" <<UNIT
[Unit]
Wants=sft-vr-debugger.service sft-curvature.service
After=sft-vr-debugger.service

[Service]
ExecStopPost=-$D/sft-curvature restore
UNIT
sysctl_user daemon-reload

if sysctl_user is-active --quiet steamvr.service; then
    if "$D/sft-curvature" status >/dev/null 2>&1; then
        sysctl_user start sft-curvature.service
        say "Done: windows you float into the world now start curved."
    else
        say "Installed. It starts working the next time SteamVR starts (reboot, or restart SteamVR"
        say "from its menu): SteamVR opens the port it needs only at startup."
    fi
else
    say "Installed; active from the next SteamVR start."
fi
