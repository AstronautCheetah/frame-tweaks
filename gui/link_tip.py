"""The pop-up by the pointer after a click on a link (or Open folder): what it did ("Opening in
Firefox in desktop mode", "Link copied"). Twice a tooltip's size and twice its time: Qt's own was
small, and gone before you'd read it, in VR especially."""
import html

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QToolTip

SCALE = 2


def qt_time(text):
    """How long Qt shows a tooltip with this text (its default: 10 s, longer for long ones)."""
    return 10000 + 40 * max(0, len(text) - 100)


def show(text):
    font = QToolTip.font()
    size = (f"{font.pointSizeF() * SCALE:g}pt" if font.pointSizeF() > 0
            else f"{max(font.pixelSize(), 12) * SCALE}px")
    QToolTip.showText(QCursor.pos(), f"<span style='font-size:{size}'>{html.escape(text)}</span>",
                      None, QRect(), qt_time(text) * SCALE)
