"""READMEs and links as the installer window shows them: Markdown made readable by Qt's reader
(GitHub-style HTML, relative links, pictures), shown in a page or whole within one, zoom, a 📋 after
each link, and what clicking a link does (lib/browser.py: the session the browser runs in)."""
import html
import posixpath
import re
import urllib.parse

from PyQt6 import sip
from PyQt6.QtCore import QEvent, QObject, QPoint, Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QFontInfo, QImage
from PyQt6.QtWidgets import QAbstractSlider, QApplication, QScrollArea, QTextBrowser

import browser  # (lib/ is on the path)
import link_tip
from i18n import _  # (translations: locale/README.md)

GITHUB = "https://github.com/AstronautCheetah/frame-tweaks/tree/main"


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
