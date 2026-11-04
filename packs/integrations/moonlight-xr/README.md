---
title: Moonlight XR for Frame
emoji: 🌙
category: Convenience
tier: extras
summary: Stream your PC's desktop and games to a big screen in VR, decoded in hardware
what: >-
  simplysanatori's Moonlight XR for Frame: a native game-streaming client for the Frame. Your
  PC's desktop or a game, streamed with Sunshine (or Apollo) on the PC, shows on a resizable screen
  in a virtual room, up to 2560×1440 in H.264 or HEVC decoded by the Frame's hardware, and you
  control it with the Frame's controllers. Pair once with a PIN; it starts from your Steam library.
why: >-
  A remote desktop such as KRdp asks for screen-sharing permission each time, and on an NVIDIA
  PC it encodes on the CPU (VA-API there can't encode H.264). Sunshine encodes on the graphics
  card, so the stream has lower latency, a higher frame rate and controller input, and its
  Desktop app covers games outside Steam too. Frame Tweaks installs the release it tested with
  its own installer and adds an app-menu entry and an Open button.
author: simplysanatori (Moonlight XR for Frame)
source:
  relation: from
  url: https://github.com/simplysanatori/moonlight-xr-steam-frame
experimental: >-
  A community project: its author wrote its Frame-specific code with Claude and has tested it
  on one Frame (SteamOS 0.4.5) against one Windows PC; 1.1.1 fixed its start on the newer
  SteamOS previews. It needs a PC running Sunshine or Apollo, which this tweak doesn't set up.
icon: {file: moonlight-xr.png}
run: {label: Open}
processes: [/MoonlightXRNative/app/moonlight-xr]
config: [~/.config/moonlight-xr]
changes: >-
  Whatever Moonlight XR's own installer sets up (its README lists it): the program in
  `~/Games/MoonlightXRNative`, a Non-Steam entry **Moonlight XR for Frame** in your Steam library
  with its artwork, SteamVR's per-app settings for it (90 Hz, no motion smoothing, the highest
  render resolution), its SteamVR dock icon, an app-menu entry Frame Tweaks adds
  (`frame-tweaks-moonlight-xr.desktop`), and its settings and pairing in
  `~/.config/moonlight-xr`
access: >-
  Connects to the PC you pair it with (the stream, its input and audio) over your network, the
  Frame's wireless adapter or USB; asks GitHub once a day for a newer release (off in its
  Settings)
survives_updates: Yes (everything is in your home folder)
undo: >-
  Uncheck it, or `./install.sh uninstall moonlight-xr`: its SteamVR dock icon and app-menu entry
  are removed and `~/Games/MoonlightXRNative` deleted (keeps your settings and pairing in
  `~/.config/moonlight-xr`). Remove its Non-Steam library entry yourself, and unpair the Frame in
  Sunshine's web page.
---
# Moonlight XR for Frame

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
simplysanatori's Moonlight XR for Frame: a native game-streaming client for the Frame. Your PC's desktop or a game, streamed with Sunshine (or Apollo) on the PC, shows on a resizable screen in a virtual room, up to 2560×1440 in H.264 or HEVC decoded by the Frame's hardware, and you control it with the Frame's controllers. Pair once with a PIN; it starts from your Steam library.

**Why on a Steam Frame:** A remote desktop such as KRdp asks for screen-sharing permission each time, and on an NVIDIA PC it encodes on the CPU (VA-API there can't encode H.264). Sunshine encodes on the graphics card, so the stream has lower latency, a higher frame rate and controller input, and its Desktop app covers games outside Steam too. Frame Tweaks installs the release it tested with its own installer and adds an app-menu entry and an Open button.
<!-- /generated:intro -->

Frame Tweaks installs it from its maker's release with the release's own installer, and adds
what makes it easy to start on the Frame.

**Before you install:** have Steam running on the Frame (its installer adds the library entry
through Steam; without Steam it installs the program and says the entry was skipped, and
installing again with Steam up adds it).

- **Install** (tick it): downloads the Moonlight XR release Frame Tweaks tested (`pin`), checks
  it against the hash recorded there, unpacks it and runs its `install.sh`. That copies the
  program to `~/Games/MoonlightXRNative/app`, adds **Moonlight XR for Frame** to your Steam
  library and sets SteamVR's settings for it. Then Frame Tweaks adds its app-menu entry. Its icon
  in the SteamVR dock stays grey until Steam has restarted once.
- **Open** on its row, or **Moonlight XR for Frame** in the app menu (Steam's **+** menu, the
  desktop's launcher), starts it the way its Steam library entry does. (Its installer's own menu
  entry is hidden: it's there for the SteamVR dock icon, so Frame Tweaks adds a visible one.)
- **Update:** Frame Tweaks' updates move it to a newer release once it's been tried on the Frame;
  your settings, pairing and library entry are kept. Its own window also says when a newer
  release is out.
- **Uninstall** (untick it): removes its SteamVR dock icon and app-menu entry and deletes
  `~/Games/MoonlightXRNative`. Your settings and pairing in `~/.config/moonlight-xr` stay
  (delete that folder too to forget them). Remove the library entry in Steam yourself (Manage →
  Remove non-Steam game from your library).

## On your PC: Sunshine

Moonlight XR streams from [Sunshine](https://github.com/LizardByte/Sunshine) (or
[Apollo](https://github.com/ClassicOldSong/Apollo)) on your PC. On Universal Blue systems (the ones with `ujust`),
`ujust setup-sunshine` installs and starts it. Elsewhere, Sunshine's own instructions cover it.

- **Encoder:** Sunshine encodes on the graphics card (NVENC on NVIDIA, VCE/VA-API on AMD), which
  is what makes the stream smooth. Its log says which encoder it picked.
- **One monitor:** Sunshine streams one monitor at a time; pick it in Sunshine's settings
  (Audio/Video, Display). On Linux it can't make a virtual display, so the stream has that
  monitor's resolution.
- **Network:** the Frame has to reach the PC on Sunshine's ports (TCP 47984, 47989, 47990, 48010;
  UDP 47998–48000, 48002, 48010). That `ujust` recipe opens them.
- Sunshine's web page is at `https://localhost:47990` on the PC. The first visit asks you to make
  its username and password.

## Use

1. Start **Moonlight XR for Frame** from your Steam library. The first screen is the list of
   PCs, shown flat in the headset. (If you used the Moonlight Flatpak on the Frame, your PCs and
   pairing are copied over.)
2. Select your PC (or **+** to type its address). Moonlight shows a PIN.
3. Type the PIN on Sunshine's web page (PIN page) on the PC.
4. Select the PC again, then **Desktop** or a game. The stream opens on a screen in the headset;
   when it ends, the flat window comes back.

Its [user guide](https://github.com/simplysanatori/moonlight-xr-steam-frame/blob/main/docs/USER_GUIDE.md)
explains the controls, rooms and settings. Its logs (`~/Games/MoonlightXRNative/*.log`) hold your
PC's name and addresses: don't post them as they are.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** Whatever Moonlight XR's own installer sets up (its README lists it): the program in `~/Games/MoonlightXRNative`, a Non-Steam entry **Moonlight XR for Frame** in your Steam library with its artwork, SteamVR's per-app settings for it (90 Hz, no motion smoothing, the highest render resolution), its SteamVR dock icon, an app-menu entry Frame Tweaks adds (`frame-tweaks-moonlight-xr.desktop`), and its settings and pairing in `~/.config/moonlight-xr`
- **🧪 Experimental:** A community project: its author wrote its Frame-specific code with Claude and has tested it on one Frame (SteamOS 0.4.5) against one Windows PC; 1.1.1 fixed its start on the newer SteamOS previews. It needs a PC running Sunshine or Apollo, which this tweak doesn't set up.
- **Unusual access:** Connects to the PC you pair it with (the stream, its input and audio) over your network, the Frame's wireless adapter or USB; asks GitHub once a day for a newer release (off in its Settings)
- **Undo:** Uncheck it, or `./install.sh uninstall moonlight-xr`: its SteamVR dock icon and app-menu entry are removed and `~/Games/MoonlightXRNative` deleted (keeps your settings and pairing in `~/.config/moonlight-xr`). Remove its Non-Steam library entry yourself, and unpair the Frame in Sunshine's web page.
<!-- /generated:changes -->

## Credits

Moonlight XR for Frame is by [simplysanatori](https://github.com/simplysanatori/moonlight-xr-steam-frame)
(GPL-3.0), a port of [Moonlight XR](https://github.com/Gilleece/moonlight-android-xr) by Sean
Gilleece, built on [Moonlight](https://github.com/moonlight-stream). Frame Tweaks downloads its
release and runs its installer, and copies none of its code. This tweak's icon, `moonlight-xr.png`, is its own app
icon (`app/assets/branding/icon-256.png` in its release), unchanged: the disc of Moonlight XR's
logo, their mark, GPL-3.0 like the app, not MIT like the rest of Frame Tweaks
(`moonlight-xr.png.license`). See also [CREDITS.md](../../../CREDITS.md).
