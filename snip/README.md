# Screen snip

Select a rectangle of the window you're using, then:

- **Copy**: the picture, to the clipboard (desktop and, with [Shared clipboard](../clipboard/),
  VR windows).
- **Save**: to `~/Pictures/Screenshots/Snip_<date>_<time>.png`.
- **Copy text**: reads the text in it ([Tesseract](https://github.com/tesseract-ocr/tesseract)
  OCR) and copies that.
- **Narrate**: reads the text aloud ([Piper](https://github.com/rhasspy/piper), offline), at
  the speed set under it (**−** / **+**, 0.75× to 2×, remembered). The snip pops out into a panel
  of its own (drawn like Arrow Pad, not a window, so it takes no place in the dashboard) with
  **■ Stop** / **▶ Again**, **⏸ Pause** / **▶ Resume**, speed, and **Close**. It starts beside
  Arrow Pad's place under the dashboard and follows the dashboard; drag its top bar to move it,
  and it remembers the spot (relative to the dashboard) for next time. The
  full-screen snip goes away, so you can carry on with anything else while it reads. A speed change applies at
  once (it reads sentence by sentence and restarts the current one).

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder and Homebrew)
> - **Changes:** `frame-snip`, Tesseract (Homebrew), an app-menu entry; Piper comes from the Speech engine helper
> - **Unusual access:** Reads the picture of the window you're using (only when you start a snip)
> - **Undo:** `./install.sh uninstall snip` (keeps Tesseract and your snips in `~/Pictures/Screenshots`)
<!-- /generated:glance -->

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

The same helper gives SteamOS's speech-dispatcher a voice (it has none of its own), which the
[Screen reader](../screen-reader/)'s Orca uses.

---
Check: `./install.sh status snip` · Remove: `./install.sh uninstall snip`
