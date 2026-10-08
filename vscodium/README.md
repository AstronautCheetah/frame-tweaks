# VSCodium

[VSCodium](https://vscodium.com) is VS Code built from Microsoft's open-source code without
their telemetry and branding. Installed from Flathub (aarch64).

```sh
./install.sh vscodium
```

- Extensions come from [Open VSX](https://open-vsx.org) (most popular ones are there, e.g.
  Codeium/Windsurf, Python, Rust Analyzer).
- It runs in the Flatpak sandbox: its built-in terminal is inside the sandbox. For a host shell,
  run `flatpak-spawn --host bash` in it, or set that as the terminal profile.
- Pairs well with [Arrow Pad](../arrowpad/) and [dictation](../dictation/) for editing in VR.

## Credits
VSCodium (MIT) by the VSCodium project; Flathub packaging by its maintainers. Not affiliated with
Microsoft. See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status vscodium` · Remove: `./install.sh uninstall vscodium`
