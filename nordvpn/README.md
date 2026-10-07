# NordVPN that survives SteamOS updates

Installers that put NordVPN's own app into `/usr` (e.g. scripts that unlock the read-only
root and use pacman) lose it at **every SteamOS update**, because the update replaces the
whole system partition. Your settings in `/var` and `/etc` remain, but `nordvpn` is gone.

This uses NordVPN's WireGuard servers (NordLynx) as ordinary **NetworkManager** connections
instead. They live in `/etc/NetworkManager/system-connections`, which updates keep, and
nothing is installed system-wide.

```sh
./install.sh nordvpn
nordvpn-wg setup        # once: paste your access token into the hidden prompt
```

Get the token at Nord Account → NordVPN → **Access token** (Set up NordVPN manually →
Generate new token). It's used once to fetch your WireGuard key and isn't stored.

## Use
Each location shows up as **NordVPN <Country>** in the network menu of the system tray.
Click one to connect. Or from a terminal:

```sh
nordvpn-wg list          # locations; ● = connected
nordvpn-wg up US         # connect (disconnects any other NordVPN location)
nordvpn-wg status        # connected? public IP and location
nordvpn-wg down
nordvpn-wg add FR IT     # more locations (codes: nordvpn-wg countries)
nordvpn-wg remove JP
nordvpn-wg refresh       # re-pick the least loaded server for every location
```

Default locations: US, CA, GB, NL, CH, DE, JP (edit `~/.config/nordvpn-wg/locations`).

## Notes
- Each location is pinned to the server that was least loaded when it was created. Run
  `nordvpn-wg refresh` now and then (an active connection is reconnected to its new server).
- While connected, DNS goes only to NordVPN's resolvers (103.86.96.100 / 103.86.99.100).
- NordLynx is IPv4-only; IPv6 is disabled on the tunnel. There's no kill switch: if the
  tunnel drops, traffic goes out normally.
- Connections are saved through NetworkManager's D-Bus API (`AddConnection2`), because this
  NetworkManager's `nmcli` can't set WireGuard peers and `nmcli connection import`
  connects immediately.
- The private key lives in the system connection files (root-only) and in
  `~/.config/nordvpn-wg/private_key` (mode 600, for adding locations later).
