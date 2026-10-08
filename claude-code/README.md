# Claude Code (command line)

Anthropic's coding agent in the terminal: `claude` in Konsole. It reads and edits files in
the folder you start it in and runs commands there, asking first.

```sh
./install.sh claude-code
claude          # in any terminal; the first run logs in through your browser
```

Installed with [Anthropic's native installer](https://code.claude.com/docs/en/setup)
(`curl -fsSL https://claude.ai/install.sh | bash`) into `~/.local/bin/claude`, which
updates itself. Linux arm64 is supported, and it lives in your home folder, so SteamOS updates
leave it alone. If `claude` is already installed another way (for example Homebrew's
`claude-code` cask), the installer leaves it as it is.

**▶ Open** starts it in a new Konsole window in your home folder.

Remove: `./install.sh uninstall claude-code` (keeps `~/.claude` and your login).

## Credits
Made by [Anthropic](https://www.anthropic.com/claude-code). This tweak only runs Anthropic's installer.

---
Check: `./install.sh status claude-code` · Remove: `./install.sh uninstall claude-code`
