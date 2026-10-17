"""lib/splash.py, the installer's look in a terminal: the output it prints again at the end
(progress bars, lines erased and redrawn, colours), the command's output passed on whole (an
escape sequence or a character split between two reads, with no picture drawn inside it), the
layout kept (the command's own scrolling region, origin mode, cleared screen, alternate screen),
a picture that fits every size, and, in a real terminal (a pty): the exit status, the command
marked as in its terminal (so neither it nor ./install.sh starts another splash inside), Ctrl+C
reaching the command, the last lines of a pipeline not lost (a session leader's end hangs up its
terminal), and stepping aside without a terminal or with FRAME_TWEAKS_SPLASH=off."""
import fcntl
import os
import pty
import select
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT, sandbox_env  # noqa: E402

import splash  # noqa: E402  (lib/, on the path through helpers)

SPLASH = ROOT / "lib/splash.py"


def plain_lines(t):
    return [t.plain(i) for i in range(len(t.lines))]


class Transcript(unittest.TestCase):
    def feed(self, text):
        """Text with escape sequences, as the stage hands it over."""
        t = splash.Transcript()
        pos = 0
        data = text.encode()
        for m in splash.SEQ.finditer(data):
            t.text(data[pos:m.start()].decode())
            if m.group().startswith(b"\x1b["):
                t.csi(m.group().decode())
            pos = m.end()
        t.text(data[pos:].decode())
        return t

    def test_a_progress_bar_keeps_its_last_state(self):
        t = self.feed("10%\r50%\r100%\r\nnext\r\n")
        self.assertEqual(plain_lines(t)[:2], ["100%", "next"])

    def test_an_erased_line(self):
        t = self.feed("abcdef\x1b[2K\rxyz\n")
        self.assertEqual(plain_lines(t)[0], "xyz")

    def test_lines_redrawn_after_moving_up(self):
        t = self.feed("one\r\ntwo\r\n\x1b[2A\x1b[2KONE\r\n\x1b[2KTWO\r\n")
        self.assertEqual(plain_lines(t)[:2], ["ONE", "TWO"])

    def test_colours_come_back(self):
        t = self.feed("\x1b[32m✔\x1b[0m ok\n")
        self.assertEqual(plain_lines(t)[0], "✔ ok")
        self.assertIn("\x1b[32m✔", t.rendered()[0])
        self.assertTrue(t.rendered()[0].endswith("ok"))

    def test_a_cleared_screen_stays_in_the_log(self):
        t = self.feed("old\r\n\x1b[2J\x1b[Hnew\r\n")
        self.assertIn("old", plain_lines(t))
        self.assertIn("new", plain_lines(t))


class Output(unittest.TestCase):
    """What the stage passes on of the command's output (the drawing left out)."""

    def setUp(self):
        self.master, self.slave = os.openpty()
        self.addCleanup(os.close, self.master)
        self.addCleanup(os.close, self.slave)
        self.stage = splash.Stage(1, self.master, 100, 30)
        self.stage.intro = False
        self.out = []
        self.stage.write = lambda s: self.out.append(s.encode() if isinstance(s, str) else s)

    def feed(self, data):
        self.stage.child_output(data, time.monotonic())
        written, self.out[:] = b"".join(self.out), []
        return written

    def test_a_sequence_split_between_reads_is_passed_on_whole(self):
        self.assertEqual(self.feed(b"red: \x1b[3"), b"red: ")
        self.stage.frame(time.monotonic() + 1)       # a frame in between
        frame = b"".join(self.out)
        self.out[:] = []
        self.assertTrue(frame.startswith(b"\x1b7"))
        self.assertEqual(self.feed(b"1mX\x1b[0m"), b"\x1b[31mX\x1b[0m")

    def test_a_character_split_between_reads(self):
        tick = "✔".encode()
        self.assertEqual(self.feed(b"ok " + tick[:1]), b"ok ")
        self.assertEqual(self.feed(tick[1:] + b"\r\n"), tick + b"\r\n")

    def test_the_layout_is_kept(self):
        self.assertEqual(self.feed(b"\x1b[1;5r\x1b[?6l\x1b[!p"), b"")       # scrolling region, origin mode, soft reset
        self.assertEqual(self.feed(b"\x1b[2J"), b"\x1b[H\x1b[J")            # a clear screen: the bottom half only

    def test_a_pager_gets_the_whole_terminal_and_gives_it_back(self):
        self.feed(b"\x1b[?1049h")
        self.assertTrue(self.stage.paused)
        rows = struct.unpack("HHHH", fcntl.ioctl(self.slave, termios.TIOCGWINSZ, b"\0" * 8))[0]
        self.assertEqual(rows, 30)
        self.feed(b"\x1b[?1049l")
        self.assertFalse(self.stage.paused)
        rows = struct.unpack("HHHH", fcntl.ioctl(self.slave, termios.TIOCGWINSZ, b"\0" * 8))[0]
        self.assertEqual(rows, 30 - self.stage.top)

    def test_no_picture_while_the_command_has_its_cursor_saved(self):
        self.feed(b"\x1b7")
        self.stage.frame(time.monotonic())
        self.assertEqual(self.out, [])
        self.feed(b"\x1b8")
        self.stage.frame(time.monotonic())
        self.assertTrue(self.out)

    def test_a_resize_while_paused_reaches_the_command(self):
        self.feed(b"\x1b[?1049h")                                          # (a pager)
        for cols, rows in ((58, 18), (120, 40), (0, 0)):                   # (0×0 crashed making a picture)
            self.stage.resize(cols, rows)
            size = struct.unpack("HHHH", fcntl.ioctl(self.slave, termios.TIOCGWINSZ, b"\0" * 8))[:2]
            self.assertEqual(size, (max(1, rows), max(1, cols)))

    def test_what_came_before_a_pager_is_written_first(self):
        """A switch to the pager clears the screen: the text before it in the same read was
        written after the clear, onto the pager's screen."""
        written = self.feed(b"text-before\r\n\x1b[?1049hPAGER")
        self.assertLess(written.find(b"text-before"), written.find(b"\x1b[2J"))

    def test_an_unchanged_picture_writes_nothing(self):
        self.stage.still, self.stage.still_art = True, None
        # (well inside one second: start + 10.0 - start can come out as 9.999…, and the clock then
        # read 0:09, then 0:10, which failed this now and then in CI)
        self.stage.frame(self.stage.start + 10.3)
        self.assertTrue(self.out)
        self.out.clear()
        self.stage.frame(self.stage.start + 10.6)   # (the same second: nothing in it changed)
        self.assertEqual(self.out, [])

    def test_what_is_being_done(self):
        self.feed("\x1b[1m── arrowpad: Arrow Pad\x1b[0m\r\n".encode())
        self.assertEqual(self.stage.step, "arrowpad: Arrow Pad")
        self.feed("\x1b[1;34m==>\x1b[0m Setting up PyQt6\r\n".encode())
        self.assertEqual(self.stage.step, "Setting up PyQt6")


class Setting(unittest.TestCase):
    """⚙ Preferences' choice (~/.config/frame-tweaks/splash), with FRAME_TWEAKS_SPLASH first."""

    def test_the_choice_and_what_goes_first(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(splash, "SETTING", Path(d) / "splash"), \
                mock.patch.dict(os.environ, {"FRAME_TWEAKS_SPLASH": ""}):
            self.assertEqual(splash.setting(), "on")              # (nothing chosen)
            splash.set_setting("still")
            self.assertEqual(splash.setting(), "still")
            splash.set_setting("off")
            self.assertEqual(splash.setting(), "off")
            os.environ["FRAME_TWEAKS_SPLASH"] = "on"
            self.assertEqual(splash.setting(), "on")              # (the variable goes first)
            os.environ["FRAME_TWEAKS_SPLASH"] = ""
            splash.SETTING.write_bytes(b"\xff\xfe")
            self.assertEqual(splash.setting(), "on")              # (a file that isn't text: on, not a crash)


class Layout(unittest.TestCase):
    def test_the_picture_fits(self):
        for cols in (60, 72, 80, 100, 120, 160, 220):
            for top in (8, 10, 12, 16, 20, 30):
                p = splash.Picture(cols, 2 * (top - 1))
                with self.subTest(cols=cols, top=top):
                    self.assertGreaterEqual(p.x0, 0)
                    self.assertLessEqual(p.x0 + p.w, cols)
                    self.assertGreaterEqual(p.y0, 0)
                    self.assertLessEqual(p.y0 + p.h, p.px)
                    canvas = [row[:] for row in p.sky(p.px, 0)]
                    p.render(canvas, 0, 3.0, p.y0)
                    cells = splash.cells(canvas)
                    self.assertEqual(len(cells), top - 1)
                    self.assertTrue(all(len(r) == cols for r in cells))

    def test_bigger_terminals_get_a_bigger_picture(self):
        self.assertLess(splash.Picture(80, 22).k, splash.Picture(120, 38).k)


def in_pty(args, env, size=(30, 100), keys=None, timeout=20):
    """Run args in a terminal of its own; (exit status, everything it wrote). keys: [(after
    this appears in the output, send these)]."""
    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe(args[0], args, env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", size[0], size[1], 0, 0))
    out, keys, end = b"", list(keys or []), time.monotonic() + timeout
    while time.monotonic() < end:
        r, _w, _x = select.select([fd], [], [], 0.1)
        if r:
            try:
                data = os.read(fd, 65536)
            except OSError:
                break
            if not data:
                break
            out += data
        while keys and keys[0][0] in out:
            os.write(fd, keys.pop(0)[1])
    os.close(fd)
    _p, st = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(st), out


class Running(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.env = sandbox_env(tmp.name, TERM="xterm-256color", COLORTERM="truecolor", LANG="C.UTF-8",
                               FRAME_TWEAKS_SPLASH="still")

    def test_the_command_runs_in_a_terminal_it_knows_and_its_status_is_kept(self):
        rc, out = in_pty([sys.executable, str(SPLASH), "--", "sh", "-c",
                          'echo "mark:$FRAME_TWEAKS_SPLASH_TTY"; echo "tty:$(tty)"; echo finished; exit 3'], self.env)
        self.assertEqual(rc, 3)
        text = out.decode("utf-8", "replace")
        mark = text.split("mark:")[1].split("\r")[0]
        self.assertEqual(text.split("tty:")[1].split("\r")[0], mark)
        self.assertIn("\x1b[?1049h", text)
        # back to the terminal as it was, then the output printed again
        back = text.rindex("\x1b[?1049l")
        self.assertIn("\x1b[r", text[text.rindex("\x1b[?1049h"):back + 8])
        self.assertIn("finished", text[back:])

    def test_never_one_inside_another(self):
        rc, out = in_pty([sys.executable, str(SPLASH), "--", sys.executable, str(SPLASH), "--", "sh", "-c", "echo inner"],
                         self.env)
        self.assertEqual(rc, 0)
        self.assertEqual(out.count(b"\x1b[?1049h"), 1)
        self.assertIn(b"inner", out)

    def test_install_sh_inside_it_does_not_start_another(self):
        rc, out = in_pty([sys.executable, str(SPLASH), "--", str(ROOT / "install.sh"), "install"], self.env)
        self.assertEqual(rc, 1)                       # (install what?)
        self.assertEqual(out.count(b"\x1b[?1049h"), 1)

    def test_ctrl_c_reaches_the_command(self):
        rc, out = in_pty([sys.executable, str(SPLASH), "--", "sh", "-c",
                          'trap "echo got-int; exit 5" INT; echo ready; sleep 10 & wait'], self.env,
                         keys=[(b"ready", b"\x03")])
        self.assertEqual(rc, 5)
        self.assertIn(b"got-int", out)

    def test_the_last_lines_of_a_pipeline_are_not_lost(self):
        # (as ./install.sh's tee: still writing when the command itself has ended)
        rc, out = in_pty([sys.executable, str(SPLASH), "--", "bash", "-c",
                          'exec > >(sleep 0.3; cat) 2>&1; echo the-last-line'], self.env)
        self.assertEqual(rc, 0)
        self.assertIn(b"the-last-line", out)

    def test_without_a_controlling_terminal(self):
        # (the one-liner reads its script from curl, and dev/fresh-install.sh's sandbox is a session
        # of its own: the keys come from the terminal the output goes to)
        rc, out = in_pty(["setsid", "-w", "sh", "-c", 'echo | "$0" "$1" -- sh -c "echo from-the-command"',
                          sys.executable, str(SPLASH)], self.env)
        self.assertEqual(rc, 0)
        self.assertIn(b"\x1b[?1049h", out)
        self.assertIn(b"from-the-command", out)

    def test_off(self):
        rc, out = in_pty([sys.executable, str(SPLASH), "--", "sh", "-c", "echo plain"],
                         {**self.env, "FRAME_TWEAKS_SPLASH": "off"})
        self.assertEqual(rc, 0)
        self.assertNotIn(b"\x1b[?1049h", out)
        self.assertIn(b"plain", out)

    def test_the_command_doesnt_ignore_sigpipe(self):
        """Python ignores SIGPIPE, and a command exec'd from it did too, with all it started:
        under the splash and when it steps aside."""
        show = "grep SigIgn /proc/self/status"
        for env in (self.env, {**self.env, "FRAME_TWEAKS_SPLASH": "off"}):
            rc, out = in_pty([sys.executable, str(SPLASH), "--", "sh", "-c", show], env)
            mask = int(out.split(b"SigIgn:")[1].split()[0], 16)
            self.assertFalse(mask & (1 << 12), env.get("FRAME_TWEAKS_SPLASH"))       # (SIGPIPE is 13)

    def test_piped_input_stays_the_commands(self):
        rc, out = in_pty(["sh", "-c", 'echo yes-please | "$0" "$1" -- sh -c "read x; echo got:\$x"',
                          sys.executable, str(SPLASH)], self.env)
        self.assertEqual(rc, 0)
        self.assertIn(b"\x1b[?1049h", out)
        self.assertIn(b"got:yes-please", out)

    def test_a_command_ending_during_the_splash(self):
        """Its output and ✖ came only after the splash had gone; the exit status is kept."""
        env = {k: v for k, v in self.env.items() if k != "FRAME_TWEAKS_SPLASH"}
        rc, out = in_pty([sys.executable, str(SPLASH), "--", "sh", "-c", "echo quick-output; exit 4"], env)
        self.assertEqual(rc, 4)
        shown = out[:out.rindex(b"\x1b[?1049l")]
        self.assertIn(b"exit status 4", shown)
        self.assertIn(b"quick-output", shown)

    def test_ctrl_c_during_the_splash_reaches_the_command(self):
        env = {k: v for k, v in self.env.items() if k != "FRAME_TWEAKS_SPLASH"}
        start = time.monotonic()
        rc, out = in_pty([sys.executable, str(SPLASH), "--", "sh", "-c", "sleep 10"], env,
                         keys=[(b"\x1b[?1049h", b"\x03")])
        self.assertLess(time.monotonic() - start, 6)
        self.assertNotEqual(rc, 0)

    def test_chosen_off_in_preferences(self):
        off = Path(self.env["HOME"]) / "splash"
        off.write_text("off\n")
        env = {k: v for k, v in self.env.items() if k != "FRAME_TWEAKS_SPLASH"}
        rc, out = in_pty([sys.executable, str(SPLASH), "--", "sh", "-c", "echo plain"],
                         {**env, "FRAME_TWEAKS_SPLASH_FILE": str(off)})
        self.assertEqual(rc, 0)
        self.assertNotIn(b"\x1b[?1049h", out)
        self.assertIn(b"plain", out)

    def test_without_a_terminal_it_steps_aside(self):
        r = subprocess.run([sys.executable, str(SPLASH), "--", "sh", "-c", 'echo "x:$FRAME_TWEAKS_SPLASH_TTY"; exit 4'],
                           env=self.env, capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 4)
        self.assertEqual(r.stdout, "x:none\n")


if __name__ == "__main__":
    unittest.main()


class DemoInYourLanguage(unittest.TestCase):
    """Preferences' Show me plays a pretend install (--demo): its words go through the translations
    (they were English whatever language was chosen)."""

    def test_every_line_is_translated(self):
        import contextlib
        import io
        import re
        out = io.StringIO()
        with mock.patch.object(splash, "_", lambda t: "«" + t + "»"), mock.patch.object(splash.time, "sleep"), \
                contextlib.redirect_stdout(out):
            splash.demo_child()
        lines = [l for l in re.sub(r"\x1b\[[0-9;]*m", "", out.getvalue()).replace("\r", "\n").splitlines()
                 if l.strip() and "MB" not in l]
        for line in lines:
            if line.startswith("── "):
                self.assertTrue(line.endswith("»") or line.endswith(": ydotool"), line)   # (a title: translated)
            else:
                self.assertIn("«", line, line)
        self.assertIn("«Done.»", lines)
