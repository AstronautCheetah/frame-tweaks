---
title: Screen snip
emoji: ✂️
category: Accessibility
tier: core
summary: >-
  Select a rectangle of the window you're using: copy it, save it, copy its text (OCR) or read
  it aloud
what: >-
  Select a rectangle of the window you're using, then copy it, save it, copy its text (OCR) or
  read it aloud (Narrate). Arrow Pad's Tools layer has a button for it.
why: >-
  SteamOS has no screenshot tool, and none of the usual ones can select a region inside VR.
author: "Frame Tweaks (OCR: Tesseract; speech: Piper)"
source:
  relation: uses
  url: https://github.com/tesseract-ocr/tesseract
depends: [homebrew, speech]
icon: {file: frame-tweaks-snip.png}
run: {label: Snip}
changes: >-
  `frame-snip`, Tesseract (Homebrew), an app-menu entry; Piper comes from the Speech engine
  helper
access: Reads the picture of the window you're using (only when you start a snip)
survives_updates: Yes (everything is in your home folder and Homebrew)
undo: >-
  `./install.sh uninstall snip` (keeps Tesseract and your snips in `~/Pictures/Screenshots`)
---
# Screen snip

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Select a rectangle of the window you're using, then copy it, save it, copy its text (OCR) or read it aloud (Narrate). Arrow Pad's Tools layer has a button for it.

**Why on a Steam Frame:** SteamOS has no screenshot tool, and none of the usual ones can select a region inside VR.
<!-- /generated:intro -->

Select a rectangle of the window you're using, then:

- **Copy**: the picture, to the clipboard (desktop and, with [Shared clipboard](../clipboard/),
  VR windows).
- **Save**: to `~/Pictures/Screenshots/Snip_<date>_<time>.png`.
- **Copy text**: reads the text in it ([Tesseract](https://github.com/tesseract-ocr/tesseract)
  OCR) and copies that.
- **Narrate**: reads the text aloud ([Piper](https://github.com/rhasspy/piper), offline), at
  the speed set under it (**−** / **+**, 0.75× to 2×, remembered). The snip pops out into a panel
  of its own (drawn like Arrow Pad, not a window, so it takes no place in the dashboard) with
  **■ Stop** / **▶ Again**, **⏸ Pause** / **▶ Resume**, **Show text** / **Show image** (the
  snip's image, or the text read from it), speed, **Copy image**, **Copy text**, **Paste** (read
  the clipboard's text instead; it's shown in place of the snip), **Close** and **Collapse** (at
  either end of the bottom row: down to just an Expand icon, with a margin to grab it by, right
  where the Collapse icon you used was; reading carries on). It starts beside
  Arrow Pad's place under the dashboard and follows the dashboard; drag its top bar to move it,
  and it remembers the spot (relative to the dashboard) for next time. Narrating another snip
  while it's open reuses it, in place. The
  full-screen snip goes away, so you can carry on with anything else while it reads. A speed change applies at
  once (it reads sentence by sentence and restarts the current one).


Start it from **Arrow Pad**: the **Tools** key, then **Snip** (the dashed rectangle). Or from
the app menu: **Screen snip**. It freezes a picture of the window the Steam session has focused
(the desktop, or a window you floated) and shows it in a new window: drag a rectangle with the
laser, adjust it with its **handles** (corners and edges) or drag it from inside to move it,
then pick an action. Dragging outside it starts a new one. **Esc** or a right-click cancels.

## Why these tools
SteamOS ships no screenshot tool, and KDE's Spectacle or Flameshot can't select a region of a
VR window. So the snip window is a small PyQt program (shared with Arrow Pad) that reads the
window's picture straight from the Steam session's display, the way Flameshot-style tools
freeze the screen. Copy text uses **Tesseract** (Apache-2.0, from Homebrew). Narrate uses
**Piper** (MIT), a fast offline neural voice, with the **LJ Speech** voice (its dataset is public
domain), installed by the [Speech engine](../speech/) helper and pinned by checksum.

The same helper gives SteamOS's speech-dispatcher a voice (it has none of its own), which KDE's
screen reader, Orca, uses.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder and Homebrew)
- **Changes:** `frame-snip`, Tesseract (Homebrew), an app-menu entry; Piper comes from the Speech engine helper
- **Unusual access:** Reads the picture of the window you're using (only when you start a snip)
- **Undo:** `./install.sh uninstall snip` (keeps Tesseract and your snips in `~/Pictures/Screenshots`)
<!-- /generated:changes -->

---
Check: `./install.sh status snip` · Remove: `./install.sh uninstall snip`
