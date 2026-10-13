# Screen snip

Select a rectangle of the window you're using, then:

- **Copy**: the picture, to the clipboard (desktop and, with [Shared clipboard](../clipboard/),
  VR windows).
- **Save**: to `~/Pictures/Screenshots/Snip_<date>_<time>.png`.
- **Copy text**: reads the text in it ([Tesseract](https://github.com/tesseract-ocr/tesseract)
  OCR) and copies that.
- **Narrate**: reads the text aloud ([Piper](https://github.com/rhasspy/piper), offline).
  Press **■ Stop** to stop.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder and Homebrew)
> - **Changes:** `frame-snip`, Piper and a voice in `~/.local/share/frame-tweaks/snip` (checksum-pinned), Tesseract (Homebrew), an app-menu entry
> - **Unusual access:** Reads the picture of the window you're using (only when you start a snip)
> - **Undo:** `./install.sh uninstall snip` (keeps Tesseract and your snips in `~/Pictures/Screenshots`)
<!-- /generated:glance -->

Start it from **Arrow Pad**: the **Tools** key, then **Snip** (the dashed rectangle). Or from
the app menu: **Screen snip**. It freezes a picture of the window the Steam session has focused
(the desktop, or a window you floated) and shows it in a new window: drag a rectangle with the
laser, then pick an action. **Esc** or a right-click cancels.

## Why these tools
SteamOS ships no screenshot tool, and KDE's Spectacle or Flameshot can't select a region of a
VR window. So the snip window is a small PyQt program (shared with Arrow Pad) that reads the
window's picture straight from the Steam session's display, the way Flameshot-style tools
freeze the screen. Copy text uses **Tesseract** (Apache-2.0, from Homebrew). Narrate uses
**Piper** (MIT), a fast offline neural voice, with the **LJ Speech** voice (its dataset is public
domain). Both are pinned by checksum (`pin`, `voice.pin`, `voice-config.pin`).

SteamOS's own speech engine (speech-dispatcher, which the [Screen reader](../screen-reader/)'s
Orca uses) has no voice installed: its espeak-ng module is there but espeak-ng isn't.

---
Check: `./install.sh status snip` · Remove: `./install.sh uninstall snip`
