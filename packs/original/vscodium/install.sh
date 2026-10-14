#!/bin/bash
# VSCodium: VS Code without Microsoft's telemetry/branding (Flathub).
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
say "Installing VSCodium (Flathub, about 245 MB)"
flatpak install -y --noninteractive flathub com.vscodium.codium
touch "$APPS"     # Steam's "+" menu rescans
say "Open 'VSCodium' from the app menu. Extensions come from Open VSX."
