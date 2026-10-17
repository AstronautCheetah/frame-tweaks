---
title: Screen snip + Narrate
emoji: ✂️
category: Accessibility
tier: core
summary: >-
  Select a rectangle of the window you're using: copy it, save it, copy its text (OCR) or read
  it aloud
what: >-
  Select a rectangle of the window you're using, then copy it, save it, copy its text (OCR) or
  have it read aloud (Narrate). Arrow Pad's Tools layer has a button for it.
why: >-
  SteamOS comes with no screenshot tool, and the usual desktop ones can't select a region of a
  window floating in VR.
author: "Frame Tweaks (OCR: Tesseract; speech: Piper)"
sudo: homebrew
source:
  relation: uses
  url: https://github.com/tesseract-ocr/tesseract
depends: [homebrew, speech]
icon: {file: frame-tweaks-snip.png}
run: {label: Snip}
processes: ['^~/.local/share/arrowpad/venv/bin/python ~/.local/bin/frame-snip( |$)']
settings:
  file: ~/.config/frame-tweaks/snip.json
  format: json
  about: >-
    How Narrate reads: its speed here, and its voice and language below (the Speech engine's
    settings). The ⚙ on Narrate's panel shows the same.
  note: >-
    The speed applies to the next Narrate (or at once, from the panel's − / +).
  options:
    - key: speed
      title: Reading speed
      default: 1.0
      choices:
        - {label: "0.75×", value: 0.75}
        - {label: "1×", value: 1.0}
        - {label: "1.25×", value: 1.25}
        - {label: "1.5×", value: 1.5}
        - {label: "1.75×", value: 1.75}
        - {label: "2×", value: 2.0}
  include: [speech]
changes: >-
  `~/.local/bin/frame-snip`, Tesseract and `wl-clipboard` (Homebrew), an app-menu entry; Piper
  comes from the Speech engine helper
access: Reads the picture of the window you're using (only when you start a snip)
survives_updates: Yes (everything is in your home folder and Homebrew)
undo: >-
  `./install.sh uninstall snip` (keeps Tesseract and `wl-clipboard`, your settings in
  `~/.config/frame-tweaks/snip.json` and your snips in `~/Pictures/Screenshots`)
---
# Screen snip + Narrate

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Select a rectangle of the window you're using, then copy it, save it, copy its text (OCR) or have it read aloud (Narrate). Arrow Pad's Tools layer has a button for it.

**Why on a Steam Frame:** SteamOS comes with no screenshot tool, and the usual desktop ones can't select a region of a window floating in VR.
<!-- /generated:intro -->

![Screen snip: a selection with its handles, and Copy, Save, Copy text, Narrate and Cancel](../../../docs/images/snip.png)

![Narrate's panel, reading a snip aloud](../../../docs/images/narrate.png)

## Install

Tick it in the Frame Tweaks window, or:

```sh
./install.sh install snip
```

It installs Tesseract (the text reader) from [Homebrew](../homebrew/), and Piper (the voice)
through the [Speech engine](../speech/) helper. Nothing else to do.

## Use

Start a snip from [Arrow Pad](../arrowpad/): the **Tools** key, then **Snip** (the dashed
rectangle). Or open **Screen snip + Narrate** from the app menu.

It takes a still picture of the window the Steam session has focused (the desktop, or a window
you floated) and shows it full size:

1. Drag a rectangle with the laser.
2. Adjust it with its **handles** (corners and edges), or drag it from inside to move it.
   Dragging outside it starts a new one.
3. Pick an action from the bar next to it. **Esc**, a right-click or **Cancel** closes it.

The actions:

- **Copy**: the picture, to the clipboard. With [Shared clipboard](../../integrations/clipboard/) installed,
  you can paste it into VR windows too.
- **Save**: to `~/Pictures/Screenshots/Snip_<date>_<time>.png`.
- **Copy text**: reads the text in it and copies that.
- **Narrate**: reads the text aloud, offline, at the speed set under the button (**−** / **+**,
  0.75× to 2×).

### The narration panel

Narrate closes the full-size picture and pops the snip out into a panel of its own, so you can
carry on with anything else while it reads. In VR it's a SteamVR panel (drawn like Arrow Pad, so
it doesn't take a place in the dashboard); it starts under the dashboard and follows it. To move it,
squeeze the grip while pointing at it (anywhere, buttons included) and let go to put it down,
or pull the trigger on an empty part of it and drag. It remembers the spot for next time.

**With Steam's keyboard open,** SteamVR hides where your controllers are from other programs, so
the panel can only slide after the laser (in its own plane); a note under it says so. With the
[VR environment helper](../vr-dashboard/) installed (any VR environment tweak brings it), SteamVR's
own grab bar shows under the panel then: hold it to move the panel anywhere, closer, further away
or turned, as a desktop window's. And pressing the panel while you type doesn't take the
keyboard away from the window you're typing in.

The panel has:

- **Stop** / **Again**, and **Pause** / **Resume** between **Previous part** and **Next part**
  (icons; point at one to see its name).
- **Previous part** / **Next part**: it reads a part (about a sentence) at a time, as in
  "part 2 of 5", and these go to the start of the part before or the one after. Previous always
  goes back a whole part (it doesn't first restart the one being read, as some music players
  do). While paused, it stays paused, on the new part; **Resume** reads it from its start. Each
  is greyed out where there's no part to go to (at the first or last), and once it's stopped or
  done.
- **Speed** **−** / **+**. A change applies at once: it reads sentence by sentence and starts
  the current sentence again.
- **Show text** / **Show image**: the snip's picture, or the text read from it.
- **Snip** (the dashed rectangle, as on Arrow Pad): snip something new; it's read in this panel.
- **Copy image** and **Copy text**.
- **Paste** (icon): read the clipboard's text instead. It's shown in place of the snip.
- **⚙ Settings:** Narrate's engine (Piper or eSpeak NG) and language, with **Apply**. The same
  settings are on this tweak's ⚙ button in the Frame Tweaks window, with the reading speed.
- **Close** (✕), and **Collapse** at either end of the bottom row. Collapse shrinks the panel to a
  single Expand icon, right where you pressed it; reading carries on.

Narrating another snip while the panel is open reuses it, where it is.

## Settings

The reading speed and the panel's spot are remembered in `~/.config/frame-tweaks/snip.json`.

## How it works

- The snip window is a small PyQt program (it shares Arrow Pad's PyQt6 copy). It reads the
  focused window's picture straight from the Steam session's display, and opens on that display
  so it shows up in VR.
- **Copy text** and **Narrate** read the text with
  [Tesseract](https://github.com/tesseract-ocr/tesseract), using its English data, on a
  picture scaled up 2× (small screen text reads better that way).
- **Narrate** speaks with [Piper](https://github.com/rhasspy/piper), an offline neural voice,
  with the LJ Speech voice. The Speech engine helper installs both, pinned by checksum. On
  SteamOS before 0.5.6, that helper also gives speech-dispatcher a voice (it has none of its
  own), which KDE's screen reader, Orca, uses; 0.5.6 removed both.
- **Copy** offers the picture as PNG, BMP and HTML, because some apps don't take a PNG alone.

## Good to know

- Copying needs desktop mode to be running: the clipboard lives there.
- **Copy text** and the panel's **Paste** use `wl-copy` and `wl-paste` from Homebrew's
  `wl-clipboard`; installing Screen snip adds it if it isn't there yet.
- Without SteamVR's OpenVR library, the narration panel opens as an ordinary window instead.
- If the Speech engine fails on a part (it doesn't start, or makes no sound), Narrate tries that
  part once more, then stops there and says so; **Again** tries again. If SteamVR fails under
  the narration panel (restarting, say), the panel closes and the reading stops: Narrate opens
  a new one.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder and Homebrew)
- **Changes:** `~/.local/bin/frame-snip`, Tesseract and `wl-clipboard` (Homebrew), an app-menu entry; Piper comes from the Speech engine helper
- **Unusual access:** Reads the picture of the window you're using (only when you start a snip)
- **Undo:** `./install.sh uninstall snip` (keeps Tesseract and `wl-clipboard`, your settings in `~/.config/frame-tweaks/snip.json` and your snips in `~/Pictures/Screenshots`)
<!-- /generated:changes -->

## Credits

[Tesseract](https://github.com/tesseract-ocr/tesseract) (Apache-2.0, from Homebrew) reads the
text. [Piper](https://github.com/rhasspy/piper) (MIT) speaks it, with the
[LJ Speech](https://keithito.com/LJ-Speech-Dataset/) voice (dataset in the public domain). Some
button icons, and its menu icon, are [KDE Breeze](https://invent.kde.org/frameworks/breeze-icons)
(LGPL-3.0-or-later), from SteamOS's own icon theme ([icons/README.md](../../../icons/README.md)). See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status snip` · Remove: `./install.sh uninstall snip`
