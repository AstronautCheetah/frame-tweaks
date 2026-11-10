---
title: "Bluetooth headphones: music only"
emoji: 🎧
category: Hardware
tier: extras
summary: Bluetooth headphones and earbuds connect for music (A2DP) only, without the call profile
what: >-
  The Frame stops offering Bluetooth audio devices the hands-free and headset profiles (the
  ones with a microphone and a voice channel). Headphones and earbuds then connect for music
  (A2DP) only, and stay on that profile. Their microphone isn't used; SteamVR uses the Frame's
  own.
why: >-
  With both profiles on offer, a pair of earbuds is connected on the call profile too, with its
  voice channel open. When the Frame goes to sleep, that channel is torn down mid-stream, and
  some earbuds (Bose QuietComfort Earbuds II here) never answer the Frame again until they're
  reset and paired anew. The music profile alone reconnects cleanly. The Frame's own microphone
  is what SteamVR uses anyway, so the call profile gives nothing in VR.
author: Frame Tweaks
icon: {theme: audio-headphones}
changes: >-
  A WirePlumber setting, `~/.config/wireplumber/wireplumber.conf.d/90-frame-tweaks-bt-music-only.conf`
  (the Bluetooth roles offered: music, not calls)
access: None
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall bt-music-only`"
---
# Bluetooth headphones: music only

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
The Frame stops offering Bluetooth audio devices the hands-free and headset profiles (the ones with a microphone and a voice channel). Headphones and earbuds then connect for music (A2DP) only, and stay on that profile. Their microphone isn't used; SteamVR uses the Frame's own.

**Why on a Steam Frame:** With both profiles on offer, a pair of earbuds is connected on the call profile too, with its voice channel open. When the Frame goes to sleep, that channel is torn down mid-stream, and some earbuds (Bose QuietComfort Earbuds II here) never answer the Frame again until they're reset and paired anew. The music profile alone reconnects cleanly. The Frame's own microphone is what SteamVR uses anyway, so the call profile gives nothing in VR.
<!-- /generated:intro -->

Bluetooth headphones and earbuds connect for music (A2DP) only, without the call profile.

## Install

```sh
./install.sh install bt-music-only
```

It applies when WirePlumber (the sound system's session manager) restarts: right away, unless
SteamVR is running, then with the Frame's next start; the status says which. Headphones connected
before it applied keep the profiles they were given until they reconnect.

## What it does

The Frame offers a Bluetooth audio device two kinds of connection: the music profile (A2DP,
stereo, the device's own codecs) and the call profile (HSP/HFP: a mono voice channel each way,
for the device's microphone). This tweak leaves the call profile out. Headphones then connect
for music only, their microphone isn't used, and nothing switches them to the call profile when
an app opens a microphone.

To use a headset's microphone with the Frame again, uninstall it.

## Good to know

- **SteamVR's microphone is the Frame's own**, so nothing in VR loses a microphone. In desktop
  mode, apps that record use the Frame's microphone too.
- **The call profile sounded worse anyway:** on it, music drops to mono at telephone quality.
  With the music profile alone, the device can't fall into that by mistake.
- **After the Frame sleeps**, every Bluetooth link drops and the device reconnects when the
  Frame wakes. With the music profile alone, that reconnect is the simple case.

## How it works

WirePlumber decides which Bluetooth roles the Frame plays (`bluez5.roles`). The tweak's file
lists the music roles (A2DP, and LE Audio's BAP) and leaves out `hfp_ag`, `hfp_hf`, `hsp_ag` and
`hsp_hs`: BlueZ then has no handler for the call profiles, so a device's hands-free service is
never connected. The file is read when WirePlumber starts; the tweak restarts it on install and
uninstall unless SteamVR is running (Valve's VR audio compositor runs inside WirePlumber, and
SteamVR doesn't survive its restart), and then the status says the setting waits for the Frame's
next start.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** A WirePlumber setting, `~/.config/wireplumber/wireplumber.conf.d/90-frame-tweaks-bt-music-only.conf` (the Bluetooth roles offered: music, not calls)
- **Undo:** `./install.sh uninstall bt-music-only`
<!-- /generated:changes -->

## Credits
Frame Tweaks.
