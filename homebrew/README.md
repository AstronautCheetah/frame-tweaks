# Homebrew

[Homebrew](https://brew.sh) is a package manager that installs programs into
`/home/linuxbrew`, outside SteamOS's read-only system partition, so SteamOS updates don't
remove them. Several tweaks use it, and they offer to install it when it's missing; this row
lets you see it, and install it up front.

```sh
./install.sh homebrew
brew install <program>      # anything from https://formulae.brew.sh
brew upgrade                # update everything it installed
```

**Used by:** [Dictation](../dictation/) (wl-clipboard, and whisper.cpp when whisper-frame isn't installed),
[Android Mirror](../adb-scrcpy/) (scrcpy) and the [shared clipboard](../clipboard/) (Rust, to build it). Claude Code may also have been installed
with it (`brew install --cask claude-code`).

**Installing needs your sudo password once**, to create `/home/linuxbrew`. If your user has no
password yet, set one with `passwd` first. After that, Homebrew never needs sudo.

**Removing:** `./install.sh uninstall homebrew` leaves Homebrew in place, because other tweaks'
programs live in it; it prints Homebrew's own uninstaller command if you really want it gone.

## Credits
[Homebrew](https://github.com/Homebrew/brew) (BSD-2-Clause), installed with its official
installer. See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status homebrew` · Remove: `./install.sh uninstall homebrew`
