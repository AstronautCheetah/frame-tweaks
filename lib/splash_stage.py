"""lib/splash.py's stage: the terminal's top half shows the picture (lib/splash_art.py) while the
command's output runs in the bottom half, and what the command wrote is kept (Transcript) to be
printed again at the end. Nothing here starts or waits for the command: lib/splash.py does."""
import fcntl
import os
import re
import select
import struct
import termios
import time

from splash_art import (BAR, BAR_DIM, BAR_TEXT, DONE, FAIL, SKY_BOTTOM, SPIN, Colours, Picture, cells, clamp,
                        ease_in_out, ease_out_back, fade, mix, text_cells)

INTRO = 2.4                   # seconds of splash before the output gets the bottom half
GLIDE = 0.5                   # of which the last ones move the picture up into the top half
FPS, INTRO_FPS = 12, 24       # frames a second: running, and during the splash
HOLD = 0.8                    # the last frame (✔ or ✖) stays this long before the output is printed again

SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def _(text):
    """The translation (lib/i18n.py), loaded when first needed: it looks at the keyboard's language."""
    global _
    try:
        from i18n import _ as tr
    except Exception:           # (anything: a picture is no reason to fail)
        def tr(t):
            return t
    _ = tr
    return tr(text)


# ---- what the command wrote ----------------------------------------------------------------

# (a CSI, an OSC, a DCS/APC/PM/SOS string, or ESC and one character, which is never one that
# opens one of those: an "ESC [" at the end of a read is a CSI still on its way)
SEQ = re.compile(rb"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[P^_X][\s\S]*?\x1b\\"
                 rb"|[ -/]*[0-OQ-WYZ\\`-~])")
SGR_RESET = re.compile(r"^(?:0?|0;.*)$")
ALT_SCREEN = re.compile(rb"\x1b\[\?[0-9;]*(?:1049|1047|47)[0-9;]*[hl]$")


class Transcript:
    """What the command wrote, as lines with their colours: printed again at the end, into the
    terminal's scrollback. A terminal without a height, enough for progress bars (carriage
    returns, erasing a line, moving up a few lines to redraw)."""

    def __init__(self, on_line=None):
        self.lines = [[]]
        self.row = self.col = 0
        self.sgr = ""
        self.on_line = on_line

    def text(self, s):
        for ch in s:
            if ch == "\n":
                if self.on_line:
                    self.on_line(self.plain(self.row))
                self.row += 1
                if self.row == len(self.lines):
                    self.lines.append([])
            elif ch == "\r":
                self.col = 0
            elif ch == "\b":
                self.col = max(0, self.col - 1)
            elif ch == "\t":
                self.put(" " * (8 - self.col % 8))
            elif ch >= " " and ch != "\x7f":
                self.put(ch)

    def put(self, s):
        line = self.lines[self.row]
        for ch in s:
            if self.col < len(line):
                line[self.col] = (ch, self.sgr)
            else:
                line.extend([(" ", "")] * (self.col - len(line)))
                line.append((ch, self.sgr))
            self.col += 1

    def csi(self, seq):
        params, final = seq[2:-1], seq[-1]
        if params.startswith("?"):
            return
        nums = [int(p) if p.isdigit() else 0 for p in params.split(";")] if params else []
        n = (nums[0] if nums else 0) or 1
        line = self.lines[self.row]
        if final == "m":
            if SGR_RESET.match(params):
                self.sgr = "" if params in ("", "0") else seq
            else:
                self.sgr += seq
        elif final == "K":
            mode = nums[0] if nums else 0
            if mode == 0:
                del line[self.col:]
            elif mode == 1:
                line[:self.col] = [(" ", "")] * min(self.col, len(line))
            else:
                line.clear()
        elif final in "AF":
            self.row = max(0, self.row - n)
            if final == "F":
                self.col = 0
        elif final in "BE":
            self.row += n
            while self.row >= len(self.lines):
                self.lines.append([])
            if final == "E":
                self.col = 0
        elif final == "C":
            self.col += n
        elif final == "D":
            self.col = max(0, self.col - n)
        elif final == "G":
            self.col = n - 1
        elif final == "J":
            mode = nums[0] if nums else 0
            if mode == 0:
                del line[self.col:]
                del self.lines[self.row + 1:]
            elif mode >= 2 and any(self.lines):      # (a cleared screen: what was on it stays in the log)
                self.lines.append([])
                self.row, self.col = len(self.lines) - 1, 0

    def plain(self, row):
        return "".join(ch for ch, _s in self.lines[row]).rstrip()

    def rendered(self):
        """The lines, coloured as they were (trailing blank lines left out)."""
        out = []
        for line in self.lines:
            s, cur = [], ""
            while line and line[-1] == (" ", ""):
                line = line[:-1]
            for ch, sgr in line:
                if sgr != cur:
                    s.append("\x1b[0m" + sgr)
                    cur = sgr
                s.append(ch)
            if cur:
                s.append("\x1b[0m")
            out.append("".join(s))
        while out and not out[-1]:
            out.pop()
        return out


def utf8_tail(data):
    """How many bytes at the end of data start a UTF-8 character that isn't complete yet."""
    for i in range(1, min(4, len(data)) + 1):
        b = data[-i]
        if b & 0xC0 == 0x80:
            continue
        need = 2 if b & 0xE0 == 0xC0 else 3 if b & 0xF0 == 0xE0 else 4 if b & 0xF8 == 0xF0 else 1
        return i if need > i else 0
    return 0


# ---- the stage: the terminal's top half, the command's output below -----------------------------

def term_size(fd):
    try:
        c, r = os.get_terminal_size(fd)
        return c, r
    except OSError:
        return 80, 24


def set_size(fd, rows, cols):
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", max(1, rows), max(1, cols), 0, 0))


class Stage:
    def __init__(self, out, master, cols, rows, still=False):
        self.out, self.master = out, master
        self.still = still
        self.colours = Colours(os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"))
        self.start = time.monotonic()
        self.step = ""
        self.result = None           # exit status, once the command has ended
        self.transcript = Transcript(on_line=self.saw_line)
        self.carry = b""
        self.carry_since = 0.0
        self.held = []               # the command's output while the splash plays
        self.intro = not still
        self.paused = False          # (the command has the whole terminal: alternate screen, or too small)
        self.alt_by_child = False
        self.child_saved = 0.0       # when the command saved its cursor (and hasn't restored it yet)
        self.cursor_visible = True
        self.prev = []
        self.resize(cols, rows, first=True)

    # -- layout
    def top_rows(self, rows):
        return max(8, rows // 2)

    def resize(self, cols, rows, first=False):
        self.cols, self.rows = cols, rows
        small = cols < 60 or rows < 16
        self.top = self.top_rows(rows)
        if not small:                       # (none for a tiny one: 0×0 crashed making it)
            self.picture = Picture(cols, 2 * (self.top - 1), 2 * rows, self.still)
            self.still_art = None
        self.prev = []
        if first:
            return
        if small:
            if not self.paused:
                self.pause()
            set_size(self.master, rows, cols)       # (paused or not, the command has the whole terminal)
            return
        if self.paused and not self.alt_by_child:
            self.resume()
        elif not self.paused and not self.intro:
            self.setup_split(clear=False)
        set_size(self.master, self.child_rows(), cols)

    def child_rows(self):
        return self.rows if self.paused or self.cols < 60 or self.rows < 16 else self.rows - self.top

    # -- output
    def write(self, s):
        data = s.encode("utf-8", "replace") if isinstance(s, str) else s
        while data:
            try:
                n = os.write(self.out, data)
            except InterruptedError:
                continue
            except BlockingIOError:             # (a terminal left non-blocking: wait until it takes more)
                select.select([], [self.out], [], 1)
                continue
            data = data[n:]

    def begin(self):
        # the alternate screen: what was on the terminal comes back at the end
        self.write("\x1b[?1049h\x1b[?25l\x1b[2J")
        if not self.intro:
            self.setup_split()

    def setup_split(self, clear=True):
        """The bottom half scrolls on its own, and the command's cursor stays in it (origin mode).
        (clear: below the picture, the terminal's own background; else the cursor goes to the
        last line of the bottom half, as after a resize.)"""
        self.write("\x1b[0m\x1b[%d;%dr\x1b[?6h" % (self.top + 1, self.rows))
        self.write("\x1b[1;1H\x1b[J" if clear else "\x1b[%d;1H" % (self.rows - self.top))
        self.write("\x1b[?25h" if self.cursor_visible else "")
        self.prev = []

    def pause(self):
        self.paused = True
        self.write("\x1b[?6l\x1b[r\x1b[0m\x1b[2J\x1b[H" + ("\x1b[?25h" if self.cursor_visible else ""))
        self.prev = []
        set_size(self.master, self.rows, self.cols)

    def resume(self):
        self.paused = False
        self.write("\x1b[0m\x1b[2J")
        self.setup_split()
        set_size(self.master, self.child_rows(), self.cols)

    def end_intro(self):
        if not self.intro:
            return
        self.intro = False
        if not self.paused:
            self.setup_split()
        for chunk in self.held:
            self.write(chunk)
        self.held = []

    def saw_line(self, line):
        line = line.strip()
        for mark in ("── ", "==> "):
            if line.startswith(mark) and len(line) > len(mark):
                self.step = line[len(mark):].strip()

    def child_output(self, data, now):
        """The command's output: shown below (or held during the splash), and kept."""
        data = self.carry + data
        self.carry = b""
        out = []
        pos = 0
        for m in SEQ.finditer(data):
            if m.start() > pos:
                out.append(self.text(data[pos:m.start()]))
            if ALT_SCREEN.match(m.group()) and out:
                # (a pager starting or ending: what came before it is written first, on the screen it was for)
                self.show(b"".join(out))
                out = []
            out.append(self.sequence(m.group()))
            pos = m.end()
        rest = data[pos:]
        esc = rest.find(b"\x1b")
        if esc >= 0 and len(rest) - esc < 4096:         # an escape sequence that isn't complete yet
            self.carry = rest[esc:]
            rest = rest[:esc]
        cut = utf8_tail(rest)
        if cut:
            self.carry = rest[-cut:] + self.carry
            rest = rest[:-cut]
        if rest:
            out.append(self.text(rest))
        if self.carry:
            self.carry_since = self.carry_since or now
        else:
            self.carry_since = 0.0
        self.show(b"".join(out))

    def show(self, chunk):
        if chunk:
            if self.intro:
                self.held.append(chunk)
            else:
                self.write(chunk)

    def flush_carry(self, now):
        """A piece of a sequence that never got its end: let it through as it is."""
        if self.carry and now - self.carry_since > 0.2:
            data, self.carry, self.carry_since = self.carry, b"", 0.0
            self.transcript.text(data.decode("utf-8", "replace"))
            (self.held.append(data) if self.intro else self.write(data))

    def text(self, data):
        self.transcript.text(data.decode("utf-8", "replace"))
        return data

    def sequence(self, seq):
        """One escape sequence from the command: passed on, kept out (it would undo the layout), or
        noted."""
        s = seq.decode("latin-1")
        if s.startswith("\x1b["):
            params, final = s[2:-1], s[-1]
            if params.startswith("?") and final in "hl":
                modes = params[1:].split(";")
                on = final == "h"
                if any(m in ("1049", "1047", "47") for m in modes):
                    # a pager or editor: it gets the whole terminal (we're on the alternate screen already)
                    if on and not self.paused:
                        self.alt_by_child = True
                        self.pause()
                    elif not on and self.alt_by_child:
                        self.alt_by_child = False
                        self.resume()
                    return b""
                if "25" in modes:
                    self.cursor_visible = on
                if "6" in modes and not self.paused:
                    return b""
                return seq
            if final == "r" and not self.paused:
                return b""                            # its own scrolling region: ours stays
            if final == "p" and "!" in params:
                return b""                            # a soft reset
            if final == "J" and params in ("2", "3") and not self.paused:
                self.transcript.csi(s)
                self.prev = []                        # (it clears the picture too: drawn again)
                return b"\x1b[H\x1b[J"                # only the bottom half (origin mode)
            if final == "s" and not params:
                self.child_saved = time.monotonic()
            elif final == "u" and not params:
                self.child_saved = 0.0
            self.transcript.csi(s)
            return seq
        if s == "\x1b7":
            self.child_saved = time.monotonic()
        elif s == "\x1b8":
            self.child_saved = 0.0
        elif s == "\x1bc":
            return b"" if self.paused else b"\x1b[H\x1b[J"     # a full reset: a clear bottom half
        return seq

    # -- frames
    def frame(self, now):
        if self.paused or (self.child_saved and now - self.child_saved < 2):
            return
        t = now - self.start
        if self.intro:
            cells_ = self.intro_frame(t)
        else:
            cells_ = self.split_frame(t)
        self.draw(cells_)

    def art(self, rows, top_px, t, comp_y, **kw):
        sky = self.picture.sky(2 * rows, top_px)
        canvas = [row[:] for row in sky]
        self.picture.render(canvas, top_px, t, comp_y, **kw)
        return cells(canvas)

    def letters(self, f):
        """How far each letter of the name has appeared, f from 0 to 1 over the reveal."""
        n = 11
        return [clamp((f * (n + 3) - i) / 4) for i in range(n)]

    def intro_frame(self, t):
        p = self.picture
        final_y = p.y0                        # (in the art area, which starts at the top of the screen)
        centred = (2 * self.rows - p.h) // 2
        glide = clamp((t - (INTRO - GLIDE)) / GLIDE)
        comp_y = round(centred + (final_y - centred) * ease_in_out(glide))
        logo = ease_out_back(clamp((t - 0.15) / 0.7)) if p.S else 1
        reveal = clamp((t - 0.6) / 0.9)
        shine = (t - 1.45) / 0.7 * 1.3 - 0.15 if 1.45 <= t < 2.15 else None
        rows = self.rows
        out = self.art(rows, 0, t, comp_y, logo_scale=max(0.0, logo), letters=self.letters(reveal), shine=shine)
        # (fading in from the terminal's dark)
        f = clamp(t / 0.35)
        if f < 1:
            out = [fade(row, f) for row in out]
        hint = _("Press any key to skip")
        if glide <= 0 and len(hint) + 4 < self.cols:
            x = (self.cols - len(hint)) // 2
            out[-1] = out[-1][:x] + text_cells(hint, len(hint), mix(SKY_BOTTOM, BAR_DIM, f * 0.8), SKY_BOTTOM) \
                + out[-1][x + len(hint):]
        if glide > 0:
            # below where the picture is going, the sky gives way to the output's dark
            g = ease_in_out(glide)
            for r in range(self.top, rows):
                out[r] = fade(out[r], 1 - g)
        return out

    def split_frame(self, t):
        p = self.picture
        shine = None
        if not self.still:
            cycle = (t - INTRO) % 7.0
            if cycle < 1.1:
                shine = cycle / 1.1 * 1.3 - 0.15
        if self.still:
            if self.still_art is None:
                self.still_art = self.art(self.top - 1, 0, t, p.y0)
            out = list(self.still_art)
        else:
            out = self.art(self.top - 1, 0, t, p.y0, shine=shine)
        out.append(self.status(t))
        return out

    def status(self, t):
        """The bar under the picture: what's being done (the command's last ── or ==> line), and for how long."""
        el = int(t)
        clock = " %d:%02d " % (el // 60, el % 60)
        if self.result is None:
            mark, colour = (SPINNER[int(t * 10) % len(SPINNER)] if not self.still else "…"), SPIN
            words = self.step or _("Working…")
        elif self.result == 0:
            mark, colour, words = "✔", DONE, _("Done")
        else:
            mark, colour, words = "✖", FAIL, _("Stopped with an error (exit status {code})").format(code=self.result)
        left = text_cells(" " + mark, 3, colour, BAR)
        mid = text_cells(" " + words, max(0, self.cols - 3 - len(clock)), BAR_TEXT, BAR)
        right = text_cells(clock, len(clock), BAR_DIM, BAR)
        return (left + mid + right)[:self.cols]

    def draw(self, rows):
        """Only the cells that changed since the last frame, between a save and a restore of the
        command's cursor (and its colours and origin mode)."""
        out = ["\x1b7\x1b[?25l\x1b[?6l"]
        changed = False
        prev = self.prev
        for r, row in enumerate(rows):
            old = prev[r] if r < len(prev) else None
            x, n = 0, min(len(row), self.cols)
            while x < n:
                if old is not None and x < len(old) and old[x] == row[x]:
                    x += 1
                    continue
                out.append("\x1b[%d;%dH" % (r + 1, x + 1))
                changed = True
                last = None
                while x < n and not (old is not None and x < len(old) and old[x] == row[x]):
                    fg, bg, ch = row[x]
                    if (fg, bg) != last:
                        out.append(self.colours.sgr(fg, bg))
                        last = (fg, bg)
                    out.append(ch)
                    x += 1
        out.append("\x1b[0m")
        if not self.intro:
            out.append("\x1b[?6h")          # (DECRC restores it too; said again for terminals that don't)
        out.append("\x1b8")
        if self.cursor_visible and not self.intro:
            out.append("\x1b[?25h")
        self.prev = rows
        if changed:
            self.write("".join(out))

    # -- the end
    def banner(self):
        """A small still card of the picture (on its sky) for the top of the output printed again."""
        width = min(self.cols, 100)
        fits = [Picture(width, 2 * rows, still=True, margin=1) for rows in (5, 6, 7, 8, 9, 10)]
        p = next((p for p in fits if p.k and p.S), None) or next((p for p in fits if p.k), None)
        if p is None:
            return []
        rows = p.px // 2
        canvas = [row[:] for row in p.sky(2 * rows, 0)]
        p.render(canvas, 0, 1.0, p.y0)
        return ["".join(self.colours.sgr(fg, bg) + ch for fg, bg, ch in row) + "\x1b[0m" for row in cells(canvas)]

    def finish(self):
        """Back to the terminal as it was, and the output printed again (into its scrollback)."""
        self.write("\x1b[0m\x1b[?6l\x1b[r\x1b[?1049l\x1b[?25h")

    def replay(self):
        """The output printed again, under the banner; returned too (FRAME_TWEAKS_SPLASH_REPLAY)."""
        out = self.banner() + [""]
        out += self.transcript.rendered()
        text = "\r\n".join(out) + "\r\n"
        self.write(text)
        return text


