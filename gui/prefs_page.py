"""The installer window's ⚙ Preferences page: the language (every Frame Tweaks program follows it),
whether uninstalling a tweak removes its settings, and how this window behaves. The window's own
choices are kept in ~/.config/frame-tweaks/installer/window.json; the language in
~/.config/frame-tweaks/language; the uninstall choice in ~/.config/frame-tweaks/uninstall-settings."""
import html
import json

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

import i18n  # (lib/ is on the path)
from i18n import _, N_
import sft

WINDOW = sft.CONF / "window.json"
# key: (default, label, explanation)
OPTIONS = {
    "haptics": (True, N_("Haptic ticks on this window's buttons (in VR)"),
                N_("A light tick when the laser moves onto a button, a firmer one on a click.")),
    "controller": (True, N_("Controller buttons in VR"),
                   N_("While the laser is on this window: B goes back, Y to the top, A ticks the row it points at, "
                      "the left D-pad moves through the rows. Takes effect when the window opens again.")),
    "update_check": (True, N_("Look for a new Frame Tweaks release when this window opens"),
                     N_("Off: only when you press ⟳ Check for updates.")),
}


def window_prefs():
    try:
        saved = json.loads(WINDOW.read_text())
    except (OSError, ValueError):
        saved = {}
    return {k: saved.get(k, default) if isinstance(saved.get(k, default), bool) else default
            for k, (default, _label, _about) in OPTIONS.items()}


def set_window_pref(key, value):
    prefs = window_prefs()
    prefs[key] = value
    WINDOW.parent.mkdir(parents=True, exist_ok=True)
    WINDOW.write_text(json.dumps(prefs, indent=1) + "\n")


class Preferences(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        back = QPushButton(_("← Back"))
        back.clicked.connect(window.go_back)
        head.addWidget(back)
        title = QLabel(_("Preferences"))
        title.setObjectName("title")
        head.addWidget(title, 1)
        lay.addLayout(head)
        body = QWidget()
        rows = QVBoxLayout(body)
        rows.setSpacing(10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(body)
        lay.addWidget(scroll, 1)

        # Language: follow the keyboard, or one chosen for every Frame Tweaks program.
        rows.addWidget(self.heading(_("Language")))
        note = QLabel(_("For this window, Arrow Pad, Screen snip, the menu entries and the VR panels. "
                        "Following the keyboard: Steam's VR keyboard in VR, KDE's layout in desktop mode; "
                        "a QWERTY or English layout keeps the system's language."))
        note.setObjectName("desc")
        note.setWordWrap(True)
        rows.addWidget(note)
        chosen = i18n.preference()
        names = dict(i18n.available())
        now = names.get(i18n.CATALOGUE.language or "en", i18n.CATALOGUE.language)
        choices = [("keyboard", _("Follow the keyboard (now: {language})").format(language=now))] + i18n.available()
        grid = QHBoxLayout()
        grid.setSpacing(6)
        for value, label in choices:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(value == chosen or (value == "keyboard" and chosen not in names))
            b.setObjectName("choice")
            b.clicked.connect(lambda _on=False, v=value: self.choose_language(v))
            grid.addWidget(b)
        grid.addStretch(1)
        rows.addLayout(grid)

        # Uninstalling: what happens to a tweak's settings (lib/sft.py UNINSTALL_PREF, which
        # ./install.sh uninstall reads, so the terminal does the same).
        rows.addWidget(self.heading(_("Uninstalling a tweak")))
        note = QLabel(_("Its settings: kept, so it's set up as before if you install it again, or removed with it. "
                        "Removing them also signs you out of Claude Desktop, takes VSCodium's extensions, and "
                        "NordVPN's key (setting it up again takes a new access token). Data stays either way: "
                        "the dictation history, adb's pairing keys, Claude Code's ~/.claude."))
        note.setObjectName("desc")
        note.setWordWrap(True)
        rows.addWidget(note)
        grid = QHBoxLayout()
        grid.setSpacing(6)
        self.uninstall_buttons = {}
        for value, label in (("keep", _("Keep its settings")), ("remove", _("Remove its settings too"))):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(value == sft.uninstall_settings())
            b.setObjectName("choice")
            b.clicked.connect(lambda _on=False, v=value: self.choose_uninstall(v))
            grid.addWidget(b)
            self.uninstall_buttons[value] = b
        grid.addStretch(1)
        rows.addLayout(grid)

        rows.addWidget(self.heading(_("This window")))
        prefs = window_prefs()
        for key, (_default, label, about) in OPTIONS.items():
            box = QCheckBox(_(label))
            box.setChecked(prefs[key])
            box.toggled.connect(lambda on, k=key: self.set_pref(k, on))
            rows.addWidget(box)
            text = QLabel(html.escape(_(about)))
            text.setObjectName("desc")
            text.setWordWrap(True)
            text.setContentsMargins(34, 0, 0, 6)
            rows.addWidget(text)
        rows.addStretch(1)

    def heading(self, text):
        h = QLabel(text)
        h.setObjectName("name")
        h.setContentsMargins(0, 8, 0, 0)
        return h

    def choose_language(self, value):
        i18n.set_preference(value)
        self.window.close_details()
        self.window.check_language()                    # (back on the list: it changes at once)

    def choose_uninstall(self, value):
        sft.set_uninstall_settings(value)
        for v, b in self.uninstall_buttons.items():
            b.setChecked(v == value)
        self.window.say(_("Saved."), good=True)

    def set_pref(self, key, on):
        set_window_pref(key, on)
        self.window.prefs[key] = on
        self.window.say(_("Saved."), good=True)
