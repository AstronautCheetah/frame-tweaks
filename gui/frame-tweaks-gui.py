#!/usr/bin/env python3
"""Frame Tweaks: graphical installer.

Rows grouped by category (convenience first, developer tools last). Tick to install, untick
to remove; click a row for details (what it is, why it's here, who made it, its README).
Rows can be hidden (never removed); some start hidden, like whisper-frame while its window mic
costs VR performance. Status checks run in the background so the window never freezes.
Changes run in a Konsole window via ./install.sh. Styled after Full Keyboard's Graphite theme.
"""
import html
import json
import os
import posixpath
import re
import shlex
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PyQt6 import sip
from PyQt6.QtCore import QEvent, QObject, QPoint, QProcess, Qt, QTimer, QUrl
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtGui import QCursor, QDesktopServices, QFont, QFontInfo, QFontMetrics, QIcon, QImage
from PyQt6.QtWidgets import (QAbstractButton, QAbstractSlider, QApplication, QCheckBox, QGridLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QStackedWidget, QTextBrowser,
                             QVBoxLayout, QWidget)

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))
os.environ.setdefault("FRAME_TWEAKS_LIB", str(REPO / "lib"))   # (packs' scripts source the helpers through it)
sys.path.insert(0, str(REPO / "gui"))           # (its pages, e.g. wallet_page.py)
import sft  # noqa: E402  (shared with ./install.sh: components, hidden rows, settings)
from sft import (COLLAPSED, HIDDEN_CATS, component, components, current_release, release_channel,  # noqa: E402
                 run_label, write_set)
import browser  # noqa: E402  (web links, across the VR and desktop sessions)
import manifest  # noqa: E402
import i18n  # noqa: E402
from i18n import _, N_, ngettext  # noqa: E402  (translations: locale/README.md)
# The window follows the keyboard itself (not the language ./install.sh found when it started it),
# and whatever it runs (status checks, installs, Run) gets the window's language.
i18n.INHERIT = False
i18n.CATALOGUE = i18n.Catalogue()
sft.load(refresh=True)                    # (sft read the tweaks' text on import, maybe in the
sft.SETTINGS = sft.settings_specs()       # language this window was started with: again, in ours)


def pass_language():
    """What the window runs gets its language; running programs (Arrow Pad, Screen snip) hear of it."""
    os.environ["FRAME_TWEAKS_LANG_RESOLVED"] = i18n.CATALOGUE.language or "en"
    i18n.announce(i18n.CATALOGUE.language)


pass_language()
from wallet_page import FLATPAK_ICONS, WalletApps  # noqa: E402  (Wallet apps page)
from packs_page import Packs  # noqa: E402  (Packs page)
from prefs_page import Preferences, window_prefs  # noqa: E402  (⚙ Preferences page)
from report_page import ReportPage  # noqa: E402  (🐞 Report a problem page)
import link_tip  # noqa: E402  (the pop-up after a click on a link)
GITHUB = "https://github.com/AstronautCheetah/frame-tweaks/tree/main"
ICONS = Path.home() / ".local/share/icons/hicolor/256x256/apps"
BREEZE = Path("/usr/share/icons/breeze-dark")
KNOWN_ISSUES = {c["id"]: c["known_issue"] for c in components() if c["known_issue"]}   # (known_issue: in its manifest)

STYLE = """
QWidget { background: #0b1016; color: #e8ecf0; font-size: 14px; }
QLabel#title { font-size: 20px; font-weight: 600; }
QWidget#cathead QPushButton#cattoggle { background: transparent; border: none; text-align: left;
                  font-size: 13px; font-weight: 700; color: #7fb2e5; letter-spacing: 1px; padding: 10px 4px 2px 4px; }
QWidget#cathead QPushButton#cattoggle:hover { color: #a9cdf0; }
QWidget#cathead QPushButton#cathide { padding: 3px 10px; font-size: 12px; margin-top: 8px; }
QLabel#category { font-size: 13px; font-weight: 700; color: #7fb2e5; letter-spacing: 1px;
                  padding: 10px 4px 2px 4px; }
QLabel#name { font-size: 15px; font-weight: 600; }
QLabel#desc { color: #9aa6b2; }
QLabel[status="ok"] { color: #5cc77a; } QLabel[status="warn"] { color: #e0b33a; }
QLabel[status="missing"], QLabel[status="checking"] { color: #6b7783; }
QWidget#row { background: #161c23; border-radius: 10px; }
QWidget#row:hover { background: #1c242d; }
QWidget#row[hidden_row="true"] { background: #11161c; }
QWidget#row[focused="true"] { background: #1f2a36; border: 2px solid #7fb2e5; }
QWidget#row QLabel, QWidget#row QCheckBox, QWidget#row QWidget#spacer { background: transparent; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2c333b, stop:0.5 #232a32, stop:1 #1c232a);
              border: none; border-bottom: 3px solid #0c1015; border-radius: 8px; padding: 6px 14px; }
QPushButton:hover { background: #3d4855; }
QPushButton:checked { background: #355b7a; }
QPushButton#apply { background: #355b7a; font-weight: 600; }
QPushButton#apply:disabled { background: #161c23; color: #3a434d; }
QPushButton#danger { background: #7a2e2e; font-weight: 600; }
QPushButton#danger:hover { background: #963838; }
QWidget#ask { background: #141b23; border: 1px solid #2a3542; border-radius: 8px; }
QPushButton#info { padding: 6px 10px; }
QPushButton#info:disabled { color: #3a434d; }
QWidget#timer { background: transparent; }
QPushButton#again { padding: 0px 10px 3px 10px; font-size: 24px; font-weight: 600; }
QPushButton#again:disabled { color: #3a434d; }
QPushButton#run { background: #2f6b46; font-weight: 600; min-width: 92px; }
QPushButton#run:hover { background: #3c8a5a; }
QPushButton#run:disabled { background: #161c23; color: #3a434d; }
QPushButton#run[help="true"] { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2c333b, stop:0.5 #232a32, stop:1 #1c232a); font-weight: 400; }
QCheckBox { padding: 8px; }
QCheckBox::indicator { width: 33px; height: 33px; }
QScrollArea { border: none; }
QScrollBar:vertical { background: #11161c; width: 28px; margin: 0 0 0 6px; border-radius: 11px; }
QScrollBar:horizontal { background: #11161c; height: 28px; margin: 6px 0 0 0; border-radius: 11px; }
QScrollBar::handle { background: #2f3a46; border: 1px solid #3a4756; border-radius: 9px; margin: 2px; }
QScrollBar::handle:vertical { min-height: 56px; }
QScrollBar::handle:horizontal { min-width: 56px; }
QScrollBar::handle:hover { background: #3d4b5a; border-color: #4f6175; }
QScrollBar::handle:pressed { background: #355b7a; border-color: #7fb2e5; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; border: none; background: none; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
QWidget#row[cta="true"] { background: #142130; border: 1px solid #2c4a66; }
QWidget#row[cta="true"]:hover { background: #18283a; }
QTextBrowser { background: #11161c; border: none; border-radius: 8px; padding: 8px; }
QLabel#issue { background: #2a2312; color: #e0b33a; border-radius: 8px; padding: 10px; }
QLabel#notice { color: #e0b33a; }
"""
# Tick boxes draw an empty box when unticked, so every row shows where to click.
_BOX = Path(__file__).resolve().parent / "images"
STYLE += f"""
QCheckBox::indicator:unchecked {{ image: url({_BOX}/box.svg); }}
QCheckBox::indicator:unchecked:hover {{ image: url({_BOX}/box-hover.svg); }}
QCheckBox::indicator:checked {{ image: url({_BOX}/box-checked.svg); }}
QRadioButton {{ padding: 8px; }}
QRadioButton::indicator {{ width: 33px; height: 33px; }}
QRadioButton::indicator:unchecked {{ image: url({_BOX}/radio.svg); }}
QRadioButton::indicator:unchecked:hover {{ image: url({_BOX}/radio-hover.svg); }}
QRadioButton::indicator:checked {{ image: url({_BOX}/radio-checked.svg); }}
"""



RESTART = 3      # a status code of the window's own: installed, but SteamVR loads it only as it starts
UNLOAD = 4       # and: uninstalled, but SteamVR runs what it loaded until it restarts
UNAVAILABLE = 256    # and: its pack or folder went since the list was read (no program exits with 256)
GONE = (1, UNLOAD, UNAVAILABLE)   # the codes of a tweak that isn't installed


def status(cid):
    """(code, text): 0 ok, 1 not installed, 2 needs attention; a status.sh line "restart …" is
    RESTART (exit 2: installed) or UNLOAD (exit 1: uninstalled), waiting for a SteamVR restart.
    A status.sh that stops without saying "missing" or "restart" (a command in it failed) didn't
    find the tweak missing: installed by Frame Tweaks (its record), or with an exit code that
    isn't 0, 1 or 2, it's 2, "status check failed" (./install.sh status_of has the same rule).
    UNAVAILABLE: its pack or folder went since the window read the list."""
    c = component(cid)
    if c is None or sft.script(c, "status") is None:     # (its pack or folder went since the list was read)
        return UNAVAILABLE, _("not available any more")
    try:
        # (a check that never returns would hold a worker for good; four of them, every status)
        r = subprocess.run(sft.script(component(cid), "status"), capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return 2, _("status check didn't finish (took over a minute)")
    out = r.stdout.strip()
    text = out.split(None, 1)[-1] if out else ""
    word = out.split(None, 1)[:1]
    if word == ["restart"] and r.returncode in (1, 2):
        return {2: RESTART, 1: UNLOAD}[r.returncode], text
    if r.returncode not in (0, 1, 2) or (r.returncode == 1 and word != ["missing"] and sft.installed_record(cid)):
        said = [line for line in re.sub(r"\x1b\[[0-9;]*m", "", r.stderr or "").splitlines() if line.strip()]
        return 2, (_("status check failed: %s") % said[-1].strip() if said else _("status check failed"))
    return r.returncode, text


def update_check(cid):
    """(installed, latest) when its update check (<id>/update-check.sh, or a link's version:)
    reports a newer upstream version, else None."""
    c = component(cid)
    cmd = sft.script(c, "update-check") if c else None
    if cmd is None:                                      # (its pack or folder went since the list was read)
        return None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        return None
    if len(out) == 2 and version_tuple(out[1]) > version_tuple(out[0]):
        return out[0], out[1]
    return None


STABLE_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
ANY_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.]+))?$")
def newest_release(tags, channel="stable"):
    """Newest tag (without the leading v): stable vX.Y.Z only, or with pre-releases on beta,
    where vX.Y.Z-rc1 ranks below vX.Y.Z."""
    pattern = ANY_TAG if channel == "beta" else STABLE_TAG
    ok = [t for t in tags if pattern.match(t)]
    return max(ok, key=release_key)[1:] if ok else None


def release_key(tag):
    """Sort key for "v1.2.0" / "1.2.0-rc.1": a pre-release sorts below its final version, and the
    numbers in it count as numbers (rc.10 after rc.9), as ./install.sh's sort -V has it."""
    m = ANY_TAG.match(tag if tag.startswith("v") else "v" + tag)
    if not m:
        return (0, 0, 0, False, ())
    pre = tuple((0, int(p)) if p.isdigit() else (1, p) for p in re.findall(r"\d+|\D+", m[4] or ""))
    return (int(m[1]), int(m[2]), int(m[3]), m[4] is None, pre)


def close_prompt():
    """How the terminal of an install, update or removal closes (quoted for bash). In VR (the Steam
    session's display), a floating window has an X button below it: easier than a key when there's
    no keyboard."""
    return shlex.quote(_("Press Enter to close, or press the X button floating below to close.")
                       if os.environ.get("DISPLAY") == ":0" else _("Press Enter to close…"))


def in_terminal(proc, script):
    """Start script (bash) in a Konsole window of its own, through a shell that waits for it: proc
    finishes when the terminal closes, and closing this window (which kills proc) leaves the
    terminal, and the install running in it, alone. (Konsole's messages go nowhere, as before:
    nothing read them, and once this window is gone a pipe to it would stop Konsole.)"""
    proc.start("bash", ["-c", 'konsole --separate -e bash -c "$1" >/dev/null 2>&1 & wait', "konsole", script])


def self_update_check():
    """Newest vX.Y.Z tag of this repo on GitHub, if newer than VERSION (needs git access); "" if
    there's none newer, None when it couldn't look (offline, say)."""
    try:
        r = subprocess.run(["git", "-C", str(REPO), "ls-remote", "--tags", "--refs", "origin", "v*"],
                           capture_output=True, text=True, timeout=15,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    tags = [line.rsplit("/", 1)[-1] for line in r.stdout.splitlines() if "refs/tags/v" in line]
    newest = newest_release(tags, release_channel())
    current = current_release()
    return newest if newest and release_key(newest) > release_key(current) else ""




def readme_links(text, comp):
    """Relative links in a README, made absolute: on GitHub for the official packs (they don't
    resolve outside the repo), as files for a user's pack."""
    def target(link):
        if comp["official"]:
            rel = posixpath.normpath(f"packs/{comp['pack_dir'].name}/{comp['id']}/{link}" if comp.get("id") else link)
            return GITHUB.rsplit("/tree/", 1)[0] + "/blob/main/" + rel
        return (comp["dir"] / link).resolve().as_uri()
    # Pictures from the local copy (the window can't fetch web images), links to GitHub.
    text = re.sub(r"!\[([^\]]*)\]\((?!https?:|file:)([^)\s]+)\)",
                  lambda m: f"![{m.group(1)}]({(comp['dir'] / m.group(2)).resolve().as_uri()})", text)
    return re.sub(r"\]\((?!https?:|#|mailto:|file:)([^)]+)\)", lambda m: f"]({target(m.group(1))})", text)


def plain_markdown(text):
    """GitHub-style README HTML as Markdown the window can show (Qt's Markdown reader loses the
    text after an HTML block it can't place, so none may be left): centred pictures become
    pictures, with their caption (<br><sub>…</sub>) as a line in italics; folded <details>
    sections show open with their summary in bold; badges (pictures from the web) are left out;
    and any <br> left over becomes a space, any <sub> goes, its text kept. Code is left as it is."""
    def picture(m):
        imgs = [html_attrs(tag) for tag in re.findall(r"<img\b[^>]*>", m[0])]
        caption = re.search(r"<sub>(.*?)</sub>", m[0], flags=re.S)
        return " ".join(f"![{a.get('alt', '')}]({a['src']})" for a in imgs if a.get("src")) + (
            f"\n\n*{' '.join(caption[1].split())}*" if caption else "")
    # (a picture's paragraph ends at its </p>, or where an HTML block does: a blank line)
    text = in_prose(text, lambda b: re.sub(r"<p\b[^>]*>\s*<img\b(?:(?!<p\b|</p>|\n[ \t]*\n).)*(?:</p>|(?=\n[ \t]*\n)|\Z)",
                                           picture, b, flags=re.S), blocks=True)
    text = in_prose(text, lambda p: re.sub(r"</?sub>", "", re.sub(r"<br\s*/?>", " ", p)))
    text = literal_placeholders(text)
    text = re.sub(r"<details>\s*<summary>(.*?)</summary>", lambda m: f"**{m[1].strip()}**\n", text, flags=re.S)
    text = re.sub(r"</details>", "", text)
    text = re.sub(r"<!--.*?-->\n?", "", text, flags=re.S)
    return re.sub(r"^\[!\[[^\]]*\]\(https?://[^)]*\)\]\([^)]*\)\s*$", "", text, flags=re.M)


HTML_TAGS = {"a", "b", "i", "em", "strong", "code", "kbd", "img", "p", "br", "sub", "sup", "details", "summary",
             "div", "span", "table", "thead", "tbody", "tr", "td", "th", "ul", "ol", "li", "pre", "hr", "blockquote",
             "h1", "h2", "h3", "h4", "h5", "h6", "picture", "source", "video", "small", "s", "u", "dl", "dt", "dd",
             "mark", "del", "ins", "abbr", "q"}


def in_prose(text, fn, blocks=False):
    """Markdown with fn applied to what isn't code: ``` blocks are left as they are (indented ones
    too, in a list item); and, unless blocks (fn given all the text between them), 4-space-indented
    lines and `inline code` too."""
    def line(l):
        if l.startswith("    "):
            return l
        return "".join(p if p.startswith("`") else fn(p) for p in re.split(r"(`[^`\n]*`)", l))
    return "".join(b if b.lstrip(" \t").startswith("```") else fn(b) if blocks else "\n".join(map(line, b.split("\n")))
                   for b in re.split(r"(^[ \t]*```.*?^[ \t]*```)", text, flags=re.S | re.M))


def html_attrs(tag):
    """An HTML tag's attributes, lowercase names: quoted either way or not at all, in any order."""
    return {k.lower(): v[1:-1] if v[:1] in "\"'" else v
            for k, v in re.findall(r"""([\w-]+)\s*=\s*("[^"]*"|'[^']*'|[^\s"'>]+)""", tag)}


def literal_placeholders(text):
    """A <placeholder> in prose ("NordVPN <country>") is an HTML tag to a Markdown reader: GitHub
    hides it, and Qt's drops all the text after it. Outside code, one that isn't an HTML tag (nor
    an <https://…> link) is shown as written."""
    return in_prose(text, lambda p: re.sub(
        r"<(/?)([A-Za-z][\w.-]*)([^<>]*)>",
        lambda m: m[0] if m[2].lower() in HTML_TAGS or ":" in m[0] else f"&lt;{m[1]}{m[2]}{m[3]}&gt;", p))


def readme_browser(text, comp):
    """A README (Markdown) as the window shows it: links absolute (readme_links), pictures from the
    local copy and fitted, a 📋 after each link, the window's font and link colour."""
    view = QTextBrowser()
    view.setOpenLinks(False)
    view.anchorClicked.connect(lambda u: follow_link(u.toString()) if u.scheme() else to_heading(view, u.fragment()))
    view.zoomer = _Zoom(view)                       # (Ctrl+wheel)
    view.viewport().installEventFilter(view.zoomer)
    view.document().setDefaultStyleSheet(
        "a { color: #7fb2e5; } code { background: #1c232a; } pre { background: #1c232a; }")
    view.setMarkdown(readme_links(plain_markdown(text), comp))     # (no HTML it can't place: plain_markdown)
    # (toHtml() pins the font and link colour it saw; dropping them keeps the window's style.)
    html_ = re.sub(r'<body style="[^"]*">', "<body>", fit_images(with_copy(view.toHtml())), count=1)
    view.setHtml(html_.replace("color:#0000ff;", "color:#7fb2e5;"))
    return view


def to_heading(view, anchor):
    """A README's link to one of its own headings (#build-from-source, named as GitHub names
    them): scroll there, in the README, or in the page around it when the README is shown whole
    (full_height). (Qt's Markdown reader gives headings no anchors of their own.)"""
    block = view.document().begin()
    while block.isValid():
        if block.blockFormat().headingLevel() and \
                re.sub(r"[^\w\- ]", "", block.text().strip().lower()).replace(" ", "-") == anchor:
            top = int(view.document().documentLayout().blockBoundingRect(block).top())
            area = page_area(view)
            if getattr(view, "whole", False) and area is not None:
                area.verticalScrollBar().setValue(view.viewport().mapTo(area.widget(), QPoint(0, top)).y())
            else:
                view.verticalScrollBar().setValue(top)
            return
        block = block.next()


def page_area(view):
    """The scroll area a widget is on (a README shown whole: the page around it), or None."""
    area = view.parentWidget()
    while area is not None and not isinstance(area, QScrollArea):
        area = area.parentWidget()
    return area


class _Zoom(QObject):
    """(readme_browser's: Ctrl+wheel over a README makes its text larger or smaller: zoom.)"""
    def __init__(self, view):
        super().__init__(view)
        self.view = view

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.Wheel and ev.modifiers() & Qt.KeyboardModifier.ControlModifier \
                and not sip.isdeleted(self.view):
            zoom(self.view, ev.angleDelta().y())
            return True
        return False


def zoom(view, delta):
    """A README's text larger (delta > 0) or smaller by 2 px a wheel notch (120), from 10 to 40 px.
    Its own style sheet does it: QTextEdit's zoom changes the font the window's style sheet sets
    (14 px), so it changed nothing. A README shown whole is fitted to its new height."""
    view.zoom_delta = getattr(view, "zoom_delta", 0) + delta
    notches = int(view.zoom_delta / 120)            # (a touchpad's small steps add up to one)
    if not notches:
        return
    view.zoom_delta -= notches * 120
    view.setStyleSheet(f"font-size: {max(10, min(40, QFontInfo(view.font()).pixelSize() + 2 * notches))}px;")
    if getattr(view, "fit", None):
        view.fit()


_Step = QAbstractSlider.SliderAction
PAGE_KEYS = {Qt.Key.Key_Up: _Step.SliderSingleStepSub, Qt.Key.Key_Down: _Step.SliderSingleStepAdd,
             Qt.Key.Key_PageUp: _Step.SliderPageStepSub, Qt.Key.Key_PageDown: _Step.SliderPageStepAdd,
             Qt.Key.Key_Space: _Step.SliderPageStepAdd,
             Qt.Key.Key_Home: _Step.SliderToMinimum, Qt.Key.Key_End: _Step.SliderToMaximum}


class _FitHeight(QObject):
    """(full_height's: a new width, a new height; the wheel and the keys that scroll, over it or
    in it, scroll the page around it, and a link Tab moves to is scrolled into view there. Ctrl+
    wheel still zooms the README (_Zoom), and a sideways scroll moves a wide picture or code line.)"""
    def __init__(self, view):
        super().__init__(view)
        self.view = view

    def eventFilter(self, obj, ev):
        if sip.isdeleted(self.view):                # (the viewport's last events, as it goes)
            return False
        if ev.type() == QEvent.Type.Resize and obj is self.view:
            QTimer.singleShot(0, self.view.fit)
            return False
        area = page_area(self.view)
        if area is None:
            return False
        if ev.type() == QEvent.Type.Wheel:
            d = ev.angleDelta()
            if ev.modifiers() & Qt.KeyboardModifier.ControlModifier or abs(d.x()) > abs(d.y()):
                return False
            QApplication.sendEvent(area.verticalScrollBar(), ev)
            return True
        if ev.type() == QEvent.Type.KeyPress and obj is self.view:
            if ev.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                QTimer.singleShot(0, lambda: self.show_cursor(area))
            elif ev.key() in PAGE_KEYS and not ev.modifiers() & ~(
                    Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.KeypadModifier):
                area.verticalScrollBar().triggerAction(PAGE_KEYS[ev.key()])
                return True
        return False

    def show_cursor(self, area):
        if sip.isdeleted(self.view) or sip.isdeleted(area):
            return
        at = self.view.cursorRect()
        p = self.view.viewport().mapTo(area.widget(), at.center())
        area.ensureVisible(p.x(), p.y(), 20, at.height() + 20)


def full_height(view):
    """A QTextBrowser shown whole, as tall as its text at its width, with no vertical scroll bar of
    its own: the page it's on scrolls instead (a wheel, laser scroll or key over it reaches the
    page). Its own horizontal bar shows when something is wider (a picture, a line of code)."""
    view.whole = True
    view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def fit(*_args):
        if sip.isdeleted(view):
            return
        doc = view.document()
        width = view.viewport().width()
        if doc.textWidth() != width:            # (setting it lays all of the README out again)
            doc.setTextWidth(width)
        wide = doc.size().width() > width + 1
        height = int(doc.size().height()) + 2 * view.frameWidth() + 4 + (
            view.horizontalScrollBar().sizeHint().height() if wide else 0)
        if view.height() != height:
            view.setFixedHeight(height)
    view.fit = fit
    view.document().documentLayout().documentSizeChanged.connect(fit)
    view.fitter = _FitHeight(view)
    view.installEventFilter(view.fitter)
    view.viewport().installEventFilter(view.fitter)
    QTimer.singleShot(0, fit)
    return view


def fit_images(text, width=860):
    """Rich text whose local pictures wider than width are shown at that width."""
    def fit(m):
        img = QImage(urllib.parse.unquote(m.group(1)[7:]))
        return m.group(0) if img.isNull() or img.width() <= width else f'<img src="{m.group(1)}" width="{width}" />'
    return re.sub(r'<img src="(file://[^"]+)"[^>]*>', fit, text)


COPY_LINK = re.compile(r"""(<a\b[^>]*?\bhref=(["'])((?:https?|file):[^"']+)\2[^>]*>.*?</a>)""", re.S)


def with_copy(text):
    """Rich text with a 📋 after each web or file link, which copies the link instead of opening it."""
    title = html.escape(_("Copy the link"), quote=True)
    return COPY_LINK.sub(lambda m: f"{m.group(1)}&nbsp;<a href={m.group(2)}copy:{m.group(3)}{m.group(2)} "
                         f"style='text-decoration:none' title='{title}'>📋</a>", text)


def md_text(text):
    """A manifest's text as rich text: escaped, with its [Markdown links](https://…) made links,
    **bold** bold and `code` as code."""
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"<a style='color:#7fb2e5' href='\2'>\1</a>",
                  html.escape(text, quote=False))
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", text)


def follow_link(url):
    """What clicking a link does: copy:<url> puts the link on the clipboard; a web link or a file
    goes to its default app in whichever session that's running (lib/browser.py); anything else
    opens the usual way."""
    if url.startswith("copy:"):
        QApplication.clipboard().setText(url[5:])
        link_tip.show(_("Link copied"))
    elif url.startswith(("https:", "http:")) and (r := opened(browser.launch, url)):
        note, proc, handoff = r
        link_tip.show(note)          # (it may have opened in the other session)
        if getattr(proc, "warning", ""):                # (the default browser isn't one: what to set)
            window_say(proc.warning)
        if handoff:                                    # the browser runs there already: did it answer?
            QTimer.singleShot(8000, lambda: browser.still_stuck(proc, url) and stuck_link(url))
    elif url.startswith("file:") and (note := opened(browser.open_path, url)):
        link_tip.show(note)
    else:
        QDesktopServices.openUrl(QUrl(url))


def opened(how, url):
    """how(url) (lib/browser.py's), or None when it couldn't, or tripped over something of this
    machine's (a desktop entry it can't read, say): then the link opens the usual way instead of
    not at all. (Noted in its log, which the diagnostics report has.)"""
    try:
        return how(url)
    except Exception as e:
        browser.log(f"couldn't open {url!r}: {type(e).__name__}: {e}")
        return None


def stuck_link(url):
    """The browser in the other session didn't take the link (it can stall while desktop mode
    isn't shown): the link goes on the clipboard instead, and the window says so."""
    QApplication.clipboard().setText(url)
    window_say(_("The browser didn't answer, so the link is on the clipboard: paste it into the browser."))


def window_say(text):
    """A message in the window's bottom bar (Window.say), from code outside the window."""
    for w in QApplication.topLevelWidgets():
        if hasattr(w, "say"):
            w.say(text)
            return
    link_tip.show(_("The browser didn't answer: the link is on the clipboard."))


def link_label(label):
    """A QLabel whose links (shown with with_copy) open or copy through follow_link."""
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setOpenExternalLinks(False)
    label.linkActivated.connect(follow_link)
    return label


def row_icon(cid):
    """The row's icon, from its manifest's icon: an installed Flatpak's own icon, then a picture
    in the tweak's folder, then a Breeze theme icon."""
    c = component(cid) or {"icon": {}, "dir": REPO}
    icon = c["icon"]
    if icon.get("flatpak"):
        hits = sorted(FLATPAK_ICONS.glob(f"*/apps/{icon['flatpak']}.*"),
                      key=lambda p: (p.suffix == ".svg", p.parent.parent.name))
        if hits:
            return QIcon(str(hits[-1]))
    if icon.get("file") and (c["dir"] / icon["file"]).is_file():
        return QIcon(str(c["dir"] / icon["file"]))
    hits = sorted(BREEZE.glob(f"*/*/{icon.get('theme', 'application-x-executable')}.svg"))
    return QIcon(str(hits[-1])) if hits else QIcon()



def version_tuple(v):
    """Sort key for an app's version, in whatever form its project writes it (1.140.06880,
    v2.3, 0.2.0+138a59b): its numbers, then a pre-release (1.2.0-rc1, 1.2.0~beta2) below the
    final version. (Frame Tweaks' own tags: release_key.)"""
    main, sep, pre = (re.split(r"([-~])", (v or "").split("+")[0], maxsplit=1) + ["", ""])[:3]
    nums = lambda s: tuple(int(n) for n in re.findall(r"\d+", s))
    return nums(main), 0 if sep else 1, nums(pre)


def latest_release(url):
    """Newest release tag from GitHub's API, or None (offline, rate limit, ...)."""
    try:
        with urllib.request.urlopen(urllib.request.Request(
                url, headers={"Accept": "application/vnd.github+json"}), timeout=8) as r:
            return json.load(r).get("tag_name")
    except Exception:
        return None


def status_text(code_text):
    if code_text is None:
        return _("checking…"), "checking"
    code, text = code_text
    if code not in (0, 1, 2, RESTART, UNLOAD, UNAVAILABLE):
        # (status.sh ended some other way, a command missing under set -e, say: installed, as
        # ./install.sh counts it, and worth a look)
        return "! " + _("status check failed (exit {code})").format(code=code), "warn"
    return ({0: "✔ " + text, 2: "! " + text, RESTART: "⟳ " + text, UNLOAD: "⟳ " + text,
             UNAVAILABLE: "· " + text}.get(code, "· " + _("not installed")),
            {0: "ok", 2: "warn", RESTART: "warn", UNLOAD: "warn"}.get(code, "missing"))


class CategoryHeader(QWidget):
    """▾/▸ CATEGORY (n): click to collapse or expand (remembered); Hide/Unhide on the right."""

    def __init__(self, window, category, count, collapsed, hidden, key=None):
        super().__init__()
        key = key or category                           # (the English name: what's remembered)
        self.setObjectName("cathead")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 4, 0)
        arrow = "▶" if collapsed else "▼"
        toggle = QPushButton(f"{arrow}  {category.upper().replace('&', '&&')}  ({count})"
                             + ("   · " + _("hidden") if hidden else ""))
        toggle.setObjectName("cattoggle")
        toggle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        toggle.setToolTip(_("Expand") if collapsed else _("Collapse"))
        toggle.clicked.connect(lambda: window.toggle_collapsed(key))
        lay.addWidget(toggle, 1)
        hide = QPushButton(_("Unhide category") if hidden else _("Hide category"))
        hide.setObjectName("cathide")
        hide.setToolTip(_("Show this category again") if hidden else
                        _("Hide the whole category from the list (doesn't remove anything)"))
        hide.clicked.connect(lambda: window.toggle_category_hidden(key))
        lay.addWidget(hide)


class Row(QWidget):
    """Clicking anywhere on the row (but its checkbox, buttons or link) opens the details."""

    def __init__(self, window, comp):
        super().__init__()
        self.window, self.comp = window, comp
        self.setObjectName("row")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.window.show_details(self.comp)


# Controller buttons in VR (B back, Y to the top, A ticks the row, the left D-pad through the
# rows; vrbuttons.py): off until they work reliably (docs/roadmap.md). Off, the window never
# claims the buttons; its haptic ticks still work.
CONTROLLER_BUTTONS = False

# The list's last row, under every group: not a tweak (nothing to install), the ways to help
# (docs/contribute.md). Built here, not in a pack, so install.sh, status and the README's
# tables never see it.
CONTRIBUTE = {"id": "_contribute", "icon": "system-users"}


class ContributeRow(Row):
    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.window.show_contribute()


class ReadmePage(QWidget):
    """Frame Tweaks' own README.md, as a page (Back returns to the list)."""

    def __init__(self, window, path=None, heading=None):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        back = QPushButton(_("← Back"))
        back.clicked.connect(window.go_back)
        head.addWidget(back)
        title = QLabel(heading or _("About Frame Tweaks"))
        title.setObjectName("title")
        head.addWidget(title, 1)
        lay.addLayout(head)
        try:
            text = (path or REPO / "README.md").read_text()
        except OSError:
            text = "_" + _("No README.") + "_"
        lay.addWidget(readme_browser(text, {"official": True, "id": None, "dir": REPO}), 1)


class Details(QWidget):
    """A page inside the main window (not a dialog: in VR each new window opens in the dashboard)."""

    def __init__(self, window, comp, state):
        super().__init__()
        self.window, self.comp = window, comp
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        back = QPushButton(_("← Back"))
        back.clicked.connect(window.leave_details)
        head.addWidget(back)
        icon = QLabel()
        icon.setPixmap(row_icon(comp["id"]).pixmap(56, 56))
        head.addWidget(icon)
        title = QLabel(f"{html.escape(comp['title'], quote=False)}  <span style='color:#6b7783;font-size:14px'>"
                       f"{html.escape(comp['category'])}</span>")
        title.setObjectName("title")
        head.addWidget(title, 1)
        lay.addLayout(head)

        issue = KNOWN_ISSUES.get(comp["id"])
        self.issue_label = None
        if issue:
            self.issue_label = QLabel()
            self.issue_label.setObjectName("issue")
            self.issue_label.setWordWrap(True)
            link_label(self.issue_label)
            self.show_issue(window.latest.get(comp["id"], "checking"))

        rel, url = comp["source"].split("|", 1) if "|" in comp["source"] else ("", "")
        rel = _(rel) if rel else rel                        # (uses, from, …: dev/i18n.py collects them)
        facts = [(_("What it is"), md_text(comp["what"])),
                 (_("Why it's included"), md_text(comp["why"])),
                 (_("Made by"), md_text(comp["author"]))]
        if comp["experimental"]:
            facts.append((_("🧪 Experimental"), f"<span style='color:#e0b33a'>{md_text(comp['experimental'])}</span>"))
        why_not = sft.not_needed([comp]).get(comp["id"])
        if why_not is not None:
            facts.append((_("Not needed"), "<span style='color:#e0b33a'>" + html.escape(
                _("This Frame doesn't need it: %s") % why_not, quote=False) + "</span>"))
        if sft.sudo_note(comp):
            facts.append((_("Asks for sudo"), "<span style='color:#e0b33a'>" + html.escape(
                _("Installing it asks for your sudo (admin) password in its terminal: %s") % sft.sudo_note(comp),
                quote=False) + "</span>"))
        if comp["link"]:
            readme = comp["link"].get("readme") or url
            facts.append((_("🔗 Linked"), "<span style='color:#e0b33a'>" + html.escape(_(
                "Installed, updated and uninstalled with the project's own commands, as its README gives them; "
                "Frame Tweaks runs them, but doesn't pin, check or change what they install."), quote=False) + "</span>"
                + (f"<br><a style='color:#7fb2e5' href='{html.escape(readme)}'>" + _("Its README") + " ↗</a>" if readme else "")))
        if url:
            facts.append((_("Source"), f"{html.escape(rel)} <a style='color:#7fb2e5' href='{url}'>{url}</a>"))
        if comp["deps"]:
            facts.append((_("Needs"), _("{tweaks} (installed automatically)").format(tweaks=", ".join(comp["deps"]))))
        self.status_at = len(facts)                         # (show_state puts a new one there)
        facts.append((_("Status"), ""))
        if comp["official"]:
            facts.append((_("Pack"), html.escape(_(comp["pack"]))))
            facts.append((_("Documentation"), f"<a style='color:#7fb2e5' href='{GITHUB}/packs/{comp['pack_dir'].name}/{comp['id']}'>"
                          + _("{file} on GitHub").format(file=f"{comp['id']}/README.md") + "</a>"))
        else:
            facts.append((_("From"), "<span style='color:#e0b33a'>"
                          + _("the pack {pack}, not part of Frame Tweaks").format(pack=html.escape(comp["pack"]))
                          + "</span>" + (" " + _("(used instead of {other}'s)").format(other=html.escape(comp["replaced"]))
                                         if comp["replaced"] else "")
                          + f"<br><a style='color:#7fb2e5' href='{comp['readme'].as_uri()}'>{html.escape(str(comp['dir']))}</a>"))
        self.facts, self.summary = facts, link_label(QLabel())
        self.summary.setWordWrap(True)
        self.show_state(state)

        try:
            text = manifest.front_matter(comp["readme"].read_text())[1]
        except (OSError, manifest.ManifestError):
            text = "_" + _("No README.") + "_"
        # (Its opening, what it is and why, is in the table above already.)
        text = re.sub(r"<!-- generated:intro .*?<!-- /generated:intro -->\n*", "", text, flags=re.S)
        # Everything below the header scrolls as one page: a long table of facts used to leave the
        # README a narrow strip to scroll in. (Back and the title stay where they are.)
        body = QWidget()
        rows = QVBoxLayout(body)
        rows.setContentsMargins(0, 0, 0, 0)
        if self.issue_label is not None:
            rows.addWidget(self.issue_label)
        rows.addWidget(self.summary)
        self.readme = full_height(readme_browser(text, comp))
        rows.addWidget(self.readme)
        rows.addStretch(1)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setWidget(body)
        lay.addWidget(self.scroll, 1)

    def show_state(self, state):
        """The table of facts, with this status ((code, text) as the window keeps it; None while
        it's being checked): the window gives it each new one, as it does the tweak's row."""
        text, kind = status_text(state)
        colour = {"ok": "#5cc77a", "warn": "#e0b33a"}.get(kind, "#9aa6b2")
        self.facts[self.status_at] = (_("Status"), f"<span style='color:{colour}'>{html.escape(text)}</span>")
        self.summary.setText(with_copy("<table cellspacing=6>" + "".join(
            f"<tr><td style='color:#6b7783;padding-right:12px' valign=top><b>{k}</b></td><td>{v}</td></tr>"
            for k, v in self.facts) + "</table>"))

    def show_issue(self, latest):
        """latest: newest upstream tag, "checking", or None when it couldn't be fetched."""
        issue = KNOWN_ISSUES[self.comp["id"]]
        text = "<b>" + _("⚠ Known issue.") + "</b> " + html.escape(issue["long"], quote=False)
        rel = issue["latest"].replace("api.github.com/repos", "github.com")
        link = f"<a style='color:#7fb2e5' href='{rel}'>"
        if latest == "checking":
            text += "<br><span style='color:#9aa6b2'>" + _("Checking for a newer release…") + "</span>"
        elif latest is None:
            text += ("<br><span style='color:#9aa6b2'>"
                     + _("Couldn't check for a newer release; see {link}its releases{end}.").format(link=link, end="</a>")
                     + "</span>")
        elif version_tuple(latest) > version_tuple(issue["version"]):
            text += "<br>" + _("<b>Version {version} is now available</b>, so this may be resolved: "
                               "see {link}its release notes{end}, then reinstall to update.").format(
                version=html.escape(latest), link=link, end="</a>")
        else:
            text += ("<br><span style='color:#9aa6b2'>"
                     + _("{version} is still the latest release.").format(version=html.escape(latest)) + "</span>")
        self.issue_label.setText(with_copy(text))


def action_command(a):
    """A settings action's command (a: one of its manifest's settings: actions)."""
    return ["bash", str(a["dir"] / a["script"]), *a.get("args", [])]


def running_action(window):
    """The settings action running in the background, or None (one at a time: SettingsSection.act)."""
    return next((p for p in window.findChildren(QProcess, "action")
                 if p.state() != QProcess.ProcessState.NotRunning), None)


def action_said(proc):
    """How a settings action that ended went: its last line of output, or "Didn't work: …" with it."""
    lines = [re.sub(r"\x1b\[[0-9;]*m", "", l).strip() for l in
             bytes(proc.readAll()).decode(errors="replace").splitlines()]
    lines = [l for l in lines if l and "#" not in l[:3]]          # (not curl's progress bar)
    ok = proc.exitStatus() == QProcess.ExitStatus.NormalExit and proc.exitCode() == 0
    last = lines[-1] if lines else _("Done.")
    return last if ok else _("Didn't work: %s") % last


class SettingsSection(QWidget):
    """One tweak's settings (lib/sft.py SETTINGS: the same choices as ./install.sh settings and the
    gears in VR): its options, Reset, and its action buttons. notice: where it reports."""

    def __init__(self, cid, notice):
        super().__init__()
        self.cid, self.spec, self.notice = cid, sft.SETTINGS[cid], notice
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        about = QLabel(self.spec["about"])
        about.setObjectName("desc")
        about.setWordWrap(True)
        lay.addWidget(about)
        self.conf = sft.read_settings(cid)
        self.buttons, self.checks = {}, {}
        for key, label, choices, _default in self.spec["options"]:
            if key in self.spec["checkboxes"]:          # on / off: one tick box
                box = QCheckBox(label)
                box.setStyleSheet("font-weight: 600; margin-top: 14px;")
                box.setChecked(self.conf.get(key) == choices[0][1])
                box.clicked.connect(lambda on, k=key, c=choices: self.choose(k, c[0][1] if on else c[1][1]))
                lay.addWidget(box)
                self.checks[key] = (box, choices[0][1])
                continue
            lab = QLabel(label)
            lab.setStyleSheet("font-weight: 600; margin-top: 14px;")
            lay.addWidget(lab)
            grid = QGridLayout()                     # (wraps: a long list of choices fits the page)
            per_row = 7 if all(len(t) <= 8 for t, _value in choices) else 4
            swatches = key in self.spec["swatches"]
            if swatches:                             # circles of colour, as the gear's panel in VR
                per_row = 12
            for n, (text, value) in enumerate(choices):
                b = QPushButton(text)
                b.setCheckable(True)
                b.setChecked(self.conf.get(key) == value)
                bold = QFont(b.font())
                bold.setBold(True)                   # (wide enough for the chosen one's bold text,
                bold.setPixelSize(15)                # at STYLE's 14 px, measured before it applies)
                b.setMinimumWidth(max(70, QFontMetrics(bold).horizontalAdvance(text) + 36))
                b.setStyleSheet("QPushButton:checked { background: #355b7a; font-weight: 600; }")
                if swatches and isinstance(value, (int, float)):
                    hue = round(value * 360)
                    b.setText("")
                    b.setToolTip(text)
                    b.setAccessibleName(text)
                    b.setFixedSize(44, 44)
                    b.setMinimumWidth(44)
                    b.setStyleSheet(f"QPushButton {{ background: hsl({hue}, 60%, 55%); border-radius: 22px;"
                                    f" border: 2px solid rgba(255, 255, 255, 64); padding: 0; }}"
                                    f" QPushButton:checked {{ border: 4px solid white; }}")
                b.clicked.connect(lambda _=False, k=key, v=value: self.choose(k, v))
                grid.addWidget(b, n // per_row, n % per_row)
                self.buttons[(key, text)] = (b, value)
            grid.setColumnStretch(per_row, 1)
            lay.addLayout(grid)
        reset = QPushButton(_("Reset to defaults"))
        reset.clicked.connect(self.reset)
        lay.addWidget(reset)
        self.actions = []
        for a in self.spec["actions"]:
            b = QPushButton()
            b.clicked.connect(lambda _=False, a=a: self.act(a))
            note = QLabel(a.get("about", ""))
            note.setObjectName("desc")
            note.setWordWrap(True)
            row = QHBoxLayout()
            row.addWidget(b)
            row.addWidget(note, 1)
            lay.addSpacing(10)
            lay.addLayout(row)
            self.actions.append((a, b, note))
        self.commands = {"\0".join(action_command(a)) for a in self.spec["actions"]}
        self.show_actions()

    def show_actions(self):
        for a, b, note in self.actions:
            value = sft.raw_setting(self.cid, a["when"]) if a.get("when") else ""
            b.setText(re.sub(r"\{(\w+)\}", lambda m: sft.raw_setting(self.cid, m[1]), a["label"]))
            b.setVisible(not a.get("when") or bool(value))
            note.setVisible(b.isVisibleTo(self) or not a.get("when"))

    def act(self, a):
        """Run the action's script in the background (a download can take a while); its last line
        of output says how it went. It's the window's process (going Back mustn't stop it), so
        one at a time: a page opened again meanwhile doesn't start a second, but says how the one
        running goes."""
        cmd = action_command(a)
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run:", " ".join(cmd))
            return
        running = running_action(self.window())
        if running is not None and running.property("command") != "\0".join(cmd):
            self.notice.setText(_("Another action is still running: try again once it's done."))
            return
        if running is None:
            running = QProcess(self.window())
            running.setObjectName("action")
            running.setProperty("command", "\0".join(cmd))       # (what a page opened again looks for)
            running.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            running.finished.connect(lambda *_args, p=running: (p.setProperty("said", action_said(p)), p.deleteLater()))
            running.start(cmd[0], cmd[1:])
        self.follow(running)

    def follow(self, proc):
        """Working… on this section's page until proc, its action, ends (started here, or from a
        page closed since); then how it went (action_said)."""
        self.notice.setText(_("Working… (a download can take a minute)"))
        for _a, b, _note in self.actions:
            b.setEnabled(False)

        def done(*_args):
            if sip.isdeleted(self):             # (its page was closed meanwhile)
                return
            self.notice.setText(proc.property("said") or _("Done."))
            for _a, b, _note in self.actions:
                b.setEnabled(True)
            self.show_actions()
        proc.finished.connect(done)

    def show_choices(self):
        for (key, _text), (b, value) in self.buttons.items():
            b.setChecked(self.conf.get(key) == value)
        for key, (box, on) in self.checks.items():
            box.setChecked(self.conf.get(key) == on)

    def choose(self, key, value):
        self.conf[key] = value
        self.show_choices()
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would save:", self.cid, json.dumps({key: value}))
            return
        sft.write_settings(self.cid, {key: value})
        self.notice.setText(_("Saved.") + " " + self.spec["note"])

    def reset(self):
        self.conf = sft.defaults(self.cid)
        self.show_choices()
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would reset:", self.cid)
            return
        sft.write_settings(self.cid, {}, reset=True)
        self.notice.setText(_("Back to the defaults.") + " " + self.spec["note"])


class SettingsPage(QWidget):
    """A tweak's settings page: its own section, then those of the tweaks its settings include
    (Screen snip + Narrate shows the Speech engine's: same files, same choices)."""

    def __init__(self, window, cid):
        super().__init__()
        self.cid = cid
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        back = QPushButton(_("← Back"))
        back.clicked.connect(window.go_back)
        head.addWidget(back)
        title = QLabel(next((c["title"] for c in components() if c["id"] == cid), cid))
        title.setObjectName("title")
        head.addWidget(title, 1)
        lay.addLayout(head)
        self.notice = QLabel()
        self.notice.setObjectName("notice")
        self.notice.setWordWrap(True)
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, 8, 0)
        self.sections = [SettingsSection(cid, self.notice)]
        col.addWidget(self.sections[0])
        for other in sft.SETTINGS[cid]["include"]:
            if other not in sft.SETTINGS:
                continue
            head2 = QLabel(next((c["title"] for c in components() if c["id"] == other), other))
            head2.setObjectName("title")
            head2.setStyleSheet("margin-top: 22px;")
            col.addWidget(head2)
            self.sections.append(SettingsSection(other, self.notice))
            col.addWidget(self.sections[-1])
        col.addStretch(1)
        running = running_action(window)         # (one of its actions, started from this page closed since)
        for section in self.sections:
            if running is not None and running.property("command") in section.commands:
                section.follow(running)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(body)
        lay.addWidget(scroll, 1)
        lay.addWidget(self.notice)


SETTINGS_PAGES = {cid: (lambda w, c=cid: SettingsPage(w, c)) for cid in sft.SETTINGS}   # the row's button opens these
# A row whose button opens a page of its own instead (label, page): the wallet's apps.
PAGES = {"wallet": (N_("🔑 Wallet apps"), WalletApps)}         # (label: translated where it's shown)


class Window(QWidget):
    pack_job = None         # a pack being added or updated from a link, (future, done, saying): finish_pack_job

    def __init__(self):
        super().__init__()
        # The build this window runs: the checkout can change under it (an update in a terminal,
        # a git pull), and until it restarts, it's this one's code that runs.
        self.build_at_start = version = sft.build_version()
        self.setWindowTitle(f"Frame Tweaks {version}")
        icon = ICONS / "frame-tweaks.png"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self.setStyleSheet(STYLE)
        self.resize(1000, 760)
        self.rows = components()
        self.state = {}               # id -> (code, text); missing = still checking
        self.boxes, self.status_labels, self.wanted, self.run_buttons = {}, {}, {}, {}
        self.again_buttons = {}
        self.pool = ThreadPoolExecutor(max_workers=4)
        self.futures = {}
        self.latest = {}              # id -> newest upstream tag (known-issue rows), None if unknown
        self.latest_futures = {}
        self.check_known_issues()
        self.details = None
        self.updates, self.update_futures = {}, {}     # id -> (installed, latest) when newer
        self.prefs = window_prefs()
        try:                                         # (what's kept under a tweak's former id: formerly:)
            sft.apply_formerly()
        except OSError:
            pass
        self.self_update = self.pool.submit(self_update_check) if self.prefs["update_check"] else None
        # packs added from a link whose source has a newer version (with Frame Tweaks' own check)
        self.pack_updates = set()
        self.pack_check = self.pool.submit(sft.packs_with_updates) if self.prefs["update_check"] else None

        self.release_at_start = current_release()
        self.update_state, self.update_newest = "check", None
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(20, 16, 20, 16)
        self.stack = None
        self.build_ui()
        # Results of background jobs (status checks, update checks): looked for 10x a second while
        # any is running, once a second otherwise (collect sets which).
        self.collector = QTimer(self, interval=100, timeout=self.collect)
        self.collector.start()
        QTimer(self, interval=int(i18n.CHECK_EVERY * 1000), timeout=self.check_language).start()
        self.vr_buttons = None
        if os.environ.get("DISPLAY") == ":0":          # opened in VR: haptic ticks (and the controller buttons, when on)
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from vrbuttons import VRButtons
            self.vr_buttons = VRButtons({"back": self.go_back, "home": self.go_home,
                                         "toggle": self.toggle_pointed_row,
                                         "up": lambda: self.move_focus(-1),
                                         "down": lambda: self.move_focus(+1)}
                                        if CONTROLLER_BUTTONS else {})
            if self.vr_buttons.started:
                QApplication.instance().installEventFilter(self)    # haptics: see eventFilter
            if self.vr_buttons.ok:
                self._laser = (None, 0.0)
                # 30x a second while the laser is on the window (or A/B/Y are claimed); 4x a second
                # otherwise, only to notice it arriving.
                self.vr_timer = QTimer(self, interval=33, timeout=self.poll_vr_buttons)
                self.vr_timer.start()
        self.refresh()

    def build_ui(self):
        """The window's widgets (again after a change of language: retranslate)."""
        top = QHBoxLayout()
        title = QLabel(f"Frame Tweaks <span style='color:#6b7783;font-size:14px'>{self.running_build()}</span>")
        title.setObjectName("title")
        top.addWidget(title)
        top.addStretch(1)
        self.self_update_label = QLabel()
        self.self_update_label.setObjectName("notice")
        self.self_update_label.linkActivated.connect(lambda _: self.run_update(None))
        top.addWidget(self.self_update_label)
        self.pack_update_label = QLabel()
        self.pack_update_label.setObjectName("notice")
        self.pack_update_label.linkActivated.connect(lambda _: self.show_packs())
        top.addWidget(self.pack_update_label)
        self.show_pack_updates()
        prefs = QPushButton("⚙")
        prefs.setToolTip(_("Preferences: the language, and how this window behaves"))
        prefs.clicked.connect(self.show_prefs)
        top.addWidget(prefs)
        self.show_hidden = QPushButton()
        self.show_hidden.setCheckable(True)
        self.show_hidden.toggled.connect(self.rebuild)
        top.addWidget(self.show_hidden)
        packs = QPushButton(_("🧩 Packs"))
        packs.setToolTip(_("Where the tweaks come from; add other people's (docs/mods.md)"))
        packs.clicked.connect(self.show_packs)
        top.addWidget(packs)
        refresh = QPushButton(_("Refresh"))
        refresh.clicked.connect(self.refresh)
        top.addWidget(refresh)

        self.list = QWidget()
        self.grid = QVBoxLayout(self.list)
        self.grid.setSpacing(8)
        scroll = QScrollArea()
        self.scroll = scroll
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.list)

        bottom = QHBoxLayout()
        # One line on the left: how the list works, or for a few seconds a message (say()).
        self.hint_text = _("Tick to install, untick to remove, then Apply changes. "
                           "Click a row for details, a category to fold it.")
        self.notice = QLabel(self.hint_text)
        self.notice.setObjectName("desc")
        self.notice.setWordWrap(True)
        bottom.addWidget(self.notice, 1)
        self.update_button = QPushButton()
        self.update_button.clicked.connect(self.update_clicked)
        bottom.addWidget(self.update_button)
        self.set_update_state(self.update_state, self.update_newest)
        about = QPushButton(_("📖 README"))
        about.setToolTip(_("What Frame Tweaks is, how to install, update and remove it, common issues"))
        about.clicked.connect(self.show_readme)
        bottom.addWidget(about)
        diag = QPushButton(_("🐞 Report a problem"))
        diag.setToolTip(_("Save a diagnostics report (user names and paths removed) and open the bug form"))
        diag.clicked.connect(self.show_report)
        bottom.addWidget(diag)
        apply_ = QPushButton(_("Apply changes"))
        apply_.setObjectName("apply")
        apply_.clicked.connect(self.apply)
        self.apply_button = apply_
        close = QPushButton(_("Close"))
        close.clicked.connect(self.close)
        bottom.addWidget(apply_)
        bottom.addWidget(close)

        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(top)
        lay.addWidget(scroll, 1)
        lay.addLayout(bottom)
        self.row_widgets, self.focus_index = [], -1
        old = self.stack
        self.stack = QStackedWidget()
        self.stack.addWidget(page)
        self.confirm_page, self.confirm_text, self.confirm_yes = self.make_confirm_page()
        self.stack.addWidget(self.confirm_page)
        self.error_page, self.error_text = self.make_error_page()
        self.stack.addWidget(self.error_page)
        self.outer.addWidget(self.stack)
        if old is not None:
            self.outer.removeWidget(old)
            old.deleteLater()

    def check_language(self):
        """Every 5 s: has the keyboard's language changed (lib/i18n.py)? Then the window's text
        follows, once you're back on the list (an open page isn't pulled away from you)."""
        if self.stack.currentIndex() == 0 and self.details is None and i18n.refresh():
            pass_language()
            self.retranslate()

    def retranslate(self):
        global KNOWN_ISSUES
        showing = self.show_hidden.isChecked()
        sft.load(refresh=True)
        sft.SETTINGS = sft.settings_specs()
        KNOWN_ISSUES = {c["id"]: c["known_issue"] for c in components() if c["known_issue"]}
        self.rows = components()
        sft.not_needed(self.rows, refresh=True)          # (why one isn't needed, as its needed.sh says: in the new language)
        self.build_ui()
        self.show_hidden.blockSignals(True)
        self.show_hidden.setChecked(showing)
        self.show_hidden.blockSignals(False)
        if self.update_newest and self.update_state == "update":
            self.show_newest(self.update_newest)
        self.refresh()                                   # (statuses again, in the new language)

    # ---- hidden rows: yours, plus defaults you haven't unhidden ----------------
    def hidden(self):
        return sft.hidden(self.rows)

    def toggle_collapsed(self, category):
        """category: its English name (category_en), whatever the window's language."""
        collapsed = sft.read_categories(COLLAPSED, self.rows)
        collapsed ^= {category}
        write_set(COLLAPSED, collapsed)
        self.rebuild()

    def toggle_category_hidden(self, category):
        sft.set_category_hidden(category, category not in sft.read_categories(HIDDEN_CATS, self.rows))
        self.rebuild()

    def toggle_hidden(self, cid):
        sft.set_hidden(cid, cid not in self.hidden())
        self.rebuild()

    # ---- status, in the background ------------------------------------------------
    def refresh(self):
        for fut in self.futures.values():            # (the last round's still waiting for a worker: not run as well)
            fut.cancel()
        self.state = {}
        self.futures = {c["id"]: self.pool.submit(status, c["id"]) for c in self.rows}
        self.collecting()
        self.rebuild()

    def collecting(self):
        """Background jobs were started: look for their results often again (collect)."""
        self.collect_every(100)

    def collect_every(self, ms):
        try:
            if self.collector.interval() != ms:
                self.collector.setInterval(ms)
        except (AttributeError, RuntimeError):       # (before the timer exists, or in a test's bare window)
            pass

    def collect(self):
        for cid, fut in list(self.latest_futures.items()):
            if fut.done():
                del self.latest_futures[cid]
                if fut.cancelled():                      # (the window closing)
                    continue
                self.latest[cid] = fut.result()
                if getattr(self.details, "comp", {}).get("id") == cid:
                    self.details.show_issue(self.latest[cid])
        if self.self_update is not None and self.self_update.done():
            job, self.self_update = self.self_update, None       # (cleared first: a check that failed came back every tick)
            try:
                newest = None if job.cancelled() else job.result()
            except Exception:
                newest = None
            if newest:
                self.show_newest(newest)
                if self.update_state in ("check", "checking"):
                    self.set_update_state("update", newest)
            elif self.update_state == "checking" and newest == "" and sft.build_version() != self.running_build():
                # Nothing newer on GitHub, but the checkout changed since this window opened: what's
                # on disk is newer than what runs here (an update in a terminal, a git pull).
                self.set_update_state("restart")
                self.say(_("Frame Tweaks was updated to {version} since this window opened: ↻ Restart to use "
                           "it.").format(version=sft.build_version()), good=True)
            elif self.update_state == "checking":
                left = sft.unfinished_update() if newest == "" else []
                self.set_update_state("finish" if left else "check")
                if newest is None:                       # (offline, say: not "up to date")
                    self.say(_("Couldn't check for updates (no connection to GitHub?)."))
                elif left:                               # (an update cut short: the checkout's new, these aren't)
                    self.say(_("The last update didn't finish: {tweaks} weren't installed again. ⬇ Finish the "
                               "update does it.").format(tweaks=", ".join(left)))
                else:
                    self.say(_("✔ Frame Tweaks is up to date ({version}).").format(version=self.running_build()),
                                             good=True)
        if self.pack_check is not None and self.pack_check.done():
            try:
                found = self.pack_check.result()
            except Exception:                            # (a pack's git saying something odd)
                found = []
            self.pack_check = None
            self.pack_updates = {p["dir"] for p in found}
            self.show_pack_updates()
            self.follow_packs()                          # (it read the packs again: one changed outside, say)
            if isinstance(self.details, Packs):
                self.details.build()
        self.finish_pack_job()
        shown = False
        for cid, fut in list(self.update_futures.items()):
            if fut.done():
                del self.update_futures[cid]
                found = None if fut.cancelled() or fut.exception() is not None else fut.result()
                state = self.state.get(cid)
                if found and (state is None or state[0] not in GONE):
                    self.updates[cid] = found
                else:                                    # (up to date now, or uninstalled meanwhile)
                    self.updates.pop(cid, None)
                self.show_status(cid)
                shown = True
        for cid, fut in list(self.futures.items()):
            if fut.done():
                del self.futures[cid]
                if fut.cancelled():                      # (the window closing)
                    continue
                try:
                    self.state[cid] = fut.result()
                except Exception as e:                   # (said on its row, rather than "checking…" for good)
                    self.state[cid] = (2, _("status check failed: {error}").format(error=str(e) or type(e).__name__))
                c = component(cid)
                if self.state[cid][0] in GONE:
                    self.updates.pop(cid, None)          # (not installed: nothing to update)
                elif c is not None and sft.script(c, "update-check") is not None:
                    self.update_futures[cid] = self.pool.submit(update_check, cid)
                self.show_status(cid)
                shown = True
                if cid in self.status_labels:
                    label = self.status_labels[cid]
                    text, kind = status_text(self.state[cid])
                    label.setProperty("status", kind)
                    label.style().unpolish(label)
                    label.style().polish(label)
                    self.update_run(cid)
                    self.update_again(cid)
                    box = self.boxes.get(cid)
                    if box is not None and cid not in self.wanted:
                        box.blockSignals(True)
                        box.setChecked(self.state[cid][0] not in GONE)
                        box.blockSignals(False)
                self.update_apply()
        if shown:
            self.fit_list()                              # (a status can make its row wider)
        busy = (self.futures or self.latest_futures or self.update_futures or self.self_update is not None
                or self.pack_check is not None or self.pack_job is not None)
        self.collect_every(100 if busy else 1000)

    # ---- layout -----------------------------------------------------------------
    def rebuild(self, *_args):
        self.row_widgets, self.focus_index = [], -1
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        hidden = self.hidden()
        # (groups by their English name, category_en: the shown one follows the language)
        hidden_cats = sft.read_categories(HIDDEN_CATS, self.rows) & {c["category_en"] for c in self.rows}
        collapsed = sft.read_categories(COLLAPSED, self.rows)
        showing = self.show_hidden.isChecked()
        n_hidden = sum(1 for c in self.rows if c["id"] in hidden and c["category_en"] not in hidden_cats)
        n_hidden += len(hidden_cats)
        self.show_hidden.setText(_("Show hidden ({n})").format(n=n_hidden))
        self.show_hidden.setEnabled(n_hidden > 0 or showing)
        self.boxes, self.status_labels, self.run_buttons, self.again_buttons = {}, {}, {}, {}
        not_needed = sft.not_needed(self.rows)
        category = None
        for comp in self.rows:
            cid = comp["id"]
            cat, key = comp["category"], comp["category_en"]
            is_hidden = cid in hidden
            if key in hidden_cats and not showing:
                continue
            if is_hidden and not showing:
                continue
            if cat != category:
                category = cat
                count = sum(1 for c in self.rows if c["category"] == cat and (showing or c["id"] not in hidden))
                self.grid.addWidget(CategoryHeader(self, cat, count, key in collapsed, key in hidden_cats, key))
            if key in collapsed:
                continue
            row = Row(self, comp)
            self.row_widgets.append(row)
            row.setProperty("hidden_row", "true" if is_hidden else "false")
            g = QGridLayout(row)
            g.setContentsMargins(8, 10, 12, 10)
            g.setHorizontalSpacing(14)
            box = QCheckBox()
            state = self.state.get(cid)
            box.setChecked(self.wanted.get(cid, state[0] not in GONE if state else False))
            box.setToolTip(_("Tick to install, untick to remove"))
            why_not = not_needed.get(cid)
            if why_not is not None and not sft.installed_record(cid):    # (installed: untick to remove)
                box.setEnabled(False)
                box.setToolTip(_("Not needed on this Frame: %s") % why_not)
            box.toggled.connect(lambda on, c=cid: (self.wanted.__setitem__(c, on), self.update_apply()))
            self.boxes[cid] = box
            icon = QLabel()
            icon.setPixmap(row_icon(cid).pixmap(40, 40))
            sudo = sft.sudo_note(comp)
            name = QLabel(html.escape(comp["title"], quote=False) +
                          ("  🧪" if comp["experimental"] else "") +
                          ("  🔗" if comp["link"] else "") +
                          ("  <span style='color:#e0b33a;font-size:12px'>sudo</span>" if sudo else "") +
                          ("" if comp["official"] else
                           f"  <span style='color:#e0b33a;font-size:12px'>🧩 {html.escape(comp['pack'])}</span>") +
                          ("  <span style='color:#6b7783'>" + _("(hidden)") + "</span>" if is_hidden else ""))
            name.setObjectName("name")
            tips = []                                      # (one tooltip says each of them)
            if comp["experimental"]:
                tips.append(_("Experimental: %s") % comp["experimental"])
            if comp["link"]:
                tips.append(_("Linked: installed and uninstalled with the project's own commands, which Frame "
                              "Tweaks runs but doesn't check"))
            if sudo:
                tips.append(_("Asks for your sudo password: %s") % sudo)
            if not comp["official"]:
                tips.append((_("From the pack {pack}, not part of Frame Tweaks; used instead of {other}'s")
                             if comp["replaced"] else _("From the pack {pack}, not part of Frame Tweaks")).format(
                                pack=comp["pack"], other=comp["replaced"]))
            if tips:
                name.setToolTip("\n\n".join(tips))
            deps = comp["deps"]
            info = QLabel(html.escape(comp["desc"], quote=False) +
                          ("  <i style='color:#6b7783'>" + _("needs: %s") % ", ".join(deps) + "</i>" if deps else ""))
            info.setObjectName("desc")
            info.setWordWrap(True)
            if cid in KNOWN_ISSUES:
                info.setText(info.text() + "<br><span style='color:#e0b33a'>"
                             f"{html.escape(KNOWN_ISSUES[cid]['short'], quote=False)}</span>")
            if why_not is not None:
                info.setText(info.text() + "<br><span style='color:#e0b33a'>" + html.escape(
                    _("Not needed on this Frame: %s") % why_not, quote=False) + "</span>")
            link = QLabel()
            if "|" in comp["source"]:
                rel, url = comp["source"].split("|", 1)
                rel = _(rel)
                short = url.split("://", 1)[-1].removeprefix("github.com/").rstrip("/")
                if url.startswith("https://github.com/"):
                    short = "/".join(short.split("/")[:2])      # owner/repo; the link has the rest
                link_label(link).setText(with_copy(
                    f"<span style='color:#6b7783'>{html.escape(rel)}</span> "
                    f"<a style='color:#7fb2e5' href='{url}'>{html.escape(short)} ↗</a>"))
                link.setToolTip(_("Open %s") % url)
            text, kind = status_text(state)
            st = QLabel(text)
            st.setProperty("status", kind)
            st.setWordWrap(True)
            st.setTextFormat(Qt.TextFormat.RichText)
            st.linkActivated.connect(lambda _, c=cid: self.run_update(c))
            self.status_labels[cid] = st
            self.show_status(cid)
            run = QPushButton()
            run.setObjectName("run")
            self.run_buttons[cid] = run
            self.update_run(cid)
            run.clicked.connect(lambda _=False, c=comp: self.run(c))
            details = QPushButton("ⓘ")
            details.setObjectName("info")
            details.setToolTip(_("Details: what it is, why it's included, who made it"))
            details.clicked.connect(lambda _=False, c=comp: self.show_details(c))
            again = QPushButton("↻")
            again.setObjectName("again")
            again.clicked.connect(lambda _=False, c=cid: self.run_reinstall(c))
            self.again_buttons[cid] = again
            self.update_again(cid)
            hide = QPushButton(_("Unhide") if is_hidden else _("Hide"))
            hide.setToolTip(_("Show this tweak in the list again") if is_hidden else
                            _("Hide this tweak from the list (doesn't remove it)"))
            hide.clicked.connect(lambda _=False, c=cid: self.toggle_hidden(c))
            g.addWidget(box, 0, 0, 3, 1)
            g.addWidget(icon, 0, 1, 3, 1)
            g.addWidget(name, 0, 2)
            g.addWidget(info, 1, 2)
            if link.text():
                g.addWidget(link, 2, 2)
            g.addWidget(st, 0, 3, 3, 1)
            g.addWidget(run, 0, 4, 3, 1)
            col = 5
            if cid in SETTINGS_PAGES and run_label(cid):   # both a Run and settings: ⚙ beside Run
                gear = QPushButton("⚙")
                gear.setObjectName("info")
                gear.setToolTip(_("Settings"))
                gear.clicked.connect(lambda _=False, c=cid: self.open_settings(c))
                g.addWidget(gear, 0, col, 3, 1)
                col += 1
            g.addWidget(again, 0, col, 3, 1)
            g.addWidget(details, 0, col + 1, 3, 1)
            g.addWidget(hide, 0, col + 2, 3, 1)
            g.setColumnStretch(2, 3)
            g.setColumnStretch(3, 2)
            self.grid.addWidget(row)
        self.add_contribute_row()
        self.grid.addStretch(1)
        self.update_apply()
        self.fit_list()

    def fit_list(self):
        """The window is never narrower than the list's widest row: the list doesn't scroll
        sideways, so the buttons past a row's right edge (Hide, ↻, ⓘ, then Run) couldn't be reached.
        Nor is a Run button narrower than its text: the style sheet's min-width, set again each time
        it's styled (update_run), would let a narrow window squeeze "⟳ Restart SteamVR" to that.
        (Each row measured itself: rows just built aren't shown yet, so the list's layout leaves
        them out until they are.)"""
        for button in self.run_buttons.values():
            button.setMinimumWidth(button.sizeHint().width())
        rows = (self.grid.itemAt(i).widget() for i in range(self.grid.count()))
        widest = max((r.minimumSizeHint().width() for r in rows if r is not None), default=0)
        margins = self.grid.contentsMargins()
        bar = self.scroll.verticalScrollBar().sizeHint().width()
        self.scroll.setMinimumWidth(widest + margins.left() + margins.right() + bar + 2 * self.scroll.frameWidth())

    def add_contribute_row(self):
        """The list's last row, under every group whatever the packs' order (and whichever groups
        are folded or hidden): how to help (CONTRIBUTE), laid out as a tweak's row with nothing
        to install: no tick box or status, a call to action instead of Run."""
        self.grid.addSpacing(12)
        row = ContributeRow(self, CONTRIBUTE)
        self.row_widgets.append(row)
        row.setProperty("hidden_row", "false")
        row.setProperty("cta", "true")
        g = QGridLayout(row)
        g.setContentsMargins(8, 10, 12, 10)
        g.setHorizontalSpacing(14)
        spacer = QWidget()                           # (where a tweak's tick box is: the icons line up)
        spacer.setObjectName("spacer")
        spacer.setFixedWidth(QCheckBox().sizeHint().width())
        icon = QLabel()
        hits = sorted(BREEZE.glob(f"*/*/{CONTRIBUTE['icon']}.svg"))
        if hits:
            icon.setPixmap(QIcon(str(hits[-1])).pixmap(40, 40))
        name = QLabel(html.escape(_("Help make Frame Tweaks better"), quote=False))
        name.setObjectName("name")
        info = QLabel(html.escape(_("Have an idea for a tweak, or an app that belongs here? Found a bug, or speak "
                                    "another language? Every suggestion, report, translation and fix makes the Frame "
                                    "better for everyone who has one."), quote=False))
        info.setObjectName("desc")
        info.setWordWrap(True)
        read = QPushButton(_("Get involved"))
        read.setObjectName("apply")
        read.clicked.connect(self.show_contribute)
        g.addWidget(spacer, 0, 0, 2, 1)
        g.addWidget(icon, 0, 1, 2, 1)
        g.addWidget(name, 0, 2)
        g.addWidget(info, 1, 2)
        g.addWidget(read, 0, 4, 2, 1)
        g.setColumnStretch(2, 3)
        g.setColumnStretch(3, 2)
        self.grid.addWidget(row)

    def show_status(self, cid):
        """Status text, plus an Update link when upstream has a newer version; and on the tweak's
        page, if that's open, its status."""
        if isinstance(getattr(self, "details", None), Details) and self.details.comp["id"] == cid:
            self.details.show_state(self.state.get(cid))
        label = self.status_labels.get(cid)
        if label is None:
            return
        text, _kind = status_text(self.state.get(cid))
        text = html.escape(text, quote=False)
        if cid in self.updates:
            cur, new = self.updates[cid]
            text += ("<br><span style='color:#7fb2e5'>↑ " + _("{version} available").format(version=html.escape(new))
                     + " · <a style='color:#7fb2e5' href='u'>" + _("Update") + "</a></span>")
        label.setText(text)

    def run_update(self, cid, to=None):
        """Reinstall one tweak (fetches its latest upstream version), or update this repo (cid None;
        to: a release, or "stable" for the newest stable one)."""
        cmd = "./install.sh install " + shlex.quote(cid) if cid else "./install.sh update" + (
            " --to " + shlex.quote(to) if to else "")
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run:", cmd)
            return
        # (0 updated, 3 updated but a tweak didn't install again; else it didn't update: no "reopen")
        after = "" if cid else ("; rc=$?; if [ $rc -eq 0 ] || [ $rc -eq 3 ]; then echo; echo "
                                + shlex.quote(_("Close and reopen Frame Tweaks to use the new version.")) + "; fi")
        full = f"cd {shlex.quote(str(REPO))} && {cmd}{after}; echo; read -rp {close_prompt()}"
        self.proc = QProcess(self)
        self.proc.finished.connect(lambda *_: (self.updates.pop(cid, None), self.refresh(),
                                               cid is None and self.after_self_update()))
        in_terminal(self.proc, full)

    # ---- updating Frame Tweaks itself: Check for updates → Update to X → Restart --------
    def show_newest(self, newest):
        self.self_update_label.setText(
            "↑ " + _("{version} available").format(version=html.escape(newest)) + " · "
            "<a style='color:#7fb2e5' href='update'>" + _("Update") + "</a>")

    def set_update_state(self, state, newest=None):
        self.update_state, b = state, self.update_button
        self.update_newest = newest
        text, tip = {"check": (_("⟳ Check for updates"), _("Look for a newer Frame Tweaks release")),
                     "checking": (_("Checking…"), ""),
                     "update": (_("⬇ Update to {version}").format(version=newest),
                                _("Install it: your tweaks are updated with it")),
                     "restart": (_("↻ Restart"), _("Reopen Frame Tweaks to use the new version")),
                     "finish": (_("⬇ Finish the update"), _("Install the tweaks the last update didn't get to"))}[state]
        b.setText(text)
        b.setToolTip(tip)
        b.setEnabled(state != "checking")
        b.setObjectName("apply" if state in ("update", "restart") else "")
        b.style().unpolish(b)
        b.style().polish(b)

    def running_build(self):
        """The build this window runs (as it opened; sft.build_version() is the checkout's now)."""
        return getattr(self, "build_at_start", None) or sft.build_version()

    def show_pack_updates(self):
        """🧩 N pack updates, a link to the Packs page (packs added from a link; that page says which)."""
        n = len(getattr(self, "pack_updates", ()))
        self.pack_update_label.setText(
            ("🧩 <a style='color:#7fb2e5' href='packs'>" + ngettext("%d pack update", "%d pack updates", n) % n
             + "</a>") if n else "")
        self.pack_update_label.setToolTip(_("Packs added from a link have a newer version where they came from: "
                                            "the Packs page says which") if n else "")

    def update_clicked(self):
        if self.update_state == "check":
            self.set_update_state("checking")
            self.self_update = self.pool.submit(self_update_check)
            if self.pack_check is None:
                self.pack_check = self.pool.submit(sft.packs_with_updates)
            self.collecting()
        elif self.update_state in ("update", "finish"):
            self.run_update(None)
        elif self.update_state == "restart":
            self.restart_self()

    def channel_changed(self):
        """Test releases on or off (⚙ Preferences): a release found before may not be one to offer now."""
        if self.update_state != "restart":
            self.self_update_label.setText("")
            self.set_update_state("check")

    def after_self_update(self):
        """The updater's terminal closed: Restart if a new release is in place."""
        if current_release() != self.release_at_start:
            self.self_update_label.setText("")
            self.set_update_state("restart")

    def restart_self(self):
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would restart the window")
            return
        # A new window from the same session (environment kept), once this one has let go of the
        # single-instance lock.
        QProcess.startDetached("bash", ["-c", 'sleep 1; exec "$0" gui', str(REPO / "install.sh")])
        QApplication.quit()

    def run_reinstall(self, cid):
        """Remove one tweak and install it again in one go (stops its running programs first)."""
        cmd = "./install.sh reinstall " + shlex.quote(cid)
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run:", cmd)
            return
        full = f"cd {shlex.quote(str(REPO))} && {cmd}; echo; read -rp {close_prompt()}"
        self.proc = QProcess(self)
        self.proc.finished.connect(lambda *_: self.changed([cid]))
        in_terminal(self.proc, full)

    def changed(self, ids):
        """The terminal that installed, reinstalled or removed these tweaks closed: an update found
        for them before is in now (or went with them), and every row is checked again."""
        for cid in ids:
            self.updates.pop(cid, None)
        self.refresh()

    def update_again(self, cid):
        """The ↻ Reinstall button: only for installed tweaks."""
        button = self.again_buttons.get(cid)
        if button is None:
            return
        state = self.state.get(cid)
        installed = state is not None and state[0] not in GONE
        button.setEnabled(installed)
        button.setToolTip(_("Reinstall: remove it and install it again in one step (settings kept)")
                          if installed else _("Reinstall (available once it's installed)"))

    def update_run(self, cid):
        """Run/Open/... for installed tweaks with something to launch, Help otherwise."""
        button = self.run_buttons.get(cid)
        if button is None:
            return
        state = self.state.get(cid)
        installed = state is not None and state[0] not in GONE
        label = run_label(cid)
        if state is not None and state[0] in (RESTART, UNLOAD):    # (until SteamVR restarts: no Run or Settings)
            button.setText(_("⟳ Restart SteamVR"))
            button.setProperty("help", "false")
            button.style().unpolish(button)
            button.style().polish(button)
            button.setEnabled(True)
            button.setToolTip(_("SteamVR loads it only as it starts. Every open app closes.") if state[0] == RESTART
                              else _("SteamVR runs it until it restarts. Every open app closes."))
            return
        if cid in PAGES:
            button.setText(_(PAGES[cid][0]))
            button.setProperty("help", "false")
            button.style().unpolish(button)
            button.style().polish(button)
            button.setEnabled(installed)
            button.setToolTip(_("Choose which apps open with the shared KDE wallet; lock or unlock it")
                              if installed else _("Tick it and Apply first"))
            return
        if cid in SETTINGS_PAGES and not label:          # (with something to run: a ⚙ beside it)
            button.setText(_("⚙ Settings"))
            button.setProperty("help", "false")
            button.style().unpolish(button)
            button.style().polish(button)
            button.setEnabled(installed)
            button.setToolTip(_("Settings") if installed else _("Settings (tick it and Apply first)"))
            return
        button.setText(("▶ " + label) if label else _("Help"))
        button.setProperty("help", "false" if label else "true")
        button.style().unpolish(button)
        button.style().polish(button)
        button.setEnabled(installed or label is None)
        button.setToolTip(_("{label} (installs first if needed: tick it and Apply)").format(label=label)
                          if label and not installed
                          else label and f"{label}" or _("Nothing to launch: how to use it"))

    def open_settings(self, cid):
        self.close_details()
        self.details = SETTINGS_PAGES[cid](self)             # a page: Back and B return to the list
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)

    def run(self, comp):
        if (self.state.get(comp["id"]) or (None,))[0] in (RESTART, UNLOAD):
            self.restart_steamvr()
            return
        if comp["id"] in PAGES:
            self.close_details()
            self.details = PAGES[comp["id"]][1](self)            # a page: Back and B return to the list
            self.stack.addWidget(self.details)
            self.stack.setCurrentWidget(self.details)
            return
        if comp["id"] in SETTINGS_PAGES and not run_label(comp["id"]):
            self.close_details()
            self.details = SETTINGS_PAGES[comp["id"]](self)      # a page: Back and B return to the list
            self.stack.addWidget(self.details)
            self.stack.setCurrentWidget(self.details)
            return
        label = run_label(comp["id"])
        if label is None:
            self.show_details(comp)
            return
        c = component(comp["id"])
        cmd = sft.script(c, "run") if c else None      # (its run.sh, or a linked project's run: command)
        if cmd is None:                                 # (its folder went since the list was read: an update, say)
            self.say(_("Couldn't start {tweak}: its files aren't where they were when the list was read. "
                       "Close and reopen Frame Tweaks.").format(tweak=comp["title"]))
            return
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):      # (some restart things: Plasma, ydotoold)
            print("would run:", " ".join(cmd))
            return
        QProcess.startDetached(cmd[0], cmd[1:])
        # (a Restart, say, changes what its row should say: look again once it's had time)
        for ms in (3000, 10000):
            QTimer.singleShot(ms, lambda c=comp["id"]: self.recheck(c))

    def recheck(self, cid):
        """Check one row's status again (in the background, as the first time)."""
        if cid in self.futures or cid not in {c["id"] for c in self.rows}:
            return
        self.futures[cid] = self.pool.submit(status, cid)
        self.collecting()

    def changeEvent(self, ev):
        """Back to the window: rows that needed attention may not any more (desktop mode started
        since, say, and with it what the row waited for). Checked again, at most every 30 s."""
        super().changeEvent(ev)
        if ev.type() != QEvent.Type.ActivationChange or not self.isActiveWindow():
            return
        if time.monotonic() - getattr(self, "rechecked", 0) < 30:
            return
        self.rechecked = time.monotonic()
        for cid, st in list(getattr(self, "state", {}).items()):
            if st is not None and st[0] in (2, RESTART, UNLOAD):
                self.recheck(cid)

    def restart_steamvr(self):
        """⟳ Restart SteamVR, on the row of a tweak SteamVR loads only as it starts (installed, or
        uninstalled but still running): SteamOS's own restart (steamvr restart), which closes every
        app in the Steam session, desktop mode and this window too."""
        self.confirm(_("Restart SteamVR?") + "<br><br><span style='font-size:14px;color:#9aa6b2'>"
                     + html.escape(_("Every open app closes, desktop mode and this window too: save your work "
                                     "first. SteamVR then starts again by itself."), quote=False) + "</span>",
                     _("Restart SteamVR"), self.do_restart_steamvr)

    def do_restart_steamvr(self):
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run: steamvr restart")
            return
        # (With the VR session's runtime folder and D-Bus: steamvr restart goes through the user
        # service manager, which desktop mode's own can't reach. From the window in desktop mode
        # it failed, "Failed to connect to user scope bus", where nobody saw it: the script had
        # already exited fine.)
        run = f"/run/user/{os.getuid()}"
        if not QProcess.startDetached("env", [f"XDG_RUNTIME_DIR={run}", f"DBUS_SESSION_BUS_ADDRESS=unix:path={run}/bus",
                                              "steamvr", "restart"])[0]:
            self.say(_("Couldn't restart SteamVR; restart it from its menu, or reboot."))

    def show_details(self, comp, back=None):
        self.close_details()
        self.details = Details(self, comp, self.state.get(comp["id"]))
        self.details_back = back                     # (where its Back goes: see leave_details)
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)

    def show_tweak(self, cid):
        """That tweak's page (--show ID); nothing for an unknown id (from a pack not in use, say)."""
        comp = next((c for c in self.rows if c["id"] == cid), None)
        if comp is not None:
            self.show_details(comp)

    def show_contribute(self):
        self.close_details()
        self.details = ReadmePage(self, REPO / "docs/contribute.md", _("Help make Frame Tweaks better"))
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)

    def show_readme(self):
        self.close_details()
        self.details = ReadmePage(self)
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)

    def show_report(self):
        self.close_details()
        self.details = ReportPage(self, follow_link, self.pool, REPO)
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)

    def show_prefs(self):
        self.close_details()
        self.details = Preferences(self, follow_link)
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)

    def show_packs(self):
        self.close_details()
        self.details = Packs(self, follow_link, self.pool)          # (it reads the packs anew)
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)
        self.follow_packs()

    def reload_tweaks(self):
        """After a pack was trusted or dropped: the list, settings and known issues anew."""
        sft.load(refresh=True)
        self.use_tweaks()

    def follow_packs(self):
        """sft read the packs again (the Packs page opening, Check for updates, a pack added or
        updated from a link): if the tweaks in use aren't the list's any more (a pack changed or
        turned off outside the window, say), the list follows. Its rows would ask sft for tweaks it
        no longer has."""
        if [(c["id"], c["dir"]) for c in components()] != [(c["id"], c["dir"]) for c in self.rows]:
            self.use_tweaks()

    def use_tweaks(self):
        """The list, settings and known issues of the tweaks sft has read."""
        global KNOWN_ISSUES
        sft.SETTINGS = sft.settings_specs()
        SETTINGS_PAGES.clear()
        SETTINGS_PAGES.update({cid: (lambda w, c=cid: SettingsPage(w, c)) for cid in sft.SETTINGS})
        KNOWN_ISSUES = {c["id"]: c["known_issue"] for c in components() if c["known_issue"]}
        self.check_known_issues()
        self.rows = components()
        self.refresh()

    def check_known_issues(self):
        """Has a known issue's app a newer release? Looked for once each, in the background: as the
        window opens, and for a tweak a pack brings later."""
        for cid, issue in KNOWN_ISSUES.items():
            if cid not in self.latest and cid not in self.latest_futures:
                self.latest_futures[cid] = self.pool.submit(latest_release, issue["latest"])
                self.collecting()

    def finish_pack_job(self):
        """A pack added or updated from a link (the Packs page's start), once its git clone or pull
        is done: its end goes to the Packs page open then (going Back meanwhile doesn't lose it),
        and the list follows the tweaks in use."""
        job = self.pack_job
        if job is None or not job[0].done():
            return
        self.pack_job = None
        fut, done, _saying = job
        if fut.cancelled():                          # (the window closing)
            return
        if isinstance(self.details, Packs):
            self.details.finished(fut, done)
        elif fut.exception() is None:
            done(None, fut.result())                 # (no page to tell: the window's part only)
        self.follow_packs()

    def close_details(self):
        if self.details is not None:
            self.stack.removeWidget(self.details)
            self.details.deleteLater()
            self.details = None
        self.stack.setCurrentIndex(0)
        self.details_back = None

    def leave_details(self):
        """Back on a page: to where it was opened from (the Packs page, for a tweak of a pack's
        inventory), else to the list."""
        back = getattr(self, "details_back", None)
        self.close_details()
        if back is not None:
            back()

    # ---- in-window messages (no dialogs: in VR they'd open in the dashboard) ----------
    def say(self, text, good=False):
        """A message on the left of the bottom bar for a few seconds: green when it's good news
        (as ✔ statuses), amber otherwise."""
        colour = "#5cc77a" if good else "#e0b33a"
        self.notice.setText(f"<span style='color:{colour}'>{html.escape(text)}</span>")
        shown = self.notice.text()
        QTimer.singleShot(6000, lambda: self.notice.text() == shown and self.notice.setText(self.hint_text))

    def make_confirm_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addStretch(1)
        text = QLabel()
        text.setObjectName("title")
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(text)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        no = QPushButton(_("Cancel"))
        no.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        yes = QPushButton()
        yes.setObjectName("apply")
        buttons.addWidget(no)
        buttons.addWidget(yes)
        buttons.addStretch(1)
        lay.addLayout(buttons)
        lay.addStretch(2)
        return page, text, yes

    # ---- apply --------------------------------------------------------------
    def pending_changes(self):
        """(install, remove): ticked but not installed, unticked but installed. Rows whose status
        isn't known yet don't count; a tweak with a warning is reinstalled with its ↻ button."""
        known = [c["id"] for c in self.rows if self.state.get(c["id"]) is not None]
        want = {cid: self.wanted.get(cid, self.state[cid][0] not in GONE) for cid in known}
        return ([cid for cid, on in want.items() if on and self.state[cid][0] in GONE],
                [cid for cid, on in want.items() if not on and self.state[cid][0] not in GONE])

    def update_apply(self):
        """Apply changes is dimmed while there's nothing to change."""
        button = getattr(self, "apply_button", None)
        if button is None:
            return
        add, remove = self.pending_changes()
        button.setEnabled(bool(add or remove))
        button.setToolTip((_("Install: %s") % ", ".join(add) if add else "") + ("; " if add and remove else "")
                          + (_("Remove: %s") % ", ".join(remove) if remove else "")
                          or _("Nothing to change: tick or untick a tweak first"))

    def apply(self):
        if self.futures:
            self.say(_("Still checking status; try again in a moment."))
            return
        # From what you ticked (self.wanted), so rows in collapsed or hidden categories count too.
        add, remove = self.pending_changes()
        if not add and not remove:
            self.say(_("Nothing to change."))
            return
        if remove:
            self.confirm(
                _("These installed tweaks were unticked and will be <b>removed</b>:") + "<br><br>"
                + html.escape(", ".join(remove)) + "<br><br><span style='font-size:14px;color:#9aa6b2'>"
                + (_("Their settings are removed too (⚙ Preferences); their data is kept.")
                   if sft.uninstall_settings() == "remove" else _("Their settings and data are kept.")) + "</span>",
                _("Remove them"), lambda: self.run_changes(add, remove))
            return
        self.run_changes(add, remove)

    def confirm(self, text, yes_label, on_yes):
        """Ask on the confirm page (text: rich text): Cancel goes back to the list, the yes button
        (yes_label) back too, then does on_yes."""
        self.confirm_text.setText(text)
        self.confirm_yes.setText(yes_label)
        try:
            self.confirm_yes.clicked.disconnect()
        except TypeError:
            pass
        self.confirm_yes.clicked.connect(lambda: (self.stack.setCurrentIndex(0), on_yes()))
        self.stack.setCurrentWidget(self.confirm_page)

    def run_changes(self, add, remove):
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):      # for tests: show the plan, change nothing
            print("would remove:", " ".join(remove) or "none")
            print("would install:", " ".join(add) or "none")
            return
        steps = []
        if remove:
            steps.append("./install.sh uninstall " + " ".join(remove))
        if add:
            steps.append("./install.sh install " + " ".join(add))
        # (one splash for both: ./install.sh run under lib/splash.py doesn't start another)
        cmd = (f"cd {shlex.quote(str(REPO))} && python3 lib/splash.py -- bash -c {shlex.quote(' && '.join(steps))}"
               f"; echo; read -rp {close_prompt()}")
        self.proc = QProcess(self)            # don't block the window while Konsole runs
        self.proc.finished.connect(lambda *_: (self.wanted.clear(), self.changed(add + remove)))
        in_terminal(self.proc, cmd)

    def uninstall_self(self, keep_tweaks, settings, keep_apps=True):
        """⚙ Preferences → Uninstall Frame Tweaks: ./install.sh uninstall-self in a terminal, and this
        window closes (it runs from the folder and the Python setup that go)."""
        flags = (["--keep-tweaks"] if keep_tweaks else [] if keep_apps else ["--remove-apps"]) + [f"--{settings}-settings"]
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):      # for tests: show the plan, change nothing
            print("would run: ./install.sh uninstall-self " + " ".join(flags))
            return
        cmd = f"cd {shlex.quote(str(REPO))} && ./install.sh uninstall-self {' '.join(flags)}; echo; read -rp {close_prompt()}"
        # (detached: it must outlive this window, which quits at once)
        ok, _pid = QProcess.startDetached("bash", ["-c", 'exec konsole --separate -e bash -c "$1" >/dev/null 2>&1',
                                                  "konsole", cmd])
        if ok:
            QApplication.instance().quit()
        else:
            self.say(_("Couldn't open a terminal: run ./install.sh uninstall-self in {folder}").format(folder=REPO))

    def eventFilter(self, obj, ev):
        """In VR: a haptic tick when the laser moves onto a button or tick box, a firmer pulse
        when it's clicked (vrbuttons.py), as on Arrow Pad."""
        t = ev.type()
        if t in (QEvent.Type.Enter, QEvent.Type.MouseButtonPress) and isinstance(obj, QAbstractButton) \
                and obj.isEnabled() and obj.isVisible() and self.prefs["haptics"]:
            self.vr_buttons.haptic("hover" if t == QEvent.Type.Enter else "press")
        return False

    # ---- controller buttons in VR (vrbuttons.py): B back, Y home, A tick ----------
    def poll_vr_buttons(self):
        over = self.laser_over_window()
        self.vr_buttons.poll(over)
        want = 33 if over or self.vr_buttons.claimed else 250
        if self.vr_timer.interval() != want:
            self.vr_timer.setInterval(want)

    def laser_over_window(self):
        """True while the laser is really on this window: the pointer is inside it and has moved
        in the last 3 s (a laser always jitters). Qt's hover state alone can stay set after the
        laser leaves for the dashboard, which would keep A/B/Y claimed from other apps."""
        import time
        pos = QCursor.pos()
        last, since = self._laser
        if pos != last:
            self._laser = (pos, time.monotonic())
            since = time.monotonic()
        return self.isVisible() and self.frameGeometry().contains(pos) and time.monotonic() - since < 3

    def go_back(self):
        if self.details is not None:
            self.leave_details()
        else:
            self.stack.setCurrentIndex(0)

    def go_home(self):
        self.close_details()
        self.scroll.verticalScrollBar().setValue(0)

    def toggle_pointed_row(self):
        """A: the row the laser points at, else the highlighted one (left D-pad)."""
        if self.stack.currentIndex() != 0:
            return
        w = QApplication.widgetAt(QCursor.pos())
        while w is not None and not isinstance(w, Row):
            w = w.parentWidget()
        if w is None and 0 <= self.focus_index < len(self.row_widgets):
            w = self.row_widgets[self.focus_index]
        if isinstance(w, ContributeRow):
            self.show_contribute()
        elif w is not None and w.comp["id"] in self.boxes:
            self.boxes[w.comp["id"]].toggle()

    def move_focus(self, step):
        """Left D-pad up/down: move a highlight through the visible rows."""
        if self.stack.currentIndex() != 0 or not self.row_widgets:
            return
        old = self.focus_index
        self.focus_index = max(0, min(len(self.row_widgets) - 1, old + step if old >= 0 else 0))
        for i in {old, self.focus_index}:
            if 0 <= i < len(self.row_widgets):
                r = self.row_widgets[i]
                r.setProperty("focused", "true" if i == self.focus_index else "false")
                r.style().unpolish(r)
                r.style().polish(r)
        self.scroll.ensureWidgetVisible(self.row_widgets[self.focus_index], 0, 40)

    # ---- diagnostics and errors -------------------------------------------------
    def make_error_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        head = QLabel(_("Something went wrong in the installer window"))
        head.setObjectName("title")
        lay.addWidget(head)
        hint = QLabel(_("Copy the details into a bug report. The window keeps working: go back and try again."))
        hint.setObjectName("desc")
        lay.addWidget(hint)
        text = QTextBrowser()
        lay.addWidget(text, 1)
        buttons = QHBoxLayout()
        copy = QPushButton(_("Copy for bug report"))
        copy.clicked.connect(lambda: (QApplication.clipboard().setText(text.toPlainText()),
                                      copy.setText(_("Copied"))))
        back = QPushButton(_("← Back"))
        back.clicked.connect(lambda: (copy.setText(_("Copy for bug report")), self.close_details()))
        report = QPushButton(_("🐞 Report a problem"))
        report.setToolTip(_("Copy these details, then save a diagnostics report and open the bug form"))
        report.clicked.connect(lambda: (QApplication.clipboard().setText(text.toPlainText()), self.show_report()))
        buttons.addWidget(back)
        buttons.addStretch(1)
        buttons.addWidget(copy)
        buttons.addWidget(report)
        lay.addLayout(buttons)
        return page, text

    def show_error(self, kind, value, tb):
        """sys.excepthook: show it in the window (a dialog would open elsewhere in VR)."""
        import platform
        import traceback
        version = self.running_build()
        details = (f"Frame Tweaks {version}, Python {platform.python_version()}, {platform.machine()}\n\n"
                   + "".join(traceback.format_exception(kind, value, tb)))
        self.error_text.setPlainText(details.replace(str(Path.home()), "~"))
        self.stack.setCurrentWidget(self.error_page)
        sys.__excepthook__(kind, value, tb)

    def closeEvent(self, ev):
        if self.vr_buttons:
            self.vr_buttons.close()
        self.collector.stop()                       # (the jobs it would look at are cancelled now)
        self.pool.shutdown(wait=False, cancel_futures=True)
        for proc in self.findChildren(QProcess):    # (stopped as the window goes: their finished
            proc.blockSignals(True)                 # would refresh it, with the pool shut down)
        super().closeEvent(ev)


SERVER = f"frame-tweaks-gui-{os.getuid()}"


ANSWER_MS = 3000      # (how long an open window has to answer a second launch before it's taken as stuck)


def hand_over(tweak=""):
    """One window: a second launch asks the open one to come forward (on that tweak) and exits
    (True). The open one answers with its session: open in the other one (VR or desktop mode),
    that's where it came forward, so a notification says so. No answer: it's stuck, and is
    stopped so this launch opens a window instead of nothing (False, as with none open)."""
    probe = QLocalSocket()
    probe.connectToServer(SERVER)
    if not probe.waitForConnected(300):
        return False
    probe.write(f"show {tweak}".strip().encode())
    probe.waitForBytesWritten(300)
    # (the answer can be in before the wait: the open window writes it as soon as it connects)
    if probe.bytesAvailable() or probe.waitForReadyRead(ANSWER_MS) or probe.bytesAvailable():
        there, here = bytes(probe.readAll()).decode(errors="replace").strip(), browser.session_of(os.environ)
        if there and here and there != here:
            notify(_("Frame Tweaks is already open in {session}").format(session=_(there)),
                   _("It came to the front there. Close it there to open it here."))
        return True
    probe.abort()
    stop_stuck_windows()
    return False


def notify(title, body):
    """A notification, for a launch that opens no window of its own."""
    try:
        subprocess.Popen(["notify-send", "-a", "Frame Tweaks", title, body], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def stop_stuck_windows():
    """The open window didn't answer a second launch: it's stuck (or one from before an update
    that doesn't answer). Stop it, so the new one opens instead of nothing; noted in the log."""
    import signal
    pids = window_pids()
    for sig, wait in ((signal.SIGTERM, 2), (signal.SIGKILL, 0)):
        for pid in pids:
            try:
                os.kill(pid, sig)
            except OSError:
                pass
        deadline = time.monotonic() + wait
        while wait and time.monotonic() < deadline and any(Path(f"/proc/{p}").exists() for p in pids):
            time.sleep(0.1)
    try:
        log = Path.home() / ".local/state/frame-tweaks/logs/window.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + f"an open window didn't answer: stopped it ({pids})\n")
    except OSError:
        pass


SCRIPT = Path(__file__).resolve()


def window_pids():
    """This user's other processes running this window: a Python (./install.sh runs it as
    sft-python) given this very script. Not an editor that has it open, say, nor any other command
    line that only names it."""
    try:
        out = subprocess.run(["pgrep", "-u", str(os.getuid()), "-f", "frame-tweaks-gui.py"],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    pids = []
    for pid in (int(p) for p in out.split() if p.isdigit() and int(p) != os.getpid()):
        try:
            argv = Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace").split("\0")
            cwd = os.readlink(f"/proc/{pid}/cwd")          # (./install.sh gives it as gui/frame-tweaks-gui.py)
        except OSError:                                      # (it ended meanwhile)
            continue
        if len(argv) > 1 and re.fullmatch(r"sft-python|python[\d.]*", Path(argv[0]).name) \
                and (Path(cwd) / argv[1]).resolve() == SCRIPT:
            pids.append(pid)
    return pids


def watch_for_hangs(log_dir):
    """If the window stops responding (its event loop stalls 10 s), write where every thread is
    to log_dir/gui-hang-<time>.log: the next freeze leaves a clue instead of nothing."""
    import faulthandler
    import threading
    beat = [time.monotonic()]
    QTimer(QApplication.instance(), interval=1000, timeout=lambda: beat.__setitem__(0, time.monotonic())).start()

    def watch():
        reported = False
        while True:
            time.sleep(2)
            stalled = time.monotonic() - beat[0]
            if stalled > 10 and not reported:
                try:
                    log_dir.mkdir(parents=True, exist_ok=True)
                    with open(log_dir / time.strftime("gui-hang-%Y%m%d-%H%M%S.log"), "w") as f:
                        f.write(f"The installer window's event loop stalled for {stalled:.0f} s. Threads:\n")
                        faulthandler.dump_traceback(f, all_threads=True)
                except OSError:
                    pass
                reported = True
            elif stalled < 3:
                reported = False
    threading.Thread(target=watch, daemon=True, name="hang-watch").start()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("frame-tweaks")
    app.setDesktopFileName("io.github.AstronautCheetah.FrameTweaks")
    # --show ID: open on that tweak's page (lib/needs.py: a feature that needs it, not installed).
    args = sys.argv[1:]
    tweak = args[args.index("--show") + 1] if "--show" in args[:-1] else ""
    if hand_over(tweak):
        return
    QLocalServer.removeServer(SERVER)
    server = QLocalServer()
    server.listen(SERVER)
    watch_for_hangs(Path.home() / ".local/state/frame-tweaks/logs")
    w = Window()

    def come_forward():
        conn = server.nextPendingConnection()
        if conn is not None:          # (the session it's open in: see above)
            conn.write((browser.session_of(os.environ) or "").encode())
            conn.flush()
        w.showNormal()
        w.raise_()
        w.activateWindow()
        if conn is not None:          # ("show ID": that tweak's page, once the message has arrived)
            conn.readyRead.connect(lambda: w.show_tweak(bytes(conn.readAll()).decode(errors="replace")[5:].strip()))
    server.newConnection.connect(come_forward)
    sys.excepthook = w.show_error
    app.aboutToQuit.connect(i18n.withdraw)          # (programs started later follow the keyboard again)
    w.show()
    if tweak:
        w.show_tweak(tweak)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
