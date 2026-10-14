---
title: Firefox privacy
emoji: 🕵️
category: Privacy & security
tier: extras
summary: >-
  Makes Firefox harder for websites to track: strong anti-fingerprinting, letterboxing and
  WebRTC limits
what: >-
  Makes Firefox harder for websites to track you: it turns on Firefox's strongest
  anti-fingerprinting (`resistFingerprinting`, from Tor Browser), with letterboxing, WebRTC
  limits, strict tracking protection, HTTPS-only mode and daily re-randomized canvas readings.
why: >-
  The Frame's hardware (Adreno GPU, the VR desktop's unusual window sizes, touch input) is rare
  among browsers, so it's easy to fingerprint.
author: Mozilla / Tor Project (resistFingerprinting); settings by Frame Tweaks
icon: {flatpak: org.mozilla.firefox, theme: internet-web-browser}
run: {label: Open}
changes: Preferences in Firefox's profile (`user.js`)
access: –
survives_updates: Yes (everything is in your home folder)
undo: >-
  `./install.sh uninstall firefox` with Firefox closed (it also clears the settings from
  `prefs.js`); if Firefox is running, quit it and run it again, or reset them in `about:config`
---
# Firefox privacy

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Makes Firefox harder for websites to track you: it turns on Firefox's strongest anti-fingerprinting (`resistFingerprinting`, from Tor Browser), with letterboxing, WebRTC limits, strict tracking protection, HTTPS-only mode and daily re-randomized canvas readings.

**Why on a Steam Frame:** The Frame's hardware (Adreno GPU, the VR desktop's unusual window sizes, touch input) is rare among browsers, so it's easy to fingerprint.
<!-- /generated:intro -->

## Install
Needs Firefox from Flathub, started at least once (so it has a profile). Then tick it in the
Frame Tweaks window, or:

```sh
./install.sh install firefox
```

Restart Firefox afterwards. Check the result at <https://coveryourtracks.eff.org>.

## Use
Nothing else to do: the settings apply at every Firefox start. What sites see:

- a common platform (**Linux x86_64**), a generic GPU and fewer hardware details
- a window size rounded to common steps (**letterboxing**: grey margins around pages)
- timezone **UTC** (site clocks and calendars may show UTC times)
- a **light** color scheme
- English pages requested; less precise timers; a fixed set of fonts
- canvas, WebGL and audio readings **randomized**, with a new key **every day**
- WebRTC limited to the default network route (no local or LAN addresses), which matters with
  a VPN

It also turns on Strict tracking protection (blocks known fingerprinting scripts) and
HTTPS-only mode. Saved passwords and Firefox Sync keep working.

## How it works
It adds a block of settings, between `// >>> frame-tweaks` and `// <<< frame-tweaks` markers,
to `user.js` in your default Firefox profile. Firefox reads `user.js` at every start, so these
values win over the Settings page and Sync. Anything else you have in `user.js` is kept. The
settings are in [user.js](user.js), with a comment on each.

The main one is `privacy.resistFingerprinting` (RFP), the Tor Browser approach: instead of
hiding, every RFP Firefox reports the same values.

## Good to know
- **Cover Your Tracks still says "unique".** In our tests it showed about 18 bits even with
  everything working. The values it flags (Firefox on Linux, RFP's font list, the letterboxed
  window size, 5 touch points, 4 CPU cores, the UTC timezone, WebGL vendor "Mozilla") are the
  fixed values that **every** RFP Firefox reports. EFF's comparison set has few RFP users, so
  this shared signature looks rare there. Changing any of them would make you stand out from
  other RFP users, so don't. Canvas and WebGL show as "randomized": no stable value.
- **If a site breaks,** use a separate Firefox profile without RFP for that site, rather than
  adding per-site exceptions, which themselves make you easier to identify.
- To blend in with a large crowd, Tor Browser remains stronger than any single-browser setting.
  An ad blocker such as uBlock Origin (from addons.mozilla.org) also blocks many fingerprinting
  scripts.
- **Removing it** takes the block out of `user.js` and, if Firefox is closed, the same settings
  out of `prefs.js` (a copy is kept as `prefs.js.frame-tweaks-bak`). If Firefox is running, quit
  it and remove again, or reset the settings in `about:config`.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** Preferences in Firefox's profile (`user.js`)
- **Undo:** `./install.sh uninstall firefox` with Firefox closed (it also clears the settings from `prefs.js`); if Firefox is running, quit it and run it again, or reset them in `about:config`
<!-- /generated:changes -->

## Credits
`resistFingerprinting` comes from the Tor Project's Tor Browser, upstreamed into Firefox (MPL-2.0). Results measured with [EFF Cover Your Tracks](https://coveryourtracks.eff.org). See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status firefox` · Remove: `./install.sh uninstall firefox`
