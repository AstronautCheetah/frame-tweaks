# ydotool (shared helper)

Keystroke injection via the kernel's uinput: the only way for ordinary programs to type
into any app under KDE Wayland. Installed automatically by `dictation` and `arrowpad`.

- `ydotool` / `ydotoold` binaries from Arch Linux ARM → `~/.local/bin`
- user service `ydotoold.service`, socket `/run/user/$UID/.ydotool_socket`
- requires write access to `/dev/uinput` (the `input` group, which SteamOS grants by default)

---
Check: `./install.sh status ydotool` · Remove: `./install.sh uninstall ydotool`
