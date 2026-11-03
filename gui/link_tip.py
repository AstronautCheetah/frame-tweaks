"""The pop-up by the pointer after a click on a link (or Open folder): what it did ("Opening in
Firefox in desktop mode", "Link copied"). Twice a tooltip's size and twice its time: Qt's own was
small, and gone before you'd read it, in VR especially.

Not a QToolTip: Qt hides a tooltip as soon as its window loses the focus, and a link that opens in
Firefox takes the focus, so "Opened in Firefox (VR)" vanished within a second, whatever time it was
given. This is a label of its own, in a tooltip-like window that never takes the focus and goes
only when its time is up, or when you click it."""
import html

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QLabel, QToolTip

SCALE = 2
# (the window's QToolTip look, STYLE in frame-tweaks-gui.py; a QLabel doesn't take that selector)
LOOK = ("color: #e8ecf0; background: #1f2731; border: 1px solid #355b7a; border-radius: 6px; "
        "padding: 8px 10px;")
_shown = None                     # the pop-up up now (one at a time: a new one replaces it)


def qt_time(text):
    """How long Qt shows a tooltip with this text (its default: 10 s, longer for long ones)."""
    return 10000 + 40 * max(0, len(text) - 100)


class _Tip(QLabel):
    def mousePressEvent(self, _event):         # (a click puts it away)
        self.close()


def show(text):
    """The pop-up with text, by the pointer, for twice Qt's tooltip time; returns it."""
    global _shown
    if _shown is not None:
        _shown.close()
    font = QToolTip.font()
    size = (f"{font.pointSizeF() * SCALE:g}pt" if font.pointSizeF() > 0
            else f"{max(font.pixelSize(), 12) * SCALE}px")
    tip = _Tip(f"<span style='font-size:{size}'>{html.escape(text)}</span>")
    tip.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
    tip.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    tip.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    tip.setStyleSheet(LOOK)
    tip.setTextFormat(Qt.TextFormat.RichText)
    tip.adjustSize()
    tip.move(QCursor.pos() + QPoint(16, 16))
    tip.show()
    tip.time_ms = qt_time(text) * SCALE
    QTimer(tip, singleShot=True, interval=tip.time_ms, timeout=tip.close).start()     # (goes with the pop-up)
    _shown = tip
    tip.destroyed.connect(lambda *_: _forget(tip))
    return tip


def _forget(tip):
    global _shown
    if _shown is tip:
        _shown = None
