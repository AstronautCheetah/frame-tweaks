"""The installer window in VR (vrbuttons.py): haptic ticks as the laser crosses a button, and the
controller's buttons (B back, Y to the top, A ticks the row, the left D-pad through the rows) while
the laser is on the window. A part of Window (a mixin: its methods use the window's rows and
stack); Window.__init__ starts it."""
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QAbstractButton, QApplication

from tweak_rows import ContributeRow, Row


class ControllerInput:
    def eventFilter(self, obj, ev):
        """In VR: a haptic tick when the laser moves onto a button or tick box, a firmer pulse
        when it's clicked (vrbuttons.py), as on Arrow Pad."""
        t = ev.type()
        if t in (QEvent.Type.Enter, QEvent.Type.MouseButtonPress) and isinstance(obj, QAbstractButton) \
                and obj.isEnabled() and obj.isVisible() and self.prefs["haptics"]:
            self.vr_buttons.haptic("hover" if t == QEvent.Type.Enter else "press")
        # (SteamVR also sends the D-pad as an arrow key, which would scroll as well as move the
        # highlight: dropped just after a D-pad press the window handled.)
        if t == QEvent.Type.KeyPress and ev.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down) \
                and self.vr_buttons.recent_dpad():
            return True
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
