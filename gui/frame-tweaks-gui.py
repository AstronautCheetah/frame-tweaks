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
from PyQt6.QtCore import QEvent, QProcess, Qt, QTimer, QUrl
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtGui import QCursor, QDesktopServices, QFont, QFontMetrics, QIcon, QImage
from PyQt6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QGridLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QStackedWidget, QTextBrowser, QToolTip,
                             QVBoxLayout, QWidget)

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))
os.environ.setdefault("FRAME_TWEAKS_LIB", str(REPO / "lib"))   # (packs' scripts source the helpers through it)
sys.path.insert(0, str(REPO / "gui"))           # (its pages, e.g. wallet_page.py)
import sft  # noqa: E402  (shared with ./install.sh: components, hidden rows, settings)
from sft import COLLAPSED, CONF, HIDDEN_CATS, component, components, read_set, run_label, write_set  # noqa: E402
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
QWidget#row QLabel, QWidget#row QCheckBox { background: transparent; }
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
"""



def status(cid):
    """(code, text): 0 ok, 1 not installed, 2 needs attention."""
    try:
        # (a check that never returns would hold a worker for good; four of them, every status)
        r = subprocess.run(["bash", str(component(cid)["dir"] / "status.sh")], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return 2, _("status check didn't finish (took over a minute)")
    text = r.stdout.strip().split(None, 1)[-1] if r.stdout.strip() else ""
    return r.returncode, text


def update_check(cid):
    """(installed, latest) when <id>/update-check.sh reports a newer upstream version, else None."""
    script = component(cid)["dir"] / "update-check.sh"
    try:
        out = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=20).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        return None
    if len(out) == 2 and version_tuple(out[1]) > version_tuple(out[0]):
        return out[0], out[1]
    return None


STABLE_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
ANY_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.]+))?$")
CHANNEL = CONF.parent / "channel"           # (~/.config/frame-tweaks/channel, as lib/common.sh reads it)


def release_channel():
    c = os.environ.get("FRAME_TWEAKS_CHANNEL") or ""
    if not c:
        try:
            c = CHANNEL.read_text().strip()
        except OSError:
            pass
    return "beta" if c == "beta" else "stable"


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


def current_release():
    return (REPO / "VERSION").read_text().strip() if (REPO / "VERSION").exists() else "0"


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
    text around HTML blocks): centred pictures become pictures, folded <details> sections show
    open with their summary in bold, and badges (pictures from the web) are left out."""
    text = re.sub(r'<p[^>]*>\s*<img\b[^>]*?\bsrc="([^"]+)"[^>]*?\balt="([^"]*)"[^>]*>\s*</p>',
                  lambda m: f"![{m[2]}]({m[1]})", text)
    text = re.sub(r"<details>\s*<summary>(.*?)</summary>", lambda m: f"**{m[1].strip()}**\n", text, flags=re.S)
    text = re.sub(r"</details>", "", text)
    text = re.sub(r"<!--.*?-->\n?", "", text, flags=re.S)
    return re.sub(r"^\[!\[[^\]]*\]\(https?://[^)]*\)\]\([^)]*\)\s*$", "", text, flags=re.M)


def readme_browser(text, comp):
    """A README (Markdown) as the window shows it: links absolute (readme_links), pictures from the
    local copy and fitted, a 📋 after each link, the window's font and link colour."""
    view = QTextBrowser()
    view.setOpenLinks(False)
    view.anchorClicked.connect(lambda u: follow_link(u.toString()) if u.scheme() else to_heading(view, u.fragment()))
    view.document().setDefaultStyleSheet(
        "a { color: #7fb2e5; } code { background: #1c232a; } pre { background: #1c232a; }")
    view.setMarkdown(readme_links(text, comp))
    # (toHtml() pins the font and link colour it saw; dropping them keeps the window's style.)
    html_ = re.sub(r'<body style="[^"]*">', "<body>", fit_images(with_copy(view.toHtml())), count=1)
    view.setHtml(html_.replace("color:#0000ff;", "color:#7fb2e5;"))
    return view


def to_heading(view, anchor):
    """A README's link to one of its own headings (#build-from-source, named as GitHub names
    them): scroll there. (Qt's Markdown reader gives headings no anchors of their own.)"""
    block = view.document().begin()
    while block.isValid():
        if block.blockFormat().headingLevel() and \
                re.sub(r"[^\w\- ]", "", block.text().strip().lower()).replace(" ", "-") == anchor:
            view.verticalScrollBar().setValue(int(view.document().documentLayout().blockBoundingRect(block).top()))
            return
        block = block.next()


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
        QToolTip.showText(QCursor.pos(), _("Link copied"))
    elif url.startswith(("https:", "http:")) and (r := browser.launch(url)):
        note, proc, handoff = r
        QToolTip.showText(QCursor.pos(), note)          # (it may have opened in the other session)
        if handoff:                                    # the browser runs there already: did it answer?
            QTimer.singleShot(8000, lambda: browser.still_stuck(proc, url) and stuck_link(url))
    elif url.startswith("file:") and (note := browser.open_path(url)):
        QToolTip.showText(QCursor.pos(), note)
    else:
        QDesktopServices.openUrl(QUrl(url))


def stuck_link(url):
    """The browser in the other session didn't take the link (it can stall while desktop mode
    isn't shown): the link goes on the clipboard instead, and the window says so."""
    QApplication.clipboard().setText(url)
    for w in QApplication.topLevelWidgets():
        if hasattr(w, "say"):
            w.say(_("The browser didn't answer, so the link is on the clipboard: paste it into the browser."))
            return
    QToolTip.showText(QCursor.pos(), _("The browser didn't answer: the link is on the clipboard."))


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
    return tuple(int(n) for n in re.findall(r"\d+", v or ""))


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
    return ({0: "✔ " + text, 2: "! " + text}.get(code, "· " + _("not installed")),
            {0: "ok", 2: "warn"}.get(code, "missing"))


class CategoryHeader(QWidget):
    """▾/▸ CATEGORY (n): click to collapse or expand (remembered); Hide/Unhide on the right."""

    def __init__(self, window, category, count, collapsed, hidden):
        super().__init__()
        self.setObjectName("cathead")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 4, 0)
        arrow = "▶" if collapsed else "▼"
        toggle = QPushButton(f"{arrow}  {category.upper().replace('&', '&&')}  ({count})"
                             + ("   · " + _("hidden") if hidden else ""))
        toggle.setObjectName("cattoggle")
        toggle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        toggle.setToolTip(_("Expand") if collapsed else _("Collapse"))
        toggle.clicked.connect(lambda: window.toggle_collapsed(category))
        lay.addWidget(toggle, 1)
        hide = QPushButton(_("Unhide category") if hidden else _("Hide category"))
        hide.setObjectName("cathide")
        hide.setToolTip(_("Show this category again") if hidden else
                        _("Hide the whole category from the list (doesn't remove anything)"))
        hide.clicked.connect(lambda: window.toggle_category_hidden(category))
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


class ReadmePage(QWidget):
    """Frame Tweaks' own README.md, as a page (Back returns to the list)."""

    def __init__(self, window):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        back = QPushButton(_("← Back"))
        back.clicked.connect(window.go_back)
        head.addWidget(back)
        title = QLabel(_("About Frame Tweaks"))
        title.setObjectName("title")
        head.addWidget(title, 1)
        lay.addLayout(head)
        try:
            text = plain_markdown((REPO / "README.md").read_text())
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
        back.clicked.connect(window.close_details)
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
            lay.addWidget(self.issue_label)
            self.show_issue(window.latest.get(comp["id"], "checking"))

        text, kind = status_text(state)
        rel, url = comp["source"].split("|", 1) if "|" in comp["source"] else ("", "")
        rel = _(rel) if rel else rel                        # (uses, from, …: dev/i18n.py collects them)
        facts = [(_("What it is"), md_text(comp["what"])),
                 (_("Why it's included"), md_text(comp["why"])),
                 (_("Made by"), md_text(comp["author"]))]
        if comp["experimental"]:
            facts.append((_("🧪 Experimental"), f"<span style='color:#e0b33a'>{md_text(comp['experimental'])}</span>"))
        if url:
            facts.append((_("Source"), f"{html.escape(rel)} <a style='color:#7fb2e5' href='{url}'>{url}</a>"))
        if comp["deps"]:
            facts.append((_("Needs"), _("{tweaks} (installed automatically)").format(tweaks=", ".join(comp["deps"]))))
        colour = {"ok": "#5cc77a", "warn": "#e0b33a"}.get(kind, "#9aa6b2")
        facts.append((_("Status"), f"<span style='color:{colour}'>{html.escape(text)}</span>"))
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
        summary = link_label(QLabel())
        summary.setText(with_copy("<table cellspacing=6>" + "".join(
            f"<tr><td style='color:#6b7783;padding-right:12px' valign=top><b>{k}</b></td><td>{v}</td></tr>"
            for k, v in facts) + "</table>"))
        summary.setWordWrap(True)
        lay.addWidget(summary)

        try:
            text = manifest.front_matter(comp["readme"].read_text())[1]
        except (OSError, manifest.ManifestError):
            text = "_" + _("No README.") + "_"
        # (Its opening, what it is and why, is in the table above already.)
        text = re.sub(r"<!-- generated:intro .*?<!-- /generated:intro -->\n*", "", text, flags=re.S)
        lay.addWidget(readme_browser(text, comp), 1)

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
        one at a time: a page opened again meanwhile doesn't start a second."""
        cmd = ["bash", str(a["dir"] / a["script"]), *a.get("args", [])]
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run:", " ".join(cmd))
            return
        self.notice.setText(_("Working… (a download can take a minute)"))
        if any(p.state() != QProcess.ProcessState.NotRunning for p in self.window().findChildren(QProcess, "action")):
            return
        for _a, b, _note in self.actions:
            b.setEnabled(False)
        proc = QProcess(self.window())
        proc.setObjectName("action")
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        def done(*_args):
            proc.deleteLater()
            if sip.isdeleted(self):             # (its page was closed meanwhile)
                return
            lines = [re.sub(r"\x1b\[[0-9;]*m", "", l).strip() for l in
                     bytes(proc.readAll()).decode(errors="replace").splitlines()]
            lines = [l for l in lines if l and "#" not in l[:3]]          # (not curl's progress bar)
            ok = proc.exitStatus() == QProcess.ExitStatus.NormalExit and proc.exitCode() == 0
            last = lines[-1] if lines else _("Done.")
            self.notice.setText(last if ok else _("Didn't work: %s") % last)
            for _a, b, _note in self.actions:
                b.setEnabled(True)
            self.show_actions()
        proc.finished.connect(done)
        proc.start(cmd[0], cmd[1:])
        self.action_proc = proc

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
    def __init__(self):
        super().__init__()
        version = sft.build_version()
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
        self.latest_futures = {cid: self.pool.submit(latest_release, i["latest"])
                               for cid, i in KNOWN_ISSUES.items()}
        self.details = None
        self.updates, self.update_futures = {}, {}     # id -> (installed, latest) when newer
        self.prefs = window_prefs()
        self.self_update = self.pool.submit(self_update_check) if self.prefs["update_check"] else None

        self.release_at_start = current_release()
        self.update_state, self.update_newest = "check", None
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(20, 16, 20, 16)
        self.stack = None
        self.build_ui()
        QTimer(self, interval=100, timeout=self.collect).start()
        QTimer(self, interval=int(i18n.CHECK_EVERY * 1000), timeout=self.check_language).start()
        self.vr_buttons = None
        if os.environ.get("DISPLAY") == ":0":          # opened in VR: controller buttons too
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from vrbuttons import VRButtons
            self.vr_buttons = VRButtons({"back": self.go_back, "home": self.go_home,
                                         "toggle": self.toggle_pointed_row,
                                         "up": lambda: self.move_focus(-1),
                                         "down": lambda: self.move_focus(+1)}
                                        if self.prefs["controller"] else {})     # (⚙ Preferences)
            if self.vr_buttons.ok:
                QApplication.instance().installEventFilter(self)    # haptics: see eventFilter
                self._laser = (None, 0.0)
                QTimer(self, interval=33, timeout=lambda: self.vr_buttons.poll(self.laser_over_window())).start()
        self.refresh()

    def build_ui(self):
        """The window's widgets (again after a change of language: retranslate)."""
        top = QHBoxLayout()
        title = QLabel(f"Frame Tweaks <span style='color:#6b7783;font-size:14px'>{sft.build_version()}</span>")
        title.setObjectName("title")
        top.addWidget(title)
        top.addStretch(1)
        self.self_update_label = QLabel()
        self.self_update_label.setObjectName("notice")
        self.self_update_label.linkActivated.connect(lambda _: self.run_update(None))
        top.addWidget(self.self_update_label)
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
        collapsed = read_set(COLLAPSED)
        collapsed ^= {category}
        write_set(COLLAPSED, collapsed)
        self.rebuild()

    def toggle_category_hidden(self, category):
        sft.set_category_hidden(category, category not in read_set(HIDDEN_CATS))
        self.rebuild()

    def toggle_hidden(self, cid):
        sft.set_hidden(cid, cid not in self.hidden())
        self.rebuild()

    # ---- status, in the background ------------------------------------------------
    def refresh(self):
        self.state = {}
        self.futures = {c["id"]: self.pool.submit(status, c["id"]) for c in self.rows}
        self.rebuild()

    def collect(self):
        for cid, fut in list(self.latest_futures.items()):
            if fut.done():
                del self.latest_futures[cid]
                self.latest[cid] = fut.result()
                if getattr(self.details, "comp", {}).get("id") == cid:
                    self.details.show_issue(self.latest[cid])
        if self.self_update is not None and self.self_update.done():
            newest, self.self_update = self.self_update.result(), None
            if newest:
                self.show_newest(newest)
                if self.update_state in ("check", "checking"):
                    self.set_update_state("update", newest)
            elif self.update_state == "checking":
                self.set_update_state("check")
                if newest is None:                       # (offline, say: not "up to date")
                    self.say(_("Couldn't check for updates (no connection to GitHub?)."))
                else:
                    self.say(_("✔ Frame Tweaks is up to date ({version}).").format(version=current_release()), good=True)
        for cid, fut in list(self.update_futures.items()):
            if fut.done():
                del self.update_futures[cid]
                if fut.result():
                    self.updates[cid] = fut.result()
                    self.show_status(cid)
        for cid, fut in list(self.futures.items()):
            if fut.done():
                del self.futures[cid]
                self.state[cid] = fut.result()
                if self.state[cid][0] != 1 and (component(cid)["dir"] / "update-check.sh").exists():
                    self.update_futures[cid] = self.pool.submit(update_check, cid)
                if cid in self.status_labels:
                    label = self.status_labels[cid]
                    self.show_status(cid)
                    text, kind = status_text(self.state[cid])
                    label.setProperty("status", kind)
                    label.style().unpolish(label)
                    label.style().polish(label)
                    self.update_run(cid)
                    self.update_again(cid)
                    box = self.boxes.get(cid)
                    if box is not None and cid not in self.wanted:
                        box.blockSignals(True)
                        box.setChecked(self.state[cid][0] != 1)
                        box.blockSignals(False)
                self.update_apply()

    # ---- layout -----------------------------------------------------------------
    def rebuild(self, *_args):
        self.row_widgets, self.focus_index = [], -1
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        hidden = self.hidden()
        hidden_cats = read_set(HIDDEN_CATS) & {c["category"] for c in self.rows}
        collapsed = read_set(COLLAPSED)
        showing = self.show_hidden.isChecked()
        n_hidden = sum(1 for c in self.rows if c["id"] in hidden and c["category"] not in hidden_cats)
        n_hidden += len(hidden_cats)
        self.show_hidden.setText(_("Show hidden ({n})").format(n=n_hidden))
        self.show_hidden.setEnabled(n_hidden > 0 or showing)
        self.boxes, self.status_labels, self.run_buttons, self.again_buttons = {}, {}, {}, {}
        category = None
        for comp in self.rows:
            cid = comp["id"]
            cat = comp["category"]
            is_hidden = cid in hidden
            if cat in hidden_cats and not showing:
                continue
            if is_hidden and not showing:
                continue
            if cat != category:
                category = cat
                count = sum(1 for c in self.rows if c["category"] == cat and (showing or c["id"] not in hidden))
                self.grid.addWidget(CategoryHeader(self, cat, count, cat in collapsed, cat in hidden_cats))
            if cat in collapsed:
                continue
            row = Row(self, comp)
            self.row_widgets.append(row)
            row.setProperty("hidden_row", "true" if is_hidden else "false")
            g = QGridLayout(row)
            g.setContentsMargins(8, 10, 12, 10)
            g.setHorizontalSpacing(14)
            box = QCheckBox()
            state = self.state.get(cid)
            box.setChecked(self.wanted.get(cid, state[0] != 1 if state else False))
            box.setToolTip(_("Tick to install, untick to remove"))
            box.toggled.connect(lambda on, c=cid: (self.wanted.__setitem__(c, on), self.update_apply()))
            self.boxes[cid] = box
            icon = QLabel()
            icon.setPixmap(row_icon(cid).pixmap(40, 40))
            name = QLabel(html.escape(comp["title"], quote=False) +
                          ("  🧪" if comp["experimental"] else "") +
                          ("" if comp["official"] else
                           f"  <span style='color:#e0b33a;font-size:12px'>🧩 {html.escape(comp['pack'])}</span>") +
                          ("  <span style='color:#6b7783'>" + _("(hidden)") + "</span>" if is_hidden else ""))
            name.setObjectName("name")
            if comp["experimental"]:
                name.setToolTip(_("Experimental: %s") % comp["experimental"])
            if not comp["official"]:
                name.setToolTip((_("From the pack {pack}, not part of Frame Tweaks; used instead of {other}'s")
                                 if comp["replaced"] else _("From the pack {pack}, not part of Frame Tweaks")).format(
                                    pack=comp["pack"], other=comp["replaced"]))
            deps = comp["deps"]
            info = QLabel(html.escape(comp["desc"], quote=False) +
                          ("  <i style='color:#6b7783'>" + _("needs: %s") % ", ".join(deps) + "</i>" if deps else ""))
            info.setObjectName("desc")
            info.setWordWrap(True)
            if cid in KNOWN_ISSUES:
                info.setText(info.text() + "<br><span style='color:#e0b33a'>"
                             f"{html.escape(KNOWN_ISSUES[cid]['short'], quote=False)}</span>")
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
        self.grid.addStretch(1)
        self.update_apply()

    def show_status(self, cid):
        """Status text, plus an Update link when upstream has a newer version."""
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

    def run_update(self, cid):
        """Reinstall one tweak (fetches its latest upstream version), or update this repo (cid None)."""
        cmd = "./install.sh install " + shlex.quote(cid) if cid else "./install.sh update"
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run:", cmd)
            return
        after = "" if cid else "; echo; echo " + shlex.quote(_("Close and reopen Frame Tweaks to use the new version."))
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
                     "restart": (_("↻ Restart"), _("Reopen Frame Tweaks to use the new version"))}[state]
        b.setText(text)
        b.setToolTip(tip)
        b.setEnabled(state != "checking")
        b.setObjectName("apply" if state in ("update", "restart") else "")
        b.style().unpolish(b)
        b.style().polish(b)

    def update_clicked(self):
        if self.update_state == "check":
            self.set_update_state("checking")
            self.self_update = self.pool.submit(self_update_check)
        elif self.update_state == "update":
            self.run_update(None)
        elif self.update_state == "restart":
            self.restart_self()

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
        self.proc.finished.connect(lambda *_: self.refresh())
        in_terminal(self.proc, full)

    def update_again(self, cid):
        """The ↻ Reinstall button: only for installed tweaks."""
        button = self.again_buttons.get(cid)
        if button is None:
            return
        state = self.state.get(cid)
        installed = state is not None and state[0] != 1
        button.setEnabled(installed)
        button.setToolTip(_("Reinstall: remove it and install it again in one step (settings kept)")
                          if installed else _("Reinstall (available once it's installed)"))

    def update_run(self, cid):
        """Run/Open/... for installed tweaks with something to launch, Help otherwise."""
        button = self.run_buttons.get(cid)
        if button is None:
            return
        state = self.state.get(cid)
        installed = state is not None and state[0] != 1
        label = run_label(cid)
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
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):      # (some restart things: Plasma, ydotoold)
            print("would run:", "bash", comp["dir"] / "run.sh")
            return
        QProcess.startDetached("bash", [str(comp["dir"] / "run.sh")])

    def show_details(self, comp):
        self.close_details()
        self.details = Details(self, comp, self.state.get(comp["id"]))
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
        self.details = Preferences(self)
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)

    def show_packs(self):
        self.close_details()
        self.details = Packs(self)
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)

    def reload_tweaks(self):
        """After a pack was trusted or dropped: the list, settings and known issues anew."""
        global KNOWN_ISSUES
        sft.load(refresh=True)
        sft.SETTINGS = sft.settings_specs()
        SETTINGS_PAGES.clear()
        SETTINGS_PAGES.update({cid: (lambda w, c=cid: SettingsPage(w, c)) for cid in sft.SETTINGS})
        KNOWN_ISSUES = {c["id"]: c["known_issue"] for c in components() if c["known_issue"]}
        self.rows = components()
        self.refresh()

    def close_details(self):
        if self.details is not None:
            self.stack.removeWidget(self.details)
            self.details.deleteLater()
            self.details = None
        self.stack.setCurrentIndex(0)

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
        yes = QPushButton(_("Remove them"))
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
        want = {cid: self.wanted.get(cid, self.state[cid][0] != 1) for cid in known}
        return ([cid for cid, on in want.items() if on and self.state[cid][0] == 1],
                [cid for cid, on in want.items() if not on and self.state[cid][0] != 1])

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
            self.confirm_text.setText(
                _("These installed tweaks were unticked and will be <b>removed</b>:") + "<br><br>"
                + html.escape(", ".join(remove)) + "<br><br><span style='font-size:14px;color:#9aa6b2'>"
                + (_("Their settings are removed too (⚙ Preferences); their data is kept.")
                   if sft.uninstall_settings() == "remove" else _("Their settings and data are kept.")) + "</span>")
            try:
                self.confirm_yes.clicked.disconnect()
            except TypeError:
                pass
            self.confirm_yes.clicked.connect(lambda: (self.stack.setCurrentIndex(0), self.run_changes(add, remove)))
            self.stack.setCurrentWidget(self.confirm_page)
            return
        self.run_changes(add, remove)

    def run_changes(self, add, remove):
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):      # for tests: show the plan, change nothing
            print("would remove:", " ".join(remove) or "none")
            print("would install:", " ".join(add) or "none")
            return
        steps = [f"cd {shlex.quote(str(REPO))}"]
        if remove:
            steps.append("./install.sh uninstall " + " ".join(remove))
        if add:
            steps.append("./install.sh install " + " ".join(add))
        cmd = " && ".join(steps) + f"; echo; read -rp {close_prompt()}"
        self.proc = QProcess(self)            # don't block the window while Konsole runs
        self.proc.finished.connect(lambda *_: (self.wanted.clear(), self.refresh()))
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
            self.close_details()
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
        if w is not None and w.comp["id"] in self.boxes:
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
        back.clicked.connect(lambda: (copy.setText(_("Copy for bug report")), self.stack.setCurrentIndex(0)))
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
        version = sft.build_version()
        details = (f"Frame Tweaks {version}, Python {platform.python_version()}, {platform.machine()}\n\n"
                   + "".join(traceback.format_exception(kind, value, tb)))
        self.error_text.setPlainText(details.replace(str(Path.home()), "~"))
        self.stack.setCurrentWidget(self.error_page)
        sys.__excepthook__(kind, value, tb)

    def closeEvent(self, ev):
        if self.vr_buttons:
            self.vr_buttons.close()
        self.pool.shutdown(wait=False, cancel_futures=True)
        for proc in self.findChildren(QProcess):    # (stopped as the window goes: their finished
            proc.blockSignals(True)                 # would refresh it, with the pool shut down)
        super().closeEvent(ev)


SERVER = f"frame-tweaks-gui-{os.getuid()}"


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
    # One window: a second launch asks the running one to come forward and exits.
    probe = QLocalSocket()
    probe.connectToServer(SERVER)
    if probe.waitForConnected(300):
        probe.write(b"show")
        probe.waitForBytesWritten(300)
        return
    QLocalServer.removeServer(SERVER)
    server = QLocalServer()
    server.listen(SERVER)
    watch_for_hangs(Path.home() / ".local/state/frame-tweaks/logs")
    w = Window()
    server.newConnection.connect(lambda: (server.nextPendingConnection(), w.showNormal(),
                                          w.raise_(), w.activateWindow()))
    sys.excepthook = w.show_error
    app.aboutToQuit.connect(i18n.withdraw)          # (programs started later follow the keyboard again)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
