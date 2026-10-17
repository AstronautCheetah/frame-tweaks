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
import fcntl
import locale
import math
import os
import random
import re
import select
import signal
import struct
import sys
import termios
import time
import tty
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INTRO = 2.4                   # seconds of splash before the output gets the bottom half
GLIDE = 0.5                   # of which the last ones move the picture up into the top half
FPS, INTRO_FPS = 12, 24       # frames a second: running, and during the splash
HOLD = 0.8                    # the last frame (✔ or ✖) stays this long before the output is printed again

# Colours (R, G, B)
SKY_TOP, SKY_BOTTOM = (40, 22, 76), (12, 14, 36)      # deep violet to midnight blue
TILE_TOP, TILE_BOTTOM = (146, 104, 222), (104, 64, 182)   # the app icon's tile (#7b4fc9 between)
WHITE = (250, 248, 255)
TITLE_TOP, TITLE_BOTTOM = (255, 255, 255), (190, 164, 255)
SHADOW = (14, 8, 30)
STAR = (236, 230, 255)
BAR, BAR_TEXT, BAR_DIM = (30, 20, 56), (214, 204, 240), (140, 126, 186)
SPIN, DONE, FAIL = (176, 146, 255), (112, 222, 142), (255, 112, 124)

# A 5×7 pixel font, the letters of the name only.
GLYPHS = {
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
}
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


def mix(a, b, f):
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f)


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def ease_out_back(f):
    f -= 1
    return 1 + f * f * (2.7 * f + 1.7)


def ease_in_out(f):
    return f * f * (3 - 2 * f)


# ---- colours as escape sequences -------------------------------------------------------------

def _xterm256(c):
    r, g, b = (int(v) for v in c)

    def level(v):
        return 0 if v < 48 else 1 if v < 115 else (v - 35) // 40
    cube = (0, 95, 135, 175, 215, 255)
    ri, gi, bi = level(r), level(g), level(b)
    gray = min(23, max(0, ((r + g + b) // 3 - 3) // 10))
    gv = 8 + 10 * gray
    if (cube[ri] - r) ** 2 + (cube[gi] - g) ** 2 + (cube[bi] - b) ** 2 <= (gv - r) ** 2 + (gv - g) ** 2 + (gv - b) ** 2:
        return 16 + 36 * ri + 6 * gi + bi
    return 232 + gray


class Colours:
    def __init__(self, truecolor):
        self.truecolor = truecolor
        self.cache = {}

    def sgr(self, fg, bg):
        key = (fg, bg)
        s = self.cache.get(key)
        if s is None:
            if self.truecolor:
                s = "\x1b[0;38;2;%d;%d;%d;48;2;%d;%d;%dm" % (*fg, *bg)
            else:
                s = "\x1b[0;38;5;%d;48;5;%dm" % (_xterm256(fg), _xterm256(bg))
            self.cache[key] = s
        return s


def q(c):
    """A colour rounded (to steps of 4): fewer cells change from frame to frame."""
    return (int(c[0]) & ~3, int(c[1]) & ~3, int(c[2]) & ~3)


# ---- the picture -------------------------------------------------------------------------------

class Picture:
    """The logo and name on a dark sky with a few twinkling stars, laid out for an art area
    `cols` wide and `px` pixels (2 × rows) high: as big as fits."""

    def __init__(self, cols, px, screen_px=None, still=False, margin=2):
        self.cols, self.px, self.still, self.margin = cols, px, still, margin
        self.layout()
        screen_px = screen_px or px
        rnd = random.Random(7)
        self.stars = [(rnd.randrange(cols), rnd.randrange(screen_px), rnd.uniform(0, 6.3), rnd.uniform(0.6, 1.6),
                       rnd.uniform(0.35, 0.9)) for _i in range(max(6, cols * screen_px // 110))]
        self.sky_cache = {}
        self.tile_cache = {}

    def layout(self):
        cols, px = self.cols, self.px
        self.k = self.S = self.gap = self.tw = self.th = 0        # (nothing fits: the sky alone)
        self.stacked = False
        for k, stacked in ((3, False), (3, True), (2, False), (2, True), (1, False), (1, True)):
            tw = 35 * k if stacked else 68 * k
            th = 17 * k if stacked else 7 * k
            S = th if stacked else round(th * 1.7)
            S += S % 2
            S = max(S, 12)
            gap = max(4, S // 3)
            if S + gap + tw <= cols - 4 and max(S, th) + 2 * self.margin <= px:
                self.k, self.stacked, self.S, self.gap, self.tw, self.th = k, stacked, S, gap, tw, th
                break
        else:
            if 68 <= cols - 4 and 7 + 2 * self.margin <= px:          # the name alone
                self.k, self.S, self.gap, self.tw, self.th = 1, 0, 0, 68, 7
            elif px >= 12 + 2 * self.margin:          # the logo alone
                self.S = min(px - 2 * self.margin, 24)
                self.S -= self.S % 2
                self.gap = self.tw = self.th = 0
        self.w = self.S + self.gap + self.tw
        self.h = max(self.S, self.th)
        self.x0 = (cols - self.w) // 2
        self.y0 = (px - self.h) // 2              # (in the art area; the splash moves it)
        self.title_px = self.title_pixels() if self.k else []

    def title_pixels(self):
        """[(x, y, shade, letter)] of the name at scale k: shade 0 at the top of a line to 1 at
        its bottom, letter the letter's number (for revealing them one by one)."""
        k, out, n = self.k, [], 0
        lines = ("FRAME", "TWEAKS") if self.stacked else ("FRAME TWEAKS",)
        for li, text in enumerate(lines):
            x, y0 = 0, li * 10 * k
            for ch in text:
                if ch == " ":
                    x += 3 * k
                    continue
                for gy, row in enumerate(GLYPHS[ch]):
                    for gx, on in enumerate(row):
                        if on == "#":
                            for dy in range(k):
                                for dx in range(k):
                                    out.append((x + gx * k + dx, y0 + gy * k + dy, (gy * k + dy) / (7 * k - 1), n))
                x += 6 * k
                n += 1
        return out

    def sky(self, rows_px, top_px):
        """The sky for a canvas of rows_px pixel rows starting at top_px of the art area."""
        key = (rows_px, top_px)
        s = self.sky_cache.get(key)
        if s is None:
            cols, px = self.cols, max(1, self.px)
            s = []
            for y in range(top_px, top_px + rows_px):
                fy = clamp(y / px)
                s.append([mix(SKY_TOP, SKY_BOTTOM, clamp(0.75 * fy + 0.25 * x / cols)) for x in range(cols)])
            if len(self.sky_cache) > 8:
                self.sky_cache.clear()
            self.sky_cache[key] = s
        return s

    def tile(self, S):
        """The tile and its two slider lines: {(x, y): (colour, alpha)} for a tile S pixels across."""
        t = self.tile_cache.get(S)
        if t is None:
            t = {}
            h, r = S / 2, S * 0.24
            line = max(1, round(S / 14))
            ys = (round(S * 0.36), round(S * 0.64))
            for y in range(S):
                for x in range(S):
                    qx, qy = abs(x + 0.5 - h) - (h - r), abs(y + 0.5 - h) - (h - r)
                    d = math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r
                    a = clamp(0.5 - d)
                    if a <= 0:
                        continue
                    c = mix(TILE_TOP, TILE_BOTTOM, y / max(1, S - 1))
                    if S * 0.27 <= x + 0.5 <= S * 0.73 and any(yy - line // 2 <= y < yy - line // 2 + line for yy in ys):
                        c = WHITE
                    t[(x, y)] = (c, a)
            self.tile_cache = {S: t} if len(self.tile_cache) > 40 else {**self.tile_cache, S: t}
        return t

    def knobs(self, t):
        """Where the two knobs are along their lines (0 to 1): they glide, as if someone tweaks them."""
        if self.still:
            return 0.68, 0.32
        return 0.62 + 0.24 * math.sin(t * 0.9), 0.36 + 0.26 * math.sin(t * 0.67 + 2.1)

    def render(self, canvas, top_px, t, comp_y, logo_scale=1.0, letters=None, shine=None):
        """Draw onto canvas (rows of colours; its first row is pixel row top_px of the art area)
        with the composition's top at comp_y. letters: how far each letter has appeared (0 to 1),
        None for all; shine: where a light band crossing the name is (0 to 1), None for none."""
        rows_px = len(canvas)
        # stars (in pixels of the whole screen, so they stay put while the picture moves), not
        # on the logo or the name
        for (x, y, phase, speed, bright) in self.stars:
            if y < top_px or y >= top_px + rows_px or x >= self.cols:
                continue
            if self.x0 - 2 <= x < self.x0 + self.w + 2 and comp_y - 2 <= y < comp_y + self.h + 2:
                continue
            b = bright * (0.55 if self.still else (0.5 + 0.5 * math.sin(t * speed + phase)) ** 3)
            if b > 0.06:
                row = canvas[y - top_px]
                row[x] = mix(row[x], STAR, round(b * 5) / 5)
        # the logo
        if self.S:
            S = max(2, round(self.S * logo_scale))
            S -= S % 2
            tile = self.tile(S)
            ox = self.x0 + (self.S - S) // 2
            oy = comp_y + (self.h - S) // 2 - top_px
            k1, k2 = self.knobs(t)
            kr = max(1.6, S * 0.1)            # (not under a pixel and a half: a small logo keeps its knobs)
            ring = max(0.8, S * 0.058)
            lo, hi = S * 0.27 + kr * 0.6, S * 0.73 - kr * 0.6
            knobs = ((lo + (hi - lo) * k1, S * 0.36, False), (lo + (hi - lo) * k2, S * 0.64, True))
            for (x, y), (c, a) in tile.items():
                cy, cx = oy + y, ox + x
                if 0 <= cy < rows_px and 0 <= cx < self.cols:
                    for (kx, ky, hollow) in knobs:
                        d = math.hypot(x + 0.5 - kx, y + 0.5 - ky)
                        ka = clamp(kr + 0.5 - d)
                        if ka > 0:
                            if hollow:
                                inner = clamp(ring + 0.5 - d)
                                c = mix(mix(c, WHITE, ka), mix(TILE_TOP, TILE_BOTTOM, y / max(1, S - 1)), inner)
                            else:
                                c = mix(c, WHITE, ka)
                    if shine is not None:
                        band = 1 - abs((ox + x - self.x0) / max(1, self.w) - shine + (y / max(1, S)) * 0.15) / 0.07
                        if band > 0:
                            c = mix(c, (200, 180, 250), 0.35 * band)
                    canvas[cy][cx] = mix(canvas[cy][cx], c, a)
        # the name
        if self.k:
            tx = self.x0 + self.S + self.gap
            ty = comp_y + (self.h - self.th) // 2 - top_px
            sh = 1 if self.k > 1 else 0
            for (x, y, shade, li) in self.title_px:
                f = 1.0 if letters is None else letters[li]
                if f <= 0:
                    continue
                rise = 0 if f >= 1 else round((1 - ease_in_out(f)) * 3 * self.k)
                cx, cy = tx + x, ty + y + rise
                if sh and 0 <= cy + sh < rows_px and 0 <= cx + sh < self.cols:
                    canvas[cy + sh][cx + sh] = mix(canvas[cy + sh][cx + sh], SHADOW, 0.8 * f)
            for (x, y, shade, li) in self.title_px:
                f = 1.0 if letters is None else letters[li]
                if f <= 0:
                    continue
                rise = 0 if f >= 1 else round((1 - ease_in_out(f)) * 3 * self.k)
                cx, cy = tx + x, ty + y + rise
                if 0 <= cy < rows_px and 0 <= cx < self.cols:
                    c = mix(TITLE_TOP, TITLE_BOTTOM, shade)
                    if shine is not None:
                        band = 1 - abs((cx - self.x0) / max(1, self.w) - shine + (y / max(1, self.th)) * 0.15) / 0.06
                        if band > 0:
                            c = mix(c, (255, 255, 255), band)
                    canvas[cy][cx] = mix(canvas[cy][cx], c, f)


def cells(canvas):
    """Pixel rows (pairs) as character cells: (text colour, background colour, character)."""
    out = []
    for r in range(0, len(canvas) - 1, 2):
        row = []
        for a, b in zip(canvas[r], canvas[r + 1]):
            a, b = q(a), q(b)
            row.append((a, b, "▀") if a != b else (a, a, " "))
        out.append(row)
    return out


def text_cells(text, width, fg, bg):
    """A line of text as cells (width wide, cut with … if longer)."""
    if len(text) > width:
        text = text[:max(0, width - 1)] + "…"
    fg, bg = q(fg), q(bg)
    return [(fg, bg, ch) for ch in text.ljust(width)]


def fade(row, f):
    """Cells faded towards black (f 0: black, 1: as they are)."""
    return [(q(mix((0, 0, 0), a, f)), q(mix((0, 0, 0), b, f)), ch) for a, b, ch in row]


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
        out = self.banner() + [""]
        out += self.transcript.rendered()
        self.write("\r\n".join(out) + "\r\n")


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
        stage.replay()
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
    w = sys.stdout.write

    def say(text, pause=0.35):
        w(text + "\n")
        sys.stdout.flush()
        time.sleep(pause)
    say("\x1b[1;34m==>\x1b[0m Setting up PyQt6, a window toolkit (about 280 MB)", 0.6)
    for i in range(0, 101, 4):
        bar = "━" * (i * 30 // 100) + "\x1b[2m" + "━" * (30 - i * 30 // 100) + "\x1b[0m"
        w("\r   \x1b[35m%s\x1b[0m %3d%% · %.1f/62.4 MB" % (bar, i, 62.4 * i / 100))
        sys.stdout.flush()
        time.sleep(0.08)
    w("\n")
    for tid, title, lines in (("ydotool", "ydotool", ["Fetching ydotool 1.0.4-2 (Arch Linux ARM, signature checked)",
                                                    "Installed ydotool and ydotoold in ~/.local/bin"]),
                              ("arrowpad", "Arrow Pad", ["Creating Arrow Pad's Python setup",
                                                         "Added Arrow Pad to the app menu",
                                                         "\x1b[32m✔\x1b[0m Arrow Pad is ready: Ctrl+Alt+A shows it"]),
                              ("snip", "Screen snip", ["Linking frame-snip into ~/.local/bin",
                                                       "Narrate's voice: Piper (offline)"])):
        say("\x1b[1m── %s: %s\x1b[0m" % (tid, title), 0.5)
        for line in lines:
            say("  " + line, 0.45)
        say("", 0.2)
    say("\x1b[1mDone.\x1b[0m", 0.3)
    for tid, st in (("ydotool", "running"), ("arrowpad", "installed"), ("snip", "installed")):
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
