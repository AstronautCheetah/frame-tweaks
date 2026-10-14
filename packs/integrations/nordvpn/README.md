---
title: NordVPN (WireGuard)
emoji: 🌐
category: Privacy & security
tier: extras
summary: >-
  NordVPN as NetworkManager connections with a tray icon; survives SteamOS updates
what: >-
  NordVPN servers in several countries as built-in network connections, with a tray icon.
  Survives SteamOS updates.
why: >-
  The usual NordVPN install goes into `/usr`, which every SteamOS update wipes, and the Frame's
  desktop has no network applet to switch VPNs.
author: Frame Tweaks; uses NordVPN's servers and API
icon: {file: frame-tweaks-nordvpn.png}
run: {label: Tray}
processes: [^~/.local/share/arrowpad/venv/bin/python ~/.local/bin/nordvpn-tray]
changes: >-
  `nordvpn-wg`, tray app and its PyQt6 Python environment (shared with Arrow Pad), KDE autostart
  entry and session-restore setting (`ksmserverrc`, so the tray isn't started twice),
  `~/.config/nordvpn-wg` (your WireGuard key and locations)
access: >-
  **Outside your home folder:** NetworkManager WireGuard connections (via NetworkManager's
  D-Bus API and `nmcli`); uses your NordVPN access token once, to fetch your WireGuard key
survives_updates: >-
  Yes (its connections live in NetworkManager's settings, which updates keep)
undo: >-
  `./install.sh uninstall nordvpn` (also deletes the connections, your key and locations; the ↻
  reinstall keeps them)
---
# NordVPN (WireGuard)

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
NordVPN servers in several countries as built-in network connections, with a tray icon. Survives SteamOS updates.

**Why on a Steam Frame:** The usual NordVPN install goes into `/usr`, which every SteamOS update wipes, and the Frame's desktop has no network applet to switch VPNs.
<!-- /generated:intro -->

## Install
You need a NordVPN subscription. Tick it in the Frame Tweaks window, or:

```sh
./install.sh install nordvpn
```

Then, once, in a terminal (Konsole in desktop mode):

```sh
nordvpn-wg setup
```

It asks for a NordVPN **access token** in a hidden prompt: nothing shows while you paste (in
Konsole, Ctrl+Shift+V), then press Enter. To get a token, sign in to your Nord Account on the
web, open **NordVPN**, find **Get access token** (under advanced settings), confirm by email
and generate one. It's shown only once, and a short-lived one is enough. Don't put it in a file
or on a command line: `nordvpn-wg` uses it once to fetch your WireGuard key and doesn't save it.
Your NordVPN username and password ("service credentials") aren't used.

Setup then creates a connection for each default location: US, CA, GB, NL, CH, DE and JP.

## Use
SteamOS on the Frame has no network applet in the desktop's taskbar, so this adds a **NordVPN
tray icon**, which starts with desktop mode (or use **Tray** on this tweak's row). Grey means
disconnected, green connected, yellow working. Click it for a menu: pick a location, disconnect,
show your public IP, or pick the least-loaded servers again.

From a terminal:

```sh
nordvpn-wg list          # locations; ● = connected
nordvpn-wg up US         # connect (disconnects any other NordVPN location)
nordvpn-wg status        # connected? public IP and location
nordvpn-wg down          # disconnect
nordvpn-wg add FR IT     # more locations (country codes: nordvpn-wg countries)
nordvpn-wg remove JP
nordvpn-wg refresh       # pick the least-loaded server again for every location
```

Your locations are listed in `~/.config/nordvpn-wg/locations`.

## How it works
NordVPN's own Linux app installs into `/usr`, on SteamOS's read-only system partition, which
every SteamOS update replaces. Instead, `nordvpn-wg` uses NordVPN's WireGuard servers (NordLynx)
as ordinary **NetworkManager** connections, named "NordVPN <country>". NetworkManager keeps them
in `/etc/NetworkManager/system-connections`, which updates keep, and nothing is installed into
the system.

Connections are created through NetworkManager's D-Bus API, so the private key never appears on
a command line or in a temporary file, and creating one doesn't connect it.

## Good to know
- Each location uses the server that was least loaded when it was created. Run
  `nordvpn-wg refresh` now and then; an active connection reconnects to its new server.
- While connected, DNS goes to NordVPN's resolvers (103.86.96.100 and 103.86.99.100).
- **IPv4 only:** IPv6 is turned off on the tunnel. On a network that has IPv6, IPv6 traffic goes
  around the VPN (check with `ip -6 addr show scope global`).
- **No kill switch:** if the tunnel drops, traffic goes out normally.
- Your WireGuard private key is stored in the connection files (readable only by root) and in
  `~/.config/nordvpn-wg/private_key` (readable only by you), so locations can be added later.
  Removing the tweak deletes both, along with the connections. Reinstalling it (↻) keeps them.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (its connections live in NetworkManager's settings, which updates keep)
- **Changes:** `nordvpn-wg`, tray app and its PyQt6 Python environment (shared with Arrow Pad), KDE autostart entry and session-restore setting (`ksmserverrc`, so the tray isn't started twice), `~/.config/nordvpn-wg` (your WireGuard key and locations)
- **Unusual access:** **Outside your home folder:** NetworkManager WireGuard connections (via NetworkManager's D-Bus API and `nmcli`); uses your NordVPN access token once, to fetch your WireGuard key
- **Undo:** `./install.sh uninstall nordvpn` (also deletes the connections, your key and locations; the ↻ reinstall keeps them)
<!-- /generated:changes -->

## Credits
Uses NordVPN's public server API and NordLynx (WireGuard). D-Bus via [jeepney](https://gitlab.com/takluyver/jeepney) (MIT). NordVPN is a trademark of Nord Security; this project isn't affiliated with it. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status nordvpn` · Remove: `./install.sh uninstall nordvpn`
