"""The installer window's pages about one thing: a tweak's details (what it is, why it's here, who
made it, its status, a known issue, its README) and a README of Frame Tweaks' own (📖 README,
Get involved)."""
import html
import re
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

import manifest  # (lib/ is on the path)
import sft
from i18n import _  # (translations: locale/README.md)
from readme_view import GITHUB, full_height, link_label, md_text, readme_browser, with_copy
from tweak_rows import row_icon
from window_logic import KNOWN_ISSUES, status_text, version_tuple

REPO = Path(__file__).resolve().parent.parent


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
        # The header: Back, icon and title on the left; the row's buttons (Run, ⚙, ↻, Hide) in the
        # middle, the grid's outer columns stretching alike to centre them.
        top = QWidget()
        top.setObjectName("detailhead")
        head = QGridLayout(top)
        head.setContentsMargins(0, 0, 0, 0)
        left = QHBoxLayout()
        back = QPushButton(_("← Back"))
        back.clicked.connect(window.leave_details)
        left.addWidget(back)
        icon = QLabel()
        icon.setPixmap(row_icon(comp["id"]).pixmap(56, 56))
        left.addWidget(icon)
        title = QLabel(f"{html.escape(comp['title'], quote=False)}  <span style='color:#6b7783;font-size:14px'>"
                       f"{html.escape(comp['category'])}</span>")
        title.setObjectName("title")
        title.setWordWrap(True)
        left.addWidget(title, 1)
        head.addLayout(left, 0, 0)
        buttons = window.details_buttons(comp)
        self.buttons = buttons if isinstance(buttons, dict) else {}     # (a test's stand-in window: none)
        self.sized = False
        middle = QHBoxLayout()
        for b in self.buttons.get("all", []):
            middle.addWidget(b)
        head.addLayout(middle, 0, 1)
        head.setColumnStretch(0, 1)
        head.setColumnStretch(2, 1)
        lay.addWidget(top)

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

    def showEvent(self, event):
        """The header's buttons sized as the row's (even_buttons), now the window's style sheet has
        reached them: measured before, ⚙ and ↻ came out the size of their 14 px text."""
        super().showEvent(event)
        if self.buttons and not self.sized:
            self.sized = True
            self.window.even_buttons(self.buttons["texts"], self.buttons["icons"])

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
