---
title: VSCodium
emoji: 🧑‍💻
category: Developer
tier: extras
summary: "VS Code without Microsoft's telemetry, from Flathub"
what: >-
  VSCodium, the code editor VS Code built from its open-source code without Microsoft's telemetry
  and branding. Installed from Flathub.
why: >-
  For coding on the headset: Flathub has a build for the Frame's ARM processor, and it works well
  with Arrow Pad and Dictation for typing in VR.
author: VSCodium project
source: {relation: from, url: https://github.com/VSCodium/vscodium}
icon: {flatpak: com.vscodium.codium}
run: {label: Open}
config: [~/.var/app/com.vscodium.codium]
app: VSCodium
changes: Flathub app `com.vscodium.codium` (system-wide Flatpak)
access: >-
  VSCodium's own Flatpak permissions: all your files, the network, and running commands outside
  its sandbox
survives_updates: Yes (SteamOS keeps Flatpak apps across updates)
undo: >-
  `./install.sh uninstall vscodium` (keeps your settings and extensions in
  `~/.var/app/com.vscodium.codium`)
---
# VSCodium

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
VSCodium, the code editor VS Code built from its open-source code without Microsoft's telemetry and branding. Installed from Flathub.

**Why on a Steam Frame:** For coding on the headset: Flathub has a build for the Frame's ARM processor, and it works well with Arrow Pad and Dictation for typing in VR.
<!-- /generated:intro -->

## Install

Tick it in the Frame Tweaks window, or:

```sh
./install.sh install vscodium
```

It downloads about 245 MB from Flathub. Nothing else to do.

## Use

Open **VSCodium** from the app menu, from Steam's VR **+** menu, or with **▶ Open** in the Frame
Tweaks window.

- Extensions come from [Open VSX](https://open-vsx.org), not Microsoft's marketplace. Most
  popular extensions are there, but not all.
- VSCodium runs as a Flatpak, in a sandbox, so its built-in terminal opens inside that sandbox,
  where your usual system tools may be missing. For a normal shell, run
  `flatpak-spawn --host bash` in it, or make that your terminal profile.
- For typing in VR, it pairs well with [Arrow Pad](../../original/arrowpad/) (arrows, Home/End, Ctrl
  shortcuts) and [Dictation](../../original/dictation/).

## Good to know

- Updates come through Flathub, like your other Flatpak apps (for example in Discover).
- Uninstalling removes the app but keeps your settings and extensions.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (SteamOS keeps Flatpak apps across updates)
- **Changes:** Flathub app `com.vscodium.codium` (system-wide Flatpak)
- **Unusual access:** VSCodium's own Flatpak permissions: all your files, the network, and running commands outside its sandbox
- **Undo:** `./install.sh uninstall vscodium` (keeps your settings and extensions in `~/.var/app/com.vscodium.codium`)
<!-- /generated:changes -->

## Credits
[VSCodium](https://github.com/VSCodium/vscodium) (MIT) by the VSCodium project; Flathub packaging
by its maintainers. Not affiliated with Microsoft. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status vscodium` · Remove: `./install.sh uninstall vscodium`
