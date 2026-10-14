---
title: VSCodium
emoji: 🧑‍💻
category: Developer
tier: extras
summary: "VS Code without telemetry (Flathub, aarch64)"
what: "VS Code without telemetry, from Flathub."
why: >-
  Coding on the headset: Flathub has the aarch64 build; pairs with Arrow Pad and dictation.
author: VSCodium project
source: {relation: from, url: https://github.com/VSCodium/vscodium}
icon: {flatpak: com.vscodium.codium}
run: {label: Open}
changes: Flathub app (`com.vscodium.codium`)
access: –
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall vscodium`"
---
# VSCodium

[VSCodium](https://vscodium.com) is VS Code built from Microsoft's open-source code without
their telemetry and branding. Installed from Flathub (aarch64).

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** Flathub app (`com.vscodium.codium`)
> - **Undo:** `./install.sh uninstall vscodium`
<!-- /generated:glance -->

```sh
./install.sh install vscodium
```

- Extensions come from [Open VSX](https://open-vsx.org) (most popular ones are there, e.g.
  Codeium/Windsurf, Python, Rust Analyzer).
- It runs in the Flatpak sandbox: its built-in terminal is inside the sandbox. For a host shell,
  run `flatpak-spawn --host bash` in it, or set that as the terminal profile.
- Pairs well with [Arrow Pad](../arrowpad/) and [dictation](../dictation/) for editing in VR.

## Credits
VSCodium (MIT) by the VSCodium project; Flathub packaging by its maintainers. Not affiliated with
Microsoft. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status vscodium` · Remove: `./install.sh uninstall vscodium`
