"""Tooltips shown twice as long as Qt's own, in every Frame Tweaks window (the installer window,
Arrow Pad, Screen snip, the NordVPN tray): in VR, reading takes longer and the laser wobbles off the
widget. Qt shows a tooltip for 10 s plus 40 ms for each character past 100 (qtooltip.cpp); a widget
with a duration of its own (setToolTipDuration) keeps it. Qt waits for the pointer to be still for
its usual time (SH_ToolTip_WakeUpDelay, 700 ms) and starts that wait again at every move, so a
laser's wobble put a tooltip off for seconds: moves within JITTER_PX of where the pointer settled
don't start it again (a timer of our own; 150 ms instead of Qt's time came too soon, tried in VR).

    from tooltips import longer_tooltips
    longer_tooltips(app)            # once, after QApplication()
"""
from PyQt6 import sip
from PyQt6.QtCore import QEvent, QObject, QTimer
from PyQt6.QtGui import QHelpEvent
from PyQt6.QtWidgets import QApplication, QStyle

FACTOR = 2
JITTER_PX = 8                      # (a laser's wobble at arm's length: a few pixels)
AUTO = "ft_tip_auto"               # (set on the widgets whose duration this sets: recomputed per text)


def qt_default_ms(text):
    """How long Qt shows a tooltip with this text when the widget doesn't say."""
    return 10000 + 40 * max(0, len(text) - 100)


class _Longer(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.anchor, self.widget = None, None
        self.timer = QTimer(self, singleShot=True, interval=wake_ms(), timeout=self.wake)

    def moved(self, pos):
        """The pointer at pos (global): the wait starts again only past JITTER_PX, or over another widget."""
        w = QApplication.widgetAt(pos)
        if w is not self.widget or self.anchor is None or (pos - self.anchor).manhattanLength() > JITTER_PX:
            self.widget, self.anchor = w, pos
            if w is not None:
                self.timer.start()

    def wake(self):
        w = self.widget
        if w is None or sip.isdeleted(w) or not w.isVisible():
            return
        # (as Qt's own: a ToolTip event, which goes up to the parents until one has a tooltip)
        QApplication.sendEvent(w, QHelpEvent(QEvent.Type.ToolTip, w.mapFromGlobal(self.anchor), self.anchor))

    def eventFilter(self, obj, event):
        t = event.type()
        # (a window's moves: Qt hands a widget without mouse tracking none of its own)
        if t == QEvent.Type.MouseMove and obj.isWindowType() and not event.buttons():
            self.moved(event.globalPosition().toPoint())
        elif t in (QEvent.Type.MouseButtonPress, QEvent.Type.Wheel, QEvent.Type.KeyPress, QEvent.Type.Leave) \
                and obj.isWindowType():
            self.timer.stop()
            self.anchor = None
        if t == QEvent.Type.ToolTip and hasattr(obj, "toolTipDuration"):
            if obj.property(AUTO) or obj.toolTipDuration() < 0:
                obj.setProperty(AUTO, True)
                obj.setToolTipDuration(FACTOR * qt_default_ms(obj.toolTip()))
        return False                # (Qt then shows it, for that long)


def wake_ms():
    """Qt's own wait before a tooltip (its style's; 700 ms)."""
    return QApplication.style().styleHint(QStyle.StyleHint.SH_ToolTip_WakeUpDelay) or 700


def longer_tooltips(app):
    """Install it on app (QApplication): tooltips steadier and longer. Returns the filter (keep it,
    or app keeps it as its child)."""
    f = _Longer(app)
    app.installEventFilter(f)
    return f
