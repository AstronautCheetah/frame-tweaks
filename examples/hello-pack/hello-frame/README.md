---
title: Hello Frame
emoji: 👋
category: Examples
tier: extras
summary: An example tweak, a menu entry that greets you (with a setting for the greeting)
what: >-
  Adds "Hello Frame" to the app menu (desktop and Steam's VR "+" menu). Opening it shows a
  notification with your greeting, which you choose in its settings.
why: >-
  It's a starting point for your own tweaks: small, but it uses most of what a tweak can do (a
  program, a menu entry, a Run button and a setting).
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
undo: >-
  `./install.sh uninstall hello-frame` (keeps `~/.config/frame-tweaks/hello-frame.conf`)
test: {offline: true, keeps: [.config/frame-tweaks/hello-frame.conf]}
---
# Hello Frame

Adds "Hello Frame" to the app menu (desktop and Steam's VR "+" menu). Opening it shows a notification with your greeting, which you choose in its settings.

**Why on a Steam Frame:** It's a starting point for your own tweaks: small, but it uses most of what a tweak can do (a program, a menu entry, a Run button and a setting).

> **For pack authors:** copy this folder to start your own tweak. Everything above the second
> `---` line is its manifest, explained in [docs/mods.md](../../../docs/mods.md). The rest is
> its README, laid out like the official tweaks' READMEs: the two paragraphs above (from `what`
> and `why`), then Install, Use, Settings, How it works, What it changes (from `changes`,
> `access`, `survives_updates` and `undo`), Credits and the Check/Remove line.

## Install

Copy the [Hello pack](../) folder into `~/.local/share/frame-tweaks/packs/` and trust it
(**🧩 Packs → Trust…** in the Frame Tweaks window, or `./install.sh mods trust "Hello pack"`).
Then tick **Hello Frame** in the Frame Tweaks window, or:

```sh
./install.sh install hello-frame
```

Nothing else to do.

## Use

Open **Hello Frame** from the app menu or Steam's VR **+** menu, or press **▶ Greet** in the
Frame Tweaks window. A notification says hello to you by your user name.

## Settings

Choose the greeting (**Hello**, **Good to see you** or **Ahoy**) on its settings page in the
Frame Tweaks window, or in a terminal:

```sh
./install.sh settings hello-frame HELLO_GREETING=ahoy
```

It's saved in `~/.config/frame-tweaks/hello-frame.conf` and used the next time it greets you.

## How it works

- `install.sh` copies the program into `~/.local/bin` and adds its menu entry;
  `uninstall.sh` removes both and keeps your settings; `status.sh` prints one line saying
  whether it's installed (`status_ok`, `status_missing` or `status_warn`).
- `run.sh` is the Frame Tweaks window's **Greet** button (`run: {label: Greet}` in the
  manifest). It opens the menu entry (`gtk-launch hello-frame`) rather than the program itself,
  so anything guarding that entry, such as a wallet gate, applies.
- `hello-frame` is the program it installs: it reads the settings file and shows the
  notification. `hello-frame.desktop` is its menu entry.

## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `~/.local/bin/hello-frame` and its app-menu entry
- **Unusual access:** None beyond your home folder
- **Undo:** `./install.sh uninstall hello-frame` (keeps `~/.config/frame-tweaks/hello-frame.conf`)

## Credits
An example by Frame Tweaks, under its [MIT licence](../../../LICENSE): copy it freely.

---
Check: `./install.sh status hello-frame` · Remove: `./install.sh uninstall hello-frame`
