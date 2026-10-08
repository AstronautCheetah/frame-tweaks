# Claude Desktop (official Linux arm64 beta)

Anthropic ships Claude Desktop for Linux as an apt package for Ubuntu/Debian (x86_64 and
arm64). SteamOS has no apt and a read-only root, so this unpacks the arm64 `.deb`
into `~/.local/opt/claude-desktop`, after verifying its SHA256 against Anthropic's repo index.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** `~/.local/opt/claude-desktop`, `claude-desktop-update`, menu entry
> - **Unusual access:** Checks against the SHA256 in Anthropic's apt index
> - **Undo:** `./install.sh uninstall claude-desktop`
<!-- /generated:glance -->

```sh
./install.sh claude-desktop
claude-desktop-update     # later: fetch a newer version if there is one
```

It doesn't auto-update in this form, so run `claude-desktop-update` now and then.

## Credits
Claude Desktop is Anthropic's; this only downloads it from Anthropic's apt repository and verifies its checksum. Not affiliated with Anthropic. See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status claude-desktop` · Remove: `./install.sh uninstall claude-desktop`
