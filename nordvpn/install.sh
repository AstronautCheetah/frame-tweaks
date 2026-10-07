#!/bin/bash
# NordVPN (NordLynx/WireGuard) as NetworkManager connections that survive SteamOS updates.
source "$(dirname "$0")/../lib/common.sh"
ensure_path
ensure_tweaks_venv
install_py_tool "$REPO_DIR/nordvpn/nordvpn-wg"
say "Installed. Now run:  nordvpn-wg setup   (asks for your NordVPN access token once)"
