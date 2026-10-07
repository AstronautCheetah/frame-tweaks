# Firefox: anti-fingerprinting

The Frame makes a browser unusually easy to fingerprint: very few browsers report a
**Linux aarch64** platform, an **Adreno** GPU, or the VR desktop's odd window size, and the
timezone gives away your location even behind a VPN. This turns on Firefox's strongest
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

Check the result at <https://coveryourtracks.eff.org>.

If a site breaks, use a separate Firefox profile without RFP for that site, rather than
adding per-site exceptions, which themselves make you more identifiable. For blending in
with a large crowd, Tor Browser remains stronger than any single-browser setting.
Adding uBlock Origin (from addons.mozilla.org) also blocks many fingerprinting scripts.
