# Firefox: anti-fingerprinting

The Frame makes a browser easier to fingerprint: an **Adreno** GPU, the VR desktop's odd
window size and touch input are rare, and the timezone gives away your location even behind a
VPN. (Firefox already reports Linux x86_64 on aarch64 by itself.) This turns on Firefox's strongest
built-in protection, `privacy.resistFingerprinting` (RFP, the Tor Browser approach), via a
`user.js` in the default profile, so it's applied at every start and Sync can't undo it.

```sh
./install.sh firefox            # then restart Firefox
firefox/install.sh --remove     # take it out again
```

What sites see with it on:
- platform **Linux x86_64**, a generic GPU and reduced hardware details
- window size rounded to common steps (**letterboxing**: grey margins around pages)
- timezone **UTC** (site clocks/calendars may show UTC times)
- **light** color scheme (`prefers-color-scheme` is reported as light)
- English pages requested; reduced timer precision; fixed fonts
- WebRTC limited to the default route (no local/LAN addresses), which matters with a VPN

Kept: Strict tracking protection (blocks known fingerprinting scripts), HTTPS-only mode,
saved passwords and Firefox Sync.

- canvas/WebGL/audio readings **randomized**, re-keyed **daily**

Check the result at <https://coveryourtracks.eff.org>.

## Reading the Cover Your Tracks result
Expect "**unique**" with ~18 bits even when everything works. The remaining values (Firefox
version on Linux, RFP's font allowlist, letterboxed 1400×900, `maxTouchPoints` 5,
`hardwareConcurrency` 4, UTC/Atlantic/Reykjavik, WebGL vendor "Mozilla") are the **fixed values
every RFP Firefox reports**, verified here with a headless Firefox that has no touch device
(RFP on: 5 touch points, 4 cores; off: 0 and 8). EFF's comparison set has few RFP users, so
that shared signature looks rare there. Changing any of those values would make you stand
out *from other RFP users*, so don't. Canvas/WebGL show as "randomized": no stable hash.

If a site breaks, use a separate Firefox profile without RFP for that site, rather than
adding per-site exceptions, which themselves make you more identifiable. For blending in
with a large crowd, Tor Browser remains stronger than any single-browser setting.
Adding uBlock Origin (from addons.mozilla.org) also blocks many fingerprinting scripts.

## Credits
`resistFingerprinting` comes from the Tor Project's Tor Browser, upstreamed into Firefox (MPL-2.0). Results measured with [EFF Cover Your Tracks](https://coveryourtracks.eff.org). See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status firefox` · Remove: `./install.sh uninstall firefox`
