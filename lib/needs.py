"""When a feature needs a tweak that isn't installed (Arrow Pad's 🎤 without Dictation, Narrate
without the Speech engine, …): say so in a dialog, which shows in VR too (a notification there
goes unseen), with a button that opens Frame Tweaks on that tweak, to install it.

Installed beside i18n.py (lib/common.sh install_i18n), for the programs tweaks install."""
import os
import shlex
import shutil
import subprocess
from pathlib import Path

try:
    from i18n import _
except ImportError:                       # (not installed by Frame Tweaks: English)
    def _(text):
        return text

# Frame Tweaks' own menu entry: how to start its window, wherever it's installed.
ENTRY = Path.home() / ".local/share/applications/io.github.AstronautCheetah.FrameTweaks.desktop"


def window_command(tweak):
    """The command that opens Frame Tweaks' window on that tweak's page, or None (no menu entry:
    Frame Tweaks itself was uninstalled)."""
    try:
        line = next(l for l in ENTRY.read_text().splitlines() if l.startswith("Exec="))
    except (OSError, StopIteration):
        return None
    return shlex.split(line[len("Exec="):]) + ["--show", tweak]


def offer(tweak, title, text, question=None, run=subprocess.Popen):
    """Say what's missing (title, text) and offer to open Frame Tweaks on `tweak` (question:
    what to do there; default: install it). Doesn't wait."""
    cmd = window_command(tweak)
    env = {k: v for k, v in os.environ.items() if not k.startswith("FRAME_TWEAKS_")}   # (its own language)
    if cmd is None:
        text += "\n\n" + _("Frame Tweaks isn't installed any more: get it again from its GitHub page.")
    if shutil.which("kdialog"):
        if cmd is None:
            args = ["kdialog", "--title", title, "--sorry", text]
        else:
            # (bash: open the window only on Yes, without this program waiting for the answer)
            args = ["bash", "-c", 'kdialog --title "$1" --yes-label "$2" --no-label "$3" --yesno "$4" && shift 4 && exec "$@"',
                    "needs", title, _("Open Frame Tweaks"), _("Not now"), text + "\n\n" + (question or _("Open Frame Tweaks to install it?"))]
            args += cmd
    else:
        args = ["notify-send", "-a", "Frame Tweaks", title, text]
    try:
        run(args, start_new_session=True, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass
