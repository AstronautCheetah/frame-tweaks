"""The installer window's ⚙ Preferences page: the language (every Frame Tweaks program follows it),
whether uninstalling a tweak removes its settings, and how this window behaves. The window's own
choices are kept in ~/.config/frame-tweaks/installer/window.json; the language in
~/.config/frame-tweaks/language; the uninstall choice in ~/.config/frame-tweaks/uninstall-settings."""
import html
import json

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

import i18n  # (lib/ is on the path)
from i18n import _, N_, ngettext
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
        # Settings kept earlier by tweaks no longer installed (./install.sh forget-settings).
        forget = QPushButton(_("Delete settings left by uninstalled tweaks…"))
        forget.clicked.connect(lambda: self.list_leftovers())
        rows.addWidget(forget, 0, Qt.AlignmentFlag.AlignLeft)
        self.leftovers = self.ask_box(rows, _("Delete them"), lambda: self.delete_leftovers())

        # Frame Tweaks itself (./install.sh uninstall-self, in a terminal, as installs are).
        rows.addWidget(self.heading(_("Uninstalling Frame Tweaks")))
        self.drop_tweaks = QCheckBox(_("Uninstall every tweak first"))
        self.drop_tweaks.setChecked(True)
        rows.addWidget(self.drop_tweaks)
        rows.addWidget(self.about(_("Off: they stay installed and keep working, but nothing updates them, and "
                                    "removing them later takes Frame Tweaks again.")))
        self.keep_apps = QCheckBox(_("Leave third-party apps installed"))
        self.keep_apps.setChecked(True)                 # (the safe choice: other projects' apps, your work in them)
        rows.addWidget(self.keep_apps)
        apps = ", ".join(sorted(c["app"] for c in sft.components() if c["app"]))
        self.keep_apps_about = self.about(_("Their tweaks stay installed, and the apps work as before: {apps}. "
                                            "Off: they're uninstalled too.").format(apps=apps))
        rows.addWidget(self.keep_apps_about)
        self.drop_tweaks.toggled.connect(lambda on: (self.keep_apps.setEnabled(on), self.keep_apps_about.setEnabled(on)))
        self.drop_settings = QCheckBox(_("Delete the settings too"))
        self.drop_settings.setChecked(sft.uninstall_settings() == "remove")
        rows.addWidget(self.drop_settings)
        rows.addWidget(self.about(_("Frame Tweaks' own, and those of the tweaks it uninstalls or uninstalled "
                                    "before. Off: they stay, for an install later.")))
        leave = QPushButton(_("Uninstall Frame Tweaks…"))
        leave.setObjectName("danger")
        leave.clicked.connect(lambda: self.ask_uninstall_self())
        rows.addWidget(leave, 0, Qt.AlignmentFlag.AlignLeft)
        self.leaving = self.ask_box(rows, _("Uninstall"), lambda: self.uninstall_self(), danger=True)

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

    def about(self, text):
        a = QLabel(html.escape(text))
        a.setObjectName("desc")
        a.setWordWrap(True)
        a.setContentsMargins(34, 0, 0, 6)
        return a

    def ask_box(self, rows, yes_label, on_yes, danger=False):
        """A question shown in place (hidden until asked): its text, Cancel and a yes button."""
        box = QWidget()
        box.setObjectName("ask")
        lay = QVBoxLayout(box)
        box.text = QLabel()
        box.text.setWordWrap(True)
        box.text.setTextFormat(Qt.TextFormat.PlainText)
        lay.addWidget(box.text)
        buttons = QHBoxLayout()
        no = QPushButton(_("Cancel"))
        no.clicked.connect(box.hide)
        box.yes = QPushButton(yes_label)
        box.yes.setObjectName("danger" if danger else "apply")
        box.yes.clicked.connect(on_yes)
        buttons.addWidget(no)
        buttons.addWidget(box.yes)
        buttons.addStretch(1)
        lay.addLayout(buttons)
        box.hide()
        rows.addWidget(box)
        return box

    def installed(self):
        """The tweaks that are (or may be) installed: any whose status isn't known yet counts."""
        state = getattr(self.window, "state", {}) or {}
        return {c["id"] for c in sft.components() if (state.get(c["id"]) or (0,))[0] != 1}

    def list_leftovers(self):
        self.found = sft.leftover_settings(self.installed())
        if not self.found:
            self.leftovers.hide()
            self.window.say(_("No settings left behind by uninstalled tweaks."), good=True)
            return
        self.leftovers.text.setText(_("Delete these settings? Their tweaks aren't installed.") + "\n\n" + "\n".join(
            f"{sft.translated(c)['title']}: {p}" for c, p in self.found))
        self.leftovers.show()

    def delete_leftovers(self):
        failed = []
        for _c, p in self.found:
            try:
                sft.remove_setting(p)
            except OSError:
                failed.append(p)
        self.leftovers.hide()
        if failed:
            self.window.say(_("Couldn't delete: {paths}").format(paths=", ".join(failed)))
        else:
            self.window.say(ngettext("Deleted {n} setting.", "Deleted {n} settings.", len(self.found)).format(
                n=len(self.found)), good=True)

    def ask_uninstall_self(self):
        lines = [_("Uninstall Frame Tweaks?"), ""]
        if not self.drop_tweaks.isChecked():
            lines.append(_("The tweaks stay installed."))
        elif self.keep_apps.isChecked():
            lines.append(_("Every tweak is uninstalled first, but those of third-party apps, which stay."))
        else:
            lines.append(_("Every tweak is uninstalled first, third-party apps too."))
        lines.append(_("Settings are deleted.") if self.drop_settings.isChecked() else _("Settings are kept."))
        lines.append(_("Its folder ({folder}) goes too, unless it holds work of yours (changes, your own packs); "
                       "this window closes, and a terminal shows each step.").format(folder=sft.REPO))
        self.leaving.text.setText("\n".join(lines))
        self.leaving.show()

    def uninstall_self(self):
        self.leaving.hide()
        self.window.uninstall_self(keep_tweaks=not self.drop_tweaks.isChecked(),
                                   settings="remove" if self.drop_settings.isChecked() else "keep",
                                   keep_apps=self.keep_apps.isChecked())

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
