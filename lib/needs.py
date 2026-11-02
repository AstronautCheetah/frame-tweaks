"""When a feature needs a tweak that isn't installed (Arrow Pad's 🎤 without Dictation, Narrate
without the Speech engine, …): say so in a dialog, which shows in VR too (a notification there
goes unseen), with a button that opens Frame Tweaks on that tweak, to install it.

Installed beside i18n.py (lib/common.sh install_i18n), for the programs tweaks install."""
import os
import re
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
    return exec_args(line[len("Exec="):]) + ["--show", tweak]


def exec_args(value):
    """A desktop entry's Exec= value as arguments, as its spec reads it (lib/installer.py
    desktop_word writes it so): the value's escapes first (\\\\, \\s, \\n, \\t, \\r), then
    double quotes, inside which a backslash escapes only " ` $ and itself, then %% as %. (shlex
    keeps the backslash before $ and `, and doesn't know %%: a checkout path with one of those
    came out wrong.)"""
    value = re.sub(r"\\([\\snrt])", lambda m: {"s": " ", "n": "\n", "r": "\r", "t": "\t"}.get(m[1], "\\"), value)
    args, word, quoted, i = [], None, False, 0
    while i < len(value):
        c = value[i]
        if quoted and c == "\\" and value[i + 1:i + 2] in ('"', "`", "$", "\\"):
            word, i = word + value[i + 1], i + 1
        elif c == '"':
            quoted, word = not quoted, word or ""
        elif c in " \t\n" and not quoted:
            if word is not None:
                args.append(word)
            word = None
        else:
            word = (word or "") + c
        i += 1
    if word is not None:
        args.append(word)
    return [a.replace("%%", "%") for a in args]


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
