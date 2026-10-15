#!/bin/bash
# NordVPN (NordLynx/WireGuard) as NetworkManager connections that survive SteamOS updates.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ensure_path
ensure_tweaks_venv
install_i18n
install_py_tool "$TWEAK_DIR/nordvpn-wg"

# Tray icon (SteamOS has no Plasma network applet). PyQt6 venv shared with arrowpad.
ensure_qt_venv || die "$(t "couldn't install PyQt6")"
sed "1s|.*|#!$QT_VENV/bin/python|" "$TWEAK_DIR/nordvpn-tray" | write_file "$BIN/nordvpn-tray" 755
install_icon frame-tweaks-nordvpn
install_desktop "$TWEAK_DIR/nordvpn-tray.desktop"
mkdir -p "$HOME/.config/autostart"
sed "s|@BIN@|$BIN|g" "$TWEAK_DIR/nordvpn-tray.desktop" > "$HOME/.config/autostart/nordvpn-tray.desktop"
# Autostart starts the tray; KDE's session restore must not start a second copy at login.
save_kconfig nordvpn ksmserverrc General excludeApps          # restored on uninstall
excl=$(kreadconfig6 --file ksmserverrc --group General --key excludeApps)
case ",$excl," in *,nordvpn-tray,*) ;; *)
    kwriteconfig6 --file ksmserverrc --group General --key excludeApps "${excl:+$excl,}nordvpn-tray" ;; esac

say "$(t 'Installed. Now run:  %s   (asks for your NordVPN access token once)' "nordvpn-wg setup")"
say "$(t "The tray icon starts with desktop mode (or launch 'NordVPN Tray' now).")"
