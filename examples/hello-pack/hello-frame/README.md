---
title: Hello Frame
emoji: 👋
category: Examples
tier: extras
summary: An example tweak, a menu entry that greets you (with a setting for the greeting)
what: >-
  Adds "Hello Frame" to the app menu (desktop and Steam's VR "+" menu). Opening it shows a
  notification with your greeting, which you choose in its settings.
why: To show how a tweak is put together; copy it to start your own.
author: Frame Tweaks (example)
icon: {theme: face-smile}
run: {label: Greet}
processes: []
settings:
  file: ~/.config/frame-tweaks/hello-frame.conf
  format: shell
  about: What Hello Frame says.
  note: Applies the next time it greets you.
  options:
    - key: HELLO_GREETING
      title: Greeting
      default: hello
      choices:
        - {label: Hello, value: hello}
        - {label: Good to see you, value: welcome}
        - {label: Ahoy, value: ahoy}
changes: "`~/.local/bin/hello-frame` and its app-menu entry"
access: None beyond your home folder
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall hello-frame`"
test: {offline: true, keeps: [.config/frame-tweaks/hello-frame.conf]}
---
# Hello Frame

An example tweak. Everything above the second `---` is its manifest: what the installer
window, `./install.sh` and the docs know about it. The rest is its README.

- `install.sh` installs it, `uninstall.sh` removes it, `status.sh` says whether it's
  installed (`status_ok`, `status_missing`, `status_warn`).
- `run.sh` is the installer window's **Greet** button (`run: label:`).
- `hello-frame` is the program it installs; `hello-frame.desktop` its menu entry.
