"""Tooltips shown twice as long as Qt's own, in every Frame Tweaks window (the installer window,
Arrow Pad, Screen snip, the NordVPN tray): in VR, reading takes longer and the laser wobbles off the
widget. Qt shows a tooltip for 10 s plus 40 ms for each character past 100 (qtooltip.cpp); a widget
with a duration of its own (setToolTipDuration) keeps it. They also come sooner: Qt waits 700 ms
with the pointer still (SH_ToolTip_WakeUpDelay), and every move starts that wait again, so the
laser's wobble put a tooltip off for seconds; WAKE_MS instead.

    from tooltips import longer_tooltips
    longer_tooltips(app)            # once, after QApplication()
"""
from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtWidgets import QProxyStyle, QStyle

FACTOR = 2
WAKE_MS = 150                      # (Qt's: 700)
AUTO = "ft_tip_auto"               # (set on the widgets whose duration this sets: recomputed per text)


def qt_default_ms(text):
    """How long Qt shows a tooltip with this text when the widget doesn't say."""
    return 10000 + 40 * max(0, len(text) - 100)


class _Longer(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.ToolTip and hasattr(obj, "toolTipDuration"):
            if obj.property(AUTO) or obj.toolTipDuration() < 0:
                obj.setProperty(AUTO, True)
                obj.setToolTipDuration(FACTOR * qt_default_ms(obj.toolTip()))
        return False                # (Qt then shows it, for that long)


class _Sooner(QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, data=None):
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return WAKE_MS
        return super().styleHint(hint, option, widget, data)


def longer_tooltips(app):
    """Install it on app (QApplication), before its windows: tooltips sooner and longer. Returns
    the filter (keep it, or app keeps it as its child)."""
    if not isinstance(app.style(), _Sooner):
        app.setStyle(_Sooner(app.style().name()))      # (the same look: Qt's style of that name, wrapped)
    f = _Longer(app)
    app.installEventFilter(f)
    return f
