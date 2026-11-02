"""lib/splash.py's picture: Frame Tweaks' logo, its two sliders and its name on a dark sky with a
few twinkling stars, drawn in "▀" character cells (two pixels to a cell), and those cells' colours
as escape sequences (24-bit, or the terminal's 256 colours). Nothing here touches the terminal."""
import math
import random

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
