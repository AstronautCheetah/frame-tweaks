# Claude Desktop (official Linux arm64 beta)

Anthropic ships Claude Desktop for Linux as an apt package for Ubuntu/Debian (x86_64 and
arm64). SteamOS has no apt and a read-only root, so this unpacks the arm64 `.deb`
into `~/.local/opt/claude-desktop`, after verifying its SHA256 against Anthropic's repo index.

```sh
./install.sh claude-desktop
claude-desktop-update     # later: fetch a newer version if there is one
```

It doesn't auto-update in this form, so run `claude-desktop-update` now and then.

---
Check: `./install.sh status claude-desktop` · Remove: `./install.sh uninstall claude-desktop`
