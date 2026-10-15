<!-- Thanks for helping. One topic per pull request; CONTRIBUTING.md has the details. -->

## What and why

<!-- What changes for someone using the Frame, and why. Link the issue if there is one. -->

## How I tested it

<!-- e.g. "dev/check.sh on Fedora 42", or "on my Frame, SteamOS 0.4.5, SteamVR build …:
     installed, used it in VR, uninstalled". Say what you couldn't test. -->

## Checklist

- [ ] `dev/check.sh` passes (it runs what CI runs)
- [ ] Changed a manifest (a tweak's README front matter)? I ran `dev/gen-docs.py`
- [ ] Changed text the window or a program shows? It's marked (`_("…")`, `t '…'`), and I ran
      `dev/i18n.py extract` (or a maintainer will)
- [ ] English only: I didn't translate (that's fine; the maintainers do it before the release)
- [ ] Anything users will notice is in CHANGELOG.md under "Unreleased"
