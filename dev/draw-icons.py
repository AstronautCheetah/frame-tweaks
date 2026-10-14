#!/usr/bin/env python3
"""Draws Frame Tweaks' own app-menu icons: a KDE Breeze glyph, white, on a rounded coloured tile
(and Dictate's 🎤 from the Noto Color Emoji font). This script, with the Breeze SVGs it names,
is their source: Breeze's licence (LGPL-3.0-or-later; icons/README.md) asks for the editable
form of a modified icon to be available. Run it again after changing a glyph or a colour.
  dev/draw-icons.py            write the icons (icons/, and the tweaks' folders)
  dev/draw-icons.py --check    compare with the committed ones instead
Needs PyQt6, and SteamOS's breeze-icons (made with 6.14.0) and noto-fonts-emoji (2.042)."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import QRectF, Qt  # noqa: E402
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPen  # noqa: E402
from PyQt6.QtSvg import QSvgRenderer  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BREEZE = Path("/usr/share/icons/breeze-dark")
SIZE = 256
TILE, RADIUS = QRectF(8, 8, 240, 240), 52
GLYPH = QRectF(48, 48, 160, 160)

# output, Breeze glyph (its file under BREEZE: the symbolic sizes, as the 64 px device icons are
# full-colour pictures), tile colour, glyph box
TILES = [
    ("icons/frame-tweaks.png", "actions/24/configure.svg", "#7b4fc9", GLYPH),
    ("packs/original/adb-scrcpy/frame-tweaks-phone.png", "devices/24/smartphone.svg", "#2e9d4f", GLYPH),
    ("packs/original/arrowpad/frame-tweaks-arrowpad.png", "devices/24/input-keyboard.svg", "#3d7bd9", GLYPH),
    ("packs/integrations/nordvpn/frame-tweaks-nordvpn.png", "devices/24/network-vpn.svg", "#1f3b73", GLYPH),
    ("packs/original/wallet/frame-tweaks-lock.png", "actions/22/object-locked.svg", "#b8860b", QRectF(56, 56, 144, 144)),
]
AS_IS = [("packs/original/snip/frame-tweaks-snip.png", "apps/48/accessories-screenshot-tool.svg")]
EMOJI = ("packs/original/dictation/frame-tweaks-dictate.png", "🎤", "#c0392b", 27.5)   # (its own corners)
SMALLER = [("icons/frame-tweaks-128.png", 128), ("icons/frame-tweaks-64.png", 64)]   # (of icons/frame-tweaks.png)


def canvas():
    img = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    return img


def tile(colour, radius=RADIUS):
    img = canvas()
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(colour))
    p.drawRoundedRect(TILE, radius, radius)
    p.end()
    return img


def glyph_tile(svg, colour, box):
    glyph = canvas()
    p = QPainter(glyph)
    QSvgRenderer(str(BREEZE / svg)).render(p, box)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)     # the glyph, in white
    p.fillRect(glyph.rect(), Qt.GlobalColor.white)
    p.end()
    img = tile(colour)
    p = QPainter(img)
    p.drawImage(0, 0, glyph)
    p.end()
    return img


def as_is(svg):
    img = canvas()
    p = QPainter(img)
    QSvgRenderer(str(BREEZE / svg)).render(p, QRectF(0, 0, SIZE, SIZE))
    p.end()
    return img


def emoji_tile(text, colour, radius):
    img = tile(colour, radius)
    p = QPainter(img)
    font = QFont("Noto Color Emoji")
    font.setPixelSize(150)
    p.setFont(font)
    p.setPen(QPen(Qt.GlobalColor.white))
    p.drawText(QRectF(0, 0, SIZE, SIZE), Qt.AlignmentFlag.AlignCenter, text)
    p.end()
    return img


def icons():
    out = {path: glyph_tile(svg, colour, box) for path, svg, colour, box in TILES}
    out.update({path: as_is(svg) for path, svg in AS_IS})
    out[EMOJI[0]] = emoji_tile(*EMOJI[1:])
    big = out["icons/frame-tweaks.png"]
    for path, px in SMALLER:
        out[path] = big.scaled(px, px, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    return out


def difference(a, b):
    """(share of pixels that differ, largest difference in one channel): 0 and 0 for the same."""
    a, b = (i.convertToFormat(QImage.Format.Format_ARGB32) for i in (a, b))
    if a.size() != b.size():
        return 1.0, 255
    n, worst, w, h = 0, 0, a.width(), a.height()
    for y in range(h):
        for x in range(w):
            pa, pb = a.pixel(x, y), b.pixel(x, y)
            if pa != pb:
                n += 1
                worst = max(worst, *(abs((pa >> s & 255) - (pb >> s & 255)) for s in (0, 8, 16, 24)))
    return n / (w * h), worst


def main():
    app = QGuiApplication(sys.argv[:1])  # noqa: F841  (kept: fonts need it)
    check = "--check" in sys.argv
    bad = 0
    for path, img in icons().items():
        if not check:
            img.save(str(ROOT / path))
            print("wrote", path)
            continue
        share, worst = difference(img, QImage(str(ROOT / path)))
        same = share == 0 or worst <= 8          # (antialiasing in another Qt version)
        bad += not same
        print(f"{'same' if same else 'DIFFERENT'}  {path}  ({share:.1%} of pixels, at most {worst} apart)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
