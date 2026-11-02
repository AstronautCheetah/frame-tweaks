#!/usr/bin/env python3
"""For maintainers, on a Frame: a window that shows which Steam Frame buttons it sees pressed, the
way Frame Tweaks reads them: the controllers' buttons from their parts in the controller's model
(lib/vrkit.py ButtonReader, d-pad directions included), the headset's Aux key from Linux
(gpio-keys, KEY_SELECT). A held button turns red once it counts as a long press, and the history
also shows what the window itself gets from SteamVR's laser mouse. Use it to check a button
before binding something to it, or after a SteamOS or SteamVR update.

  DISPLAY=:0 ~/.local/share/arrowpad/venv/bin/python dev/button-test.py     (over SSH, in VR)

It needs PyQt6 and the openvr module (Arrow Pad's venv has both), SteamVR running, and closes by
itself after DURATION seconds (180); LONG sets what counts as long (0.6 s, Dictation's default).
The system buttons aren't shown: SteamVR keeps them."""
import glob, os, struct, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from PyQt6.QtCore import QEvent, QObject, QTimer, Qt
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget
LONG = float(os.environ.get("LONG", "0.6"))     # (Dictation's default hold)
RED, NORMAL = "#ff4d4d", "#e8e8e8"
import openvr as vr
import vrkit
NAMES = [("left", "button_view", "Left View"), ("left", "dpad_up", "Left D-pad up"), ("left", "dpad_down", "Left D-pad down"),
         ("left", "dpad_left", "Left D-pad left"), ("left", "dpad_right", "Left D-pad right"), ("left", "bumper", "Left bumper"),
         ("left", "trigger", "Left trigger"), ("left", "button_grip", "Left grip"), ("left", "thumbstick", "Left stick click"),
         ("right", "button_a", "Right A"), ("right", "button_b", "Right B"), ("right", "button_x", "Right X"),
         ("right", "button_y", "Right Y"), ("right", "button_menu", "Right Menu"), ("right", "bumper", "Right bumper"),
         ("right", "trigger", "Right trigger"), ("right", "button_grip", "Right grip"), ("right", "thumbstick", "Right stick click")]
vr.init(vr.VRApplication_Overlay)
readers = [(label, vrkit.ButtonReader(vr, hand, part)) for hand, part, label in NAMES]
aux = None
for p in glob.glob("/sys/class/input/event*"):
    if open(p + "/device/name").read().strip() == "gpio-keys":
        aux = os.open("/dev/input/" + os.path.basename(p), os.O_RDONLY | os.O_NONBLOCK)
aux_down = False
app = QApplication(sys.argv)
w = QWidget(); w.setWindowTitle("Button test (Frame Tweaks)"); w.resize(1000, 620)
w.setStyleSheet("background:#1e2227;")
lay = QVBoxLayout(w)
title = QLabel("Steam Frame button test"); tf = title.font(); tf.setPointSize(22); tf.setBold(True); title.setFont(tf)
title.setStyleSheet(f"color:{NORMAL}"); title.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.addWidget(title)
sub = QLabel("Which buttons this window sees pressed: the controllers' parts through SteamVR, the headset's Aux key through Linux.")
sub.setStyleSheet("color:#9aa6b2"); sub.setAlignment(Qt.AlignmentFlag.AlignCenter); sub.setWordWrap(True); lay.addWidget(sub)
now_lbl = QLabel("Press a button"); now_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
f = now_lbl.font(); f.setPointSize(30); f.setBold(True); now_lbl.setFont(f); now_lbl.setWordWrap(True)
hist_lbl = QLabel(""); hf = hist_lbl.font(); hf.setPointSize(14); hist_lbl.setFont(hf); hist_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
now_lbl.setTextFormat(Qt.TextFormat.RichText); hist_lbl.setTextFormat(Qt.TextFormat.RichText)
legend = QLabel(f"<span style='color:{NORMAL}'>■</span> short press &nbsp;&nbsp; <span style='color:{RED}'>■</span> long press (held {LONG:g} s or more)")
lf = legend.font(); lf.setPointSize(13); legend.setFont(lf); legend.setTextFormat(Qt.TextFormat.RichText)
lay.addWidget(now_lbl, 2); lay.addWidget(hist_lbl, 3)
bottom = QHBoxLayout(); bottom.addStretch(1); bottom.addWidget(legend); lay.addLayout(bottom)
history, last, t0, since = [], set(), time.time(), {}
def note(text, color=NORMAL):
    line = f"{time.time()-t0:5.1f}s  {text}"
    history.insert(0, f"<span style='color:{color}'>{line}</span>"); del history[10:]
    hist_lbl.setText("<br>".join(history)); print(line, flush=True)
def poll():
    global last, aux_down
    if aux is not None:
        try:
            data = os.read(aux, 24 * 16)
            for i in range(0, len(data), 24):
                _, _, typ, code, val = struct.unpack("qqHHi", data[i:i + 24])
                if typ == 1 and code == 353 and val in (0, 1):
                    aux_down = val == 1
        except BlockingIOError:
            pass
    down = {label for label, r in readers if r.pressed()}
    if aux_down:
        down.add("Headset Aux")
    t = time.monotonic()
    for b in sorted(down - last):
        since[b] = t; note(f"pressed  {b}")
    for b in sorted(last - down):
        held = t - since.pop(b, t)
        note(f"released {b} after {held:.2f} s ({'long' if held >= LONG else 'short'})", RED if held >= LONG else NORMAL)
    last = down
    parts = [f"<span style='color:{RED if t - since[b] >= LONG else NORMAL}'>{b}</span>" for b in sorted(down)]
    now_lbl.setText(", ".join(parts) if parts else f"<span style='color:{NORMAL}'>(nothing pressed)</span>")
KINDS = {QEvent.Type.MouseButtonPress: "window got mouse down", QEvent.Type.KeyPress: "window got key"}
class EF(QObject):
    def eventFilter(self, o, e):
        k = KINDS.get(e.type())
        if k and o.isWidgetType() and o.window() is w:
            note(f"{k}: " + (e.button().name if "mouse" in k else Qt.Key(e.key()).name))
        return False
ef = EF(); app.installEventFilter(ef)
QTimer(w, interval=16, timeout=poll).start()
w.show()
QTimer.singleShot(int(float(os.environ.get("DURATION", "180")) * 1000), app.quit)
app.exec(); vr.shutdown()
