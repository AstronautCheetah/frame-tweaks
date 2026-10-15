"""The installer window's Packs page: the packs of tweaks it found (docs/mods.md), whether each is
in use, trusting or no longer using a user's pack, adding one from a link (and updating or
removing it), and what's wrong with any of them."""
import html
import subprocess
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QCursor, QDesktopServices
from PyQt6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QToolTip,
                             QVBoxLayout, QWidget)

import browser  # (lib/ is on the path)
from i18n import _, N_, ngettext  # (translations: locale/README.md)
import sft

EXAMPLE_LINK = "https://github.com/…/…"         # (an address, not text: the same in every language)
COMMUNITY = "https://github.com/AstronautCheetah/frame-tweaks/blob/main/docs/community-packs.md"
STATE = {"official": (N_("Comes with Frame Tweaks: in use"), "#5cc77a"),
         "off": (N_("Comes with Frame Tweaks: turned off, so its tweaks aren't listed"), "#9aa6b2"),
         "trusted": (N_("Trusted: its tweaks are listed"), "#5cc77a"),
         "untrusted": (N_("Not trusted yet: its tweaks aren't listed"), "#e0b33a"),
         "changed": (N_("Changed since you trusted it: not used until you trust it again"), "#e0b33a")}


class PackRow(QWidget):
    """A pack's row: clicking it (but its buttons or links) shows or hides its inventory."""

    def __init__(self, page, d):
        super().__init__()
        self.page, self.dir = page, d
        self.setObjectName("row")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.page.toggle_inventory(self.dir)


class Packs(QWidget):
    def __init__(self, window, follow_link=None, pool=None):
        super().__init__()
        self.window, self.follow = window, follow_link
        # (adding or updating a pack is a git clone or pull: off this thread, looked at 5 times a second)
        self.pool = pool or ThreadPoolExecutor(max_workers=1)
        self.job = None
        self.timer = QTimer(self, interval=200, timeout=self.collect)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        back = QPushButton(_("← Back"))
        back.clicked.connect(window.go_back)
        head.addWidget(back)
        title = QLabel(_("Packs"))
        title.setObjectName("title")
        head.addWidget(title, 1)
        folder = QPushButton(_("Open packs folder"))
        folder.setToolTip(str(sft.USER_PACKS))
        folder.clicked.connect(self.open_folder)
        head.addWidget(folder)
        lay.addLayout(head)
        about = QLabel(_(
            "Every tweak here comes from a <b>pack</b>: a folder of tweak folders, each described by its "
            "README.md. Frame Tweaks' own are in three official packs, Original, Integrations and 3rd "
            "Party, all in use unless you turn one off. To add more, add one from its link below, or put "
            "a pack's folder in <code>{folder}</code>; then trust it. "
            "<b>A pack's tweaks run as you</b>, with your files and passwords in reach: trust only packs "
            "from people you trust, and read what they do first. If a pack's files change, it waits "
            "until you trust it again. How to write one: docs/mods.md.").format(folder=html.escape(str(sft.USER_PACKS))))
        about.setWordWrap(True)
        about.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(about)
        add = QHBoxLayout()
        add.addWidget(QLabel(_("Add a pack from a link:")))
        self.link = QLineEdit()
        self.link.setPlaceholderText(EXAMPLE_LINK)
        self.link.returnPressed.connect(self.add)
        add.addWidget(self.link, 1)
        paste = QPushButton(_("Paste"))
        paste.setToolTip(_("Paste the link from the clipboard"))
        paste.clicked.connect(lambda: self.link.setText(QApplication.clipboard().text().strip()))
        add.addWidget(paste)
        self.add_button = QPushButton(_("Add"))
        self.add_button.setToolTip(_("Download the pack into your packs folder. Nothing of it runs until you trust it."))
        self.add_button.clicked.connect(self.add)
        add.addWidget(self.add_button)
        lay.addLayout(add)
        shared = QLabel(f"<a style='color:#7fb2e5' href='{COMMUNITY}'>" + html.escape(_("Packs others share")) + " ↗</a>")
        shared.setToolTip(_("Community packs: packs people shared, with their links"))
        shared.linkActivated.connect(self.open_link)
        lay.addWidget(shared)
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        self.notice.setTextFormat(Qt.TextFormat.PlainText)
        self.notice.hide()
        lay.addWidget(self.notice)
        self.body = QWidget()
        self.rows = QVBoxLayout(self.body)
        self.rows.setSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.body)
        lay.addWidget(scroll, 1)
        self.confirming = self.removing = None
        self.build()

    def build(self):
        while self.rows.count():
            w = self.rows.takeAt(0).widget()
            if w:
                w.hide()                                 # (gone now, not only once it's deleted)
                w.deleteLater()
        data = sft.load(refresh=True)
        used = {c["id"]: c for c in data["components"]}
        shown = self.open_packs()
        for p in data["packs"]:
            row = PackRow(self, p["dir"])
            g = QHBoxLayout(row)
            g.setContentsMargins(12, 10, 12, 10)
            text, colour = STATE[p["state"]]
            text = _(text)
            origin = sft.pack_origin(p["dir"]) if sft.removable(p) else None
            updates = getattr(self.window, "pack_updates", None)            # (Check for updates found these)
            newer = isinstance(updates, set) and p["dir"] in updates
            count = ngettext("%d tweak", "%d tweaks", len(p["tweaks"])) % len(p["tweaks"])
            inventory = (f"<br><span style='color:#7fb2e5'>▾ {count}</span>" + self.inventory(p, used)
                         if p["dir"] in shown else f"<br><span style='color:#7fb2e5'>▸ {count}</span>")
            info = QLabel(f"<b>{html.escape(p['label'])}</b>"
                          + (" <span style='color:#6b7783'>" + _("tweak pack provided by {author}").format(
                              author=html.escape(p["author"]))
                             + "</span>" if p["author"] else "")
                          + (f"<br>{html.escape(p['about'])}" if p["about"] else "")
                          + f"<br><span style='color:{colour}'>{text}</span>"
                          + ("<br><span style='color:#e0b33a'>" + _("A newer version is out where it came from: "
                                                                    "Update gets it.") + "</span>" if newer else "")
                          + f"<br><span style='color:#6b7783'>{html.escape(str(p['dir']))}</span>"
                          + ("<br>" + _("From {link}").format(link=(
                              f"<a style='color:#7fb2e5' href='{html.escape(origin)}'>{html.escape(origin)} ↗</a>"
                              if origin.startswith("https://") else html.escape(origin))) if origin else "")
                          + inventory)
            info.setWordWrap(True)
            info.setTextFormat(Qt.TextFormat.RichText)
            info.linkActivated.connect(self.open_link)
            g.addWidget(info, 1)
            if p["state"] in ("official", "off"):
                on = p["state"] == "off"
                b = QPushButton(_("Use") if on else _("Stop using"))
                b.setToolTip(_("Its tweaks come back to the list") if on else
                             _("Its tweaks leave the list; installed ones stay until you uninstall them"))
                b.clicked.connect(lambda _=False, d=p["dir"], on=on: self.use_official(d, on))
                g.addWidget(b)
            else:
                if p["state"] == "trusted":
                    b = QPushButton(_("Stop using"))
                    b.setToolTip(_("Its tweaks leave the list; installed ones stay until you uninstall them"))
                    b.clicked.connect(lambda _=False, d=p["dir"]: self.trust(d, False))
                elif self.confirming == p["dir"]:
                    b = QPushButton(_("Yes: it runs as me"))
                    b.setToolTip(_("Trust this pack's current files"))
                    b.clicked.connect(lambda _=False, d=p["dir"]: self.trust(d, True))
                else:
                    b = QPushButton(_("Trust…"))
                    b.clicked.connect(lambda _=False, d=p["dir"]: self.confirm(d))
                g.addWidget(b)
                if origin:
                    b = QPushButton(_("Update"))
                    if newer:
                        b.setObjectName("apply")
                    b.setToolTip(_("Get its newer version from where it was added; it waits until you trust it again"))
                    b.setEnabled(self.job is None)
                    b.clicked.connect(lambda _=False, p=p: self.update(p))
                    g.addWidget(b)
                if sft.removable(p):
                    if self.removing == p["dir"]:
                        b = QPushButton(_("Yes, delete it"))
                        b.setObjectName("danger")
                        b.clicked.connect(lambda _=False, p=p: self.remove(p))
                    else:
                        b = QPushButton(_("Remove…"))
                        b.setToolTip(_("Delete this pack from your packs folder"))
                        b.clicked.connect(lambda _=False, d=p["dir"]: self.ask_remove(d))
                    g.addWidget(b)
            self.rows.addWidget(row)
        if data["problems"]:
            probs = QLabel("<b>" + _("Problems") + "</b><br>" + "<br>".join(html.escape(x) for x in data["problems"]))
            probs.setWordWrap(True)
            probs.setTextFormat(Qt.TextFormat.RichText)
            probs.setStyleSheet("color: #e0b33a")
            self.rows.addWidget(probs)
        self.rows.addStretch(1)

    def confirm(self, d):
        self.confirming, self.removing = d, None
        self.build()

    def ask_remove(self, d):
        self.confirming, self.removing = None, d
        self.build()

    # ---- packs from a link (lib/sft.py add_pack, update_pack, remove_pack) ----
    def tell(self, text, good=False):
        self.notice.setText(text)
        self.notice.setStyleSheet(f"color: {'#5cc77a' if good else '#e0b33a'}")
        self.notice.show()

    def start(self, work, done, saying):
        """work() off this thread (a git clone or pull takes seconds); then done(its result)."""
        if self.job is not None:
            return
        self.job = (self.pool.submit(work), done)
        self.add_button.setEnabled(False)
        self.tell(saying, good=True)
        self.build()                                    # (its Update buttons dimmed meanwhile)
        self.timer.start()

    def collect(self):
        fut, done = self.job
        if not fut.done():
            return
        self.timer.stop()
        self.job = None
        self.add_button.setEnabled(True)
        try:
            result = fut.result()
        except sft.PackError as e:
            self.tell(str(e))
            self.build()
            return
        except Exception as e:                          # (whatever it is, said rather than lost)
            self.tell(_("That didn't work: {error}").format(error=e))
            self.build()
            return
        done(result)

    def add(self):
        link = self.link.text().strip()
        if not link:
            self.tell(_("Paste or type the link of a pack's git repository first."))
            return
        self.start(lambda: sft.add_pack(link), self.added, _("Adding the pack…"))

    def added(self, d):
        self.link.clear()
        p = next((x for x in sft.load()["packs"] if x["dir"] == d.resolve()), None)
        self.tell(_("Added {name}. It isn't used until you trust it: its tweaks would run as you. Read what they "
                    "do first (its link, or Open packs folder), then Trust… below.").format(
                        name=sft.plain(p["name"]) if p else d.name), good=True)
        self.build()

    def update(self, p):
        self.start(lambda: sft.update_pack(p["dir"]), lambda got: self.updated(p, got),
                   _("Updating {name}…").format(name=sft.plain(p["name"])))

    def updated(self, p, got):
        name = sft.plain(p["name"])
        updates = getattr(self.window, "pack_updates", None)
        if isinstance(updates, set) and p["dir"] in updates:   # (got it: the window's notice goes too)
            updates.discard(p["dir"])
            self.window.show_pack_updates()
        if not got["files"]:
            self.tell(_("{name} is up to date.").format(name=name), good=True)
        else:
            self.tell(ngettext("{name}: updated, {n} file changed.", "{name}: updated, {n} files changed.",
                               len(got["files"])).format(name=name, n=len(got["files"])) + " "
                      + _("It isn't used until you trust it again: read what changed first, then Trust… below.")
                      + "".join("\n• " + line for line in got["log"]))
            self.window.reload_tweaks()
        self.build()

    def remove(self, p):
        self.removing = None
        try:
            sft.remove_pack(p["dir"])
        except sft.PackError as e:
            self.tell(str(e))
            self.build()
            return
        self.tell(_("Removed {name}.").format(name=sft.plain(p["name"])), good=True)
        self.window.reload_tweaks()
        self.build()

    def open_packs(self):
        """The packs whose inventory is shown (kept by the window: the page is built anew each time)."""
        shown = getattr(self.window, "packs_open", None)
        if not isinstance(shown, set):
            shown = set()
            try:
                self.window.packs_open = shown
            except AttributeError:
                pass
        return shown

    def toggle_inventory(self, d):
        shown = self.open_packs()
        shown.symmetric_difference_update({d})
        self.build()

    def inventory(self, p, used):
        """Its tweaks, one a line: emoji, name (a link to its page while it's in the list), tags,
        summary, and whether it's installed. Read from their READMEs: nothing of the pack runs."""
        installed = set(sft.pack_installed(p))
        lines = []
        for t in p["tweaks"]:
            c, _probs = sft.read_tweak(p["dir"] / t)
            if not c:
                lines.append(f"{html.escape(t)} <span style='color:#e0b33a'>" + _("(its README can't be read)") + "</span>")
                continue
            c = sft.translated(c) if p["state"] in ("official", "off") else c
            mine = used.get(t) is not None and used[t]["pack_dir"] == p["dir"]
            name = html.escape(c["title"], quote=False)
            name = f"<a style='color:#7fb2e5' href='tweak:{html.escape(t)}'>{name}</a>" if mine else f"<b>{name}</b>"
            tags = (" 🧪" if c["experimental"] else "") + (" 🔗" if c["link"] else "") + (
                " <span style='color:#e0b33a'>sudo</span>" if c["sudo"] else "")
            other = used[t]["replaced"] if mine and used[t]["replaced"] else ""
            lines.append(f"{html.escape(c['emoji'])} {name}{tags} — {html.escape(c['desc'], quote=False)}"
                         + (" <i>" + _("(instead of {other}'s)").format(other=html.escape(other)) + "</i>" if other else "")
                         + (" <span style='color:#5cc77a'>✔ " + _("installed") + "</span>" if t in installed else ""))
        return "".join(f"<br>&nbsp;&nbsp;{line}" for line in lines) or "<br>&nbsp;&nbsp;" + _("none")

    def open_link(self, url):
        if url.startswith("tweak:"):                     # (a tweak of the inventory: its page; Back comes here)
            comp = next((c for c in sft.components() if c["id"] == url[len("tweak:"):]), None)
            if comp is not None:
                self.window.show_details(comp, back=self.window.show_packs)
            return
        if self.follow:
            self.follow(url)
        else:
            QDesktopServices.openUrl(QUrl(url))

    def trust(self, d, on):
        self.confirming = self.removing = None
        sft.set_trusted(d, on)
        self.window.reload_tweaks()
        self.build()

    def use_official(self, d, on):
        sft.set_official(d, on)
        self.window.reload_tweaks()
        self.build()

    def open_folder(self):
        sft.USER_PACKS.mkdir(parents=True, exist_ok=True)
        # The default file manager as desktop mode sets it, where it's running (lib/browser.py):
        # xdg-open from the VR session would pick Kate.
        note = browser.open_path(str(sft.USER_PACKS))
        if note:
            QToolTip.showText(QCursor.pos(), note)
        else:
            subprocess.Popen(["xdg-open", str(sft.USER_PACKS)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
