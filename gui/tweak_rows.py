"""The installer window's list rows: a category's header (fold, tick all, hide), a tweak's row
(the window fills in its widgets: Window.rebuild), the last row's call to help, and the icons
they show."""
from pathlib import Path

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QCursor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QPushButton, QStyle, QStyleOptionButton,
                             QWidget)

from sft import component  # (lib/ is on the path)
from i18n import _  # (translations: locale/README.md)
from wallet_page import FLATPAK_ICONS

REPO = Path(__file__).resolve().parent.parent
BREEZE = Path("/usr/share/icons/breeze-dark")


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


def box_icon(ticked, window, size=22):
    """A row's checkbox as a picture, ticked or not, drawn as the window draws its boxes (a box of
    its own, so with its style sheet): the category's Tick all and Untick all buttons."""
    ratio = QApplication.instance().devicePixelRatio() if QApplication.instance() else 1.0
    pm = QPixmap(round(size * max(ratio, 2.0)), round(size * max(ratio, 2.0)))   # (sharp when scaled up in VR)
    pm.setDevicePixelRatio(max(ratio, 2.0))
    pm.fill(Qt.GlobalColor.transparent)
    box = QCheckBox(window)
    box.hide()
    box.ensurePolished()
    opt = QStyleOptionButton()
    opt.initFrom(box)
    opt.rect = QRect(0, 0, size, size)
    opt.state |= QStyle.StateFlag.State_Enabled | (QStyle.StateFlag.State_On if ticked else QStyle.StateFlag.State_Off)
    painter = QPainter(pm)
    box.style().drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorCheckBox, opt, painter, box)
    painter.end()
    box.deleteLater()
    return QIcon(pm)


class CategoryHeader(QWidget):
    """▾/▸ CATEGORY (n) ☑ ☐: click it (or the empty part of the header) to collapse or expand
    (remembered); its two boxes tick or untick every tweak in it; Hide/Unhide on the right."""

    def __init__(self, window, category, count, collapsed, hidden, key=None, foldable=True):
        super().__init__()
        key = key or category                           # (the English name: what's remembered)
        self.toggle_collapsed = lambda: window.toggle_collapsed(key)
        self.setObjectName("cathead")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 4, 0)
        arrow = "▶" if collapsed else "▼"
        toggle = QPushButton(f"{arrow}  {category.upper().replace('&', '&&')}  ({count})"
                             + ("   · " + _("hidden") if hidden else ""))
        toggle.setObjectName("cattoggle")
        toggle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        toggle.setToolTip(_("Expand") if collapsed else _("Collapse"))
        toggle.clicked.connect(self.toggle_collapsed)
        # (not while searching: every category is shown unfolded then, whatever's saved, and
        # folding there would save the opposite of what's seen; Window.toggle_collapsed)
        toggle.setEnabled(foldable)
        lay.addWidget(toggle)
        for ticked, tip in ((True, _("Tick every tweak in this category")),
                            (False, _("Untick every tweak in this category (installed ones are removed when you "
                                      "apply the changes)"))):
            b = QPushButton()
            b.setObjectName("cattick")
            b.setIcon(box_icon(ticked, window))
            b.setIconSize(QSize(22, 22))
            b.setToolTip(tip)
            b.setAccessibleName(tip)
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.clicked.connect(lambda _c=False, on=ticked: window.tick_category(key, on))
            lay.addWidget(b)
        lay.addStretch(1)
        hide = QPushButton(_("Unhide category") if hidden else _("Hide category"))
        hide.setObjectName("cathide")
        hide.setToolTip(_("Show this category again") if hidden else
                        _("Hide the whole category from the list (doesn't remove anything)"))
        hide.clicked.connect(lambda: window.toggle_category_hidden(key))
        lay.addWidget(hide)

    def mouseReleaseEvent(self, ev):
        """The empty part of the header folds it too, as the whole header did."""
        if ev.button() == Qt.MouseButton.LeftButton:
            self.toggle_collapsed()


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


# The list's last row, under every group: not a tweak (nothing to install), the ways to help
# (docs/contribute.md). Built here, not in a pack, so install.sh, status and the tables
# of tweaks (docs/tweaks.md) never see it.
CONTRIBUTE = {"id": "_contribute", "icon": "system-users"}


class ContributeRow(Row):
    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.window.show_contribute()
