#!/usr/bin/env python3
"""The installer's look in a terminal: a short animated splash (Frame Tweaks' logo, its two sliders
gliding, and its name), which then goes on in the top half of the terminal while the command's
output runs in the bottom half. When the command ends, the terminal is as it was before, with the
whole output in it (and in its scrollback) under a small banner.

  python3 lib/splash.py -- COMMAND [ARG...]      run COMMAND under it (its exit status is ours)
  python3 lib/splash.py --demo                   a pretend install, to see it

The picture is drawn in "▀" characters: two pixels to a character cell (the upper one in the text
colour, the lower one in the background colour), in 24-bit colour where the terminal says it has
it (COLORTERM), else in its 256 colours. Nothing moves across the whole screen (no warp-speed
stars): in the headset, big moving fields make people queasy.

The command runs in a terminal of its own (a pty the size of the bottom half): colours, progress
bars, questions, sudo's password prompt and Ctrl+C work as usual. The top half is drawn between
the command's writes, never inside one of its escape sequences, and the terminal's scrolling
region and origin mode keep the command's output, even its cursor moves, in the bottom half. A
command that switches to the alternate screen (a pager, an editor) gets the whole terminal until
it switches back. Konsole keeps no scrollback for a part of the screen scrolling on its own, and
the splash draws on the alternate screen anyway, so the output is printed again at the end.

⚙ Preferences → Installing in a terminal chooses: animated (the default), still (no splash, no
motion) or plain output (~/.config/frame-tweaks/splash: on, still or off; FRAME_TWEAKS_SPLASH,
with the same values, goes first). KDE's animation speed set to instant (System Settings) keeps
it still too. It steps aside (the command runs as it would have) when set off, without a
terminal to draw on, in one smaller than 60×20, with TERM=dumb or linux, outside UTF-8, and if
anything goes wrong drawing it (the output so far is printed and the command goes on). Any key
skips the splash. The command finds FRAME_TWEAKS_SPLASH_TTY set to its terminal, so ./install.sh run in it
doesn't start another one."""
# (The docstring above is the usage it prints. Here: the setting, and running the command in a
# terminal of its own; lib/splash_stage.py draws the split screen, lib/splash_art.py the picture.)
import fcntl
import locale
import os
import select
import signal
import sys
import termios
import time
import tty
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# (_ is splash_stage's, so run()'s first call loads the translations the frames use too)
from splash_stage import FPS, HOLD, INTRO, INTRO_FPS, Stage, _, set_size, term_size  # noqa: E402
from splash_art import Picture, cells  # noqa: E402,F401  (re-exported: splash.NAME, for the tests)
from splash_stage import SEQ, Transcript  # noqa: E402,F401  (re-exported: splash.NAME, for the tests)


def kde_still():
    """KDE's animation speed set to instant (System Settings → General Behaviour)."""
    cfg = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "kdeglobals"
    try:
        group = ""
        for line in cfg.read_text(errors="replace").splitlines():
            line = line.strip()
            if line.startswith("["):
                group = line
            elif group == "[KDE]" and line.replace(" ", "").startswith("AnimationDurationFactor="):
                return float(line.split("=", 1)[1]) == 0
    except (OSError, ValueError):
        pass
    return False


# ---- running the command ----------------------------------------------------------------------

def wanted(out):
    if setting() == "off":
        return False
    if not os.isatty(out) or os.environ.get("TERM", "") in ("", "dumb", "linux"):
        return False
    if "utf" not in (locale.getpreferredencoding(False) or "").lower().replace("-", ""):
        return False
    try:
        if os.tcgetpgrp(out) != os.getpgrp():       # (run in the background: ./install.sh … &)
            return False
    except OSError:
        pass                                    # (not this process's terminal: no session of its own to be in the background of)
    cols, rows = term_size(out)
    return cols >= 60 and rows >= 20


SETTING = Path(os.environ.get("FRAME_TWEAKS_SPLASH_FILE") or Path.home() / ".config/frame-tweaks/splash")


def setting():
    """"on", "still" or "off": FRAME_TWEAKS_SPLASH, else ⚙ Preferences' choice, else on."""
    v = os.environ.get("FRAME_TWEAKS_SPLASH", "").strip().lower()
    if not v:
        try:
            v = SETTING.read_text().strip().lower()
        except (OSError, UnicodeDecodeError):
            v = ""
    return "off" if v in ("off", "0", "no", "false") else "still" if v == "still" else "on"


def set_setting(value):
    SETTING.parent.mkdir(parents=True, exist_ok=True)
    SETTING.write_text((value if value in ("still", "off") else "on") + "\n")


def keyboard(out):
    """Where keys come from: stdin if it's the terminal, else the terminal (/dev/tty: the one-liner
    reads its script from curl), else the one the output goes to (a process without a controlling
    terminal, e.g. in dev/fresh-install.sh's sandbox, a session of its own). Raises OSError."""
    if os.isatty(0):
        return 0
    try:
        return os.open("/dev/tty", os.O_RDONLY)
    except OSError:
        return os.open(os.ttyname(out), os.O_RDONLY | os.O_NOCTTY)


def tty_path(fd):
    """The terminal fd is, as ./install.sh reads it (readlink /proc/$$/fd/1: the two must agree, or
    it starts a splash again and again); None if it can't be read."""
    try:
        return os.readlink(f"/proc/self/fd/{fd}")
    except OSError:
        return None


def default_signals():
    """Python ignores SIGPIPE (and SIGXFSZ), and a command exec'd from it would too, with whatever
    it starts: a pipeline's writer then keeps going after its reader has gone."""
    for sig in (signal.SIGPIPE, signal.SIGXFSZ):
        signal.signal(sig, signal.SIG_DFL)


def plain(cmd):
    """The command as it would have run (marked, so ./install.sh doesn't start a splash again)."""
    os.environ["FRAME_TWEAKS_SPLASH_TTY"] = (tty_path(1) if os.isatty(1) else None) or "none"
    sys.stdout.flush()
    default_signals()
    os.execvp(cmd[0], cmd)


def run(cmd):
    out = 1
    if not wanted(out) or os.environ.get("FRAME_TWEAKS_SPLASH_TTY") == tty_path(out):
        plain(cmd)                   # (or already in the terminal a splash gave it: never one in another)
    resized = [False]

    def on_winch(*_a):
        resized[0] = True
    signal.signal(signal.SIGWINCH, on_winch)    # (before the size is read: a resize in between counts)
    try:
        inp = keyboard(out)
        saved = termios.tcgetattr(inp)
        cols, rows = term_size(out)
        still = setting() == "still" or kde_still()
        master, slave = os.openpty()
        termios.tcsetattr(slave, termios.TCSANOW, saved)
        stage = Stage(1, master, cols, rows, still)
        set_size(slave, stage.child_rows(), cols)
        name = tty_path(slave) or os.ttyname(slave)
        piped = not os.isatty(0)
        pid = os.fork()
    except (OSError, termios.error):
        signal.signal(signal.SIGWINCH, signal.SIG_DFL)
        plain(cmd)
    if pid == 0:
        try:
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
            # (input piped or redirected stays the command's: yes | ./install.sh …; sudo asks
            # through the terminal, /dev/tty, either way)
            for fd in ((1, 2) if piped else (0, 1, 2)):
                os.dup2(slave, fd)
            for fd in {master, slave, inp} - {0, 1, 2}:
                os.close(fd)                    # (held here, the terminal outlived a splash that died)
            os.environ["FRAME_TWEAKS_SPLASH_TTY"] = name
            leader(cmd)
        except BaseException as e:
            os.write(2, ("%s: %s\n" % (cmd[0], e)).encode())
        os._exit(127)
    os.close(slave)
    status = None

    def on_end(sig, _f):
        try:
            os.killpg(pid, sig)          # (the command and what it runs: its own session)
        except OSError:
            pass
    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(sig, on_end)
    _("Working…")                    # (the translations, loaded now rather than mid-frame)
    broken = None
    try:
        tty.setraw(inp)
        stage.begin()
        status = loop(stage, master, inp, pid, resized)
    except Exception as e:           # drawing went wrong: the command goes on, plainly
        broken = e
    finally:
        try:
            stage.finish()
        except OSError:                          # (the terminal is gone: closed)
            pass
        try:
            termios.tcsetattr(inp, termios.TCSADRAIN, saved)
        except (OSError, termios.error):
            pass
    try:
        text = stage.replay()
        # (lib/detached.sh in tmux: tmux's screen goes with the session, so it prints this again
        # after, into the terminal's scrollback)
        if os.environ.get("FRAME_TWEAKS_SPLASH_REPLAY"):
            Path(os.environ["FRAME_TWEAKS_SPLASH_REPLAY"]).write_text(text)
    except OSError:
        pass
    if status is None:
        status = stage.result                    # (known already when drawing failed after the end)
    if broken is not None:
        sys.stderr.write("(splash: %s: %s)\n" % (type(broken).__name__, broken))
        if status is None:
            status = passthrough(master, pid, inp, saved)
    if status is None:
        status = reap(pid, block=True)
    return status


def leader(cmd):
    """The command's terminal's session leader (in the forked child): runs the command, and once
    it has ended, waits (2 s at most) for what it left running in the session, e.g. ./install.sh's
    tee still writing its last lines to the terminal: a session leader that ends hangs up its
    terminal, which would kill them first. (In Konsole the shell is the leader and stays.) Its
    exit status is the command's."""
    pid = os.fork()
    if pid == 0:
        default_signals()
        os.execvp(cmd[0], cmd)
    for sig in (signal.SIGINT, signal.SIGQUIT, signal.SIGTSTP):
        signal.signal(sig, signal.SIG_IGN)      # (Ctrl+C is for the command)
    while True:
        try:
            _p, st = os.waitpid(pid, 0)
            break
        except InterruptedError:
            continue
    me = os.getpid()
    end = time.monotonic() + 2
    while time.monotonic() < end and session_others(me):
        time.sleep(0.02)
    os._exit(os.waitstatus_to_exitcode(st) if os.WIFEXITED(st) else 128 + os.WTERMSIG(st))


def session_others(sid):
    """Whether processes other than the session leader are still in session sid."""
    for d in os.listdir("/proc"):
        if d.isdigit() and int(d) != sid:
            try:
                with open("/proc/%s/stat" % d, "rb") as f:
                    fields = f.read().rsplit(b")", 1)[1].split()
            except OSError:
                continue
            if len(fields) > 3 and int(fields[3]) == sid:
                return True
    return False


def reap(pid, block=False):
    try:
        p, st = os.waitpid(pid, 0 if block else os.WNOHANG)
    except ChildProcessError:
        return 1
    if p == 0:
        return None
    return os.waitstatus_to_exitcode(st) if os.WIFEXITED(st) else 128 + os.WTERMSIG(st)


def loop(stage, master, inp, pid, resized):
    """Until the command ends: its output below, keys to it, the picture above."""
    next_frame = time.monotonic()
    status = None
    drain_until = None
    open_in = True
    while True:
        now = time.monotonic()
        fps = INTRO_FPS if stage.intro else FPS
        wait = max(0.0, min(next_frame - now, 0.25))
        fds = [master] + ([inp] if open_in else [])
        try:
            r, _w, _x = select.select(fds, [], [], wait)
        except InterruptedError:
            r = []
        now = time.monotonic()
        if master in r:
            try:
                data = os.read(master, 65536)
            except OSError:
                data = b""
            if not data:
                break
            stage.child_output(data, now)
        if open_in and inp in r:
            try:
                keys = os.read(inp, 1024)
            except OSError:
                keys = b""
            if not keys:
                open_in = False
            elif stage.intro and not any(c in keys for c in b"\x03\x1c\x1a"):
                stage.end_intro()                    # (that key only skips the splash)
            else:
                stage.end_intro()                    # (Ctrl+C, Ctrl+\, Ctrl+Z: for the command too)
                try:
                    os.write(master, keys)
                except OSError:
                    pass
        stage.flush_carry(now)
        if status is None:
            status = reap(pid)
            if status is not None:
                stage.result = status
                drain_until = now + 0.3              # (what's still on its way; a daemon it left may keep the terminal open)
                if stage.intro:
                    stage.end_intro()
        if drain_until and now > drain_until:
            break
        if resized[0]:
            resized[0] = False
            c, rws = term_size(1)
            stage.resize(c, rws)
        if stage.intro and now - stage.start >= INTRO:
            stage.end_intro()
        if now >= next_frame:
            stage.frame(now)
            next_frame = now + 1.0 / fps
    if status is None:
        status = reap(pid, block=True)
    stage.result = status
    stage.end_intro()                            # (it ended before the splash did: its output, and ✔ or ✖)
    if not stage.paused and not stage.still:
        end = time.monotonic() + HOLD
        while time.monotonic() < end:
            stage.frame(time.monotonic())
            time.sleep(1.0 / FPS)
    elif not stage.paused:
        stage.frame(time.monotonic())
    return status


def passthrough(master, pid, inp, saved):
    """The rest of the command's output as it is, and keys to it (after the picture failed): until
    it has ended and its output is drained."""
    status, until, out_ok = None, None, True
    try:
        tty.setraw(inp)
    except (OSError, termios.error):
        pass
    try:
        while until is None or time.monotonic() < until:
            try:
                r, _w, _x = select.select([master, inp], [], [], 0.2)
            except InterruptedError:
                continue
            if inp in r:
                try:
                    keys = os.read(inp, 1024)
                    if keys:
                        os.write(master, keys)
                except OSError:
                    pass
            if master in r:
                try:
                    data = os.read(master, 65536)
                except OSError:
                    data = b""
                if not data:
                    break
                if out_ok:
                    try:
                        os.write(1, data)
                    except OSError:
                        out_ok = False           # (the terminal is gone: read on, so the command isn't stuck)
            if status is None:
                status = reap(pid)
                if status is not None:
                    until = time.monotonic() + 0.3
    finally:
        try:
            termios.tcsetattr(inp, termios.TCSADRAIN, saved)
        except (OSError, termios.error):
            pass
    return status if status is not None else reap(pid, block=True)


# ---- a pretend install, to see it --------------------------------------------------------------

def demo_child():
    """What a real install prints (some of it its very words), in Frame Tweaks' language: it
    showed English whatever language was chosen."""
    w = sys.stdout.write

    def say(text, pause=0.35):
        w(text + "\n")
        sys.stdout.flush()
        time.sleep(pause)
    say("\x1b[1;34m==>\x1b[0m " + _("Setting up PyQt6, a window toolkit"), 0.6)
    for i in range(0, 101, 4):
        bar = "━" * (i * 30 // 100) + "\x1b[2m" + "━" * (30 - i * 30 // 100) + "\x1b[0m"
        w("\r   \x1b[35m%s\x1b[0m %3d%% · %.1f/62.4 MB" % (bar, i, 62.4 * i / 100))
        sys.stdout.flush()
        time.sleep(0.08)
    w("\n")
    pad, snip = _("Arrow Pad"), _("Screen snip + Narrate")
    for tid, title, lines in (
            ("ydotool", "ydotool", [_("Fetching {name} (Arch Linux ARM, signature checked)").format(name="ydotool 1.0.4-3"),
                                    _("Installed {programs} in {folder}").format(programs="ydotool, ydotoold",
                                                                                 folder="~/.local/bin")]),
            ("arrowpad", pad, [_("Setting up {name}'s Python packages").format(name=pad),
                               _("Added {name} to the app menu").format(name=pad),
                               "\x1b[32m✔\x1b[0m " + _("{name} is ready: {keys} shows it").format(name=pad, keys="Ctrl+Alt+A")]),
            ("snip", snip, [_("Linking {program} into {folder}").format(program="frame-snip", folder="~/.local/bin"),
                            _("Narrate's voice: {voice}").format(voice="Piper")])):
        say("\x1b[1m── %s: %s\x1b[0m" % (tid, title), 0.5)
        for line in lines:
            say("  " + line, 0.45)
        say("", 0.2)
    say("\x1b[1m" + _("Done.") + "\x1b[0m", 0.3)
    for tid, st in (("ydotool", _("running")), ("arrowpad", _("installed")), ("snip", _("installed"))):
        say("  \x1b[32m✔\x1b[0m %-15s %s" % (tid, st), 0.08)


def main(argv):
    if argv[:1] == ["--demo-child"]:
        demo_child()
        return 0
    if argv[:1] == ["--demo"]:
        cmd = [sys.executable, str(Path(__file__).resolve()), "--demo-child"]
    elif argv[:1] == ["--"] and len(argv) > 1:
        cmd = argv[1:]
    else:
        sys.stderr.write(__doc__.split("\n\n")[1] + "\n")
        return 2
    return run(cmd)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
