"""The installer window's ⚙ Preferences page: the language (every Frame Tweaks program follows it),
whether uninstalling a tweak removes its settings, and how this window behaves. The window's own
choices are kept in ~/.config/frame-tweaks/installer/window.json; the language in
~/.config/frame-tweaks/language; whether updates take test releases in ~/.config/frame-tweaks/channel;
the uninstall choice in ~/.config/frame-tweaks/uninstall-settings; the look of installs in a
terminal in ~/.config/frame-tweaks/splash (lib/splash.py)."""

import os
import shlex

from PyQt6.QtCore import QProcess, Qt, QTimer
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QFrame, QHBoxLayout, QLabel, QPushButton, QRadioButton,
                             QScrollArea, QVBoxLayout, QWidget)

import i18n  # (lib/ is on the path)
import ftconf
from i18n import _, N_, ngettext
import sft
import splash

WINDOW = sft.CONF / "window.json"
# key: (default, label, explanation)
OPTIONS = {
    "haptics": (True, N_("Haptic ticks on this window's buttons (in VR)"),
                N_("A light tick when the laser moves onto a button, a firmer one on a click.")),
    "update_check": (True, N_("Look for a new Frame Tweaks release when this window opens"),
                     N_("Off: only when you press ⟳ Check for updates.")),
}


def window_prefs():
    saved = ftconf.read_json(WINDOW)
    return {k: saved.get(k, default) if isinstance(saved.get(k, default), bool) else default
            for k, (default, _label, _about) in OPTIONS.items()}


def set_window_pref(key, value):
    ftconf.update_json(WINDOW, {**window_prefs(), key: value})


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
        self.scroll = scroll = QScrollArea()
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

        rows.addWidget(self.heading(_("This window")))
        prefs = window_prefs()
        for key, (_default, label, about) in OPTIONS.items():
            box = QCheckBox(_(label))
            box.setChecked(prefs[key])
            box.toggled.connect(lambda on, k=key: self.set_pref(k, on))
            rows.addWidget(box)
            rows.addWidget(self.about(_(about)))

        # Updates: stable releases, or test releases too (sft.CHANNEL, as ./install.sh channel sets it).
        rows.addWidget(self.heading(_("Updates")))
        self.test_releases = QCheckBox(_("Get test releases too"))
        self.test_releases.setChecked(sft.release_channel() == "beta")
        self.test_releases.toggled.connect(lambda on: self.choose_channel(on))
        rows.addWidget(self.test_releases)
        rows.addWidget(self.about(_("Test releases (such as 0.7.0-rc.1) come before a release, for people who try "
                                    "things first: newer, less tested. Off: stable releases only.")))
        self.going_back = self.ask_box(rows, _("Go back now"), lambda: self.go_back_to_stable(), no_label=_("Stay on it"))

        # Installing in a terminal: Frame Tweaks' logo above the output (lib/splash.py, which reads
        # the choice for this window's installs and the terminal's alike).
        rows.addWidget(self.heading(_("Installing in a terminal")))
        rows.addWidget(self.note(_("While an install, removal or update runs in a terminal, as this window's do: "
                                   "Frame Tweaks' logo above the output, animated or still, or the output alone.")))
        grid = QHBoxLayout()
        grid.setSpacing(6)
        self.splash_buttons = {}
        for value, label in (("on", _("Animated")), ("still", _("Still")), ("off", _("Output only"))):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(value == splash.setting())
            b.setObjectName("choice")
            b.clicked.connect(lambda _on=False, v=value: self.choose_splash(v))
            grid.addWidget(b)
            self.splash_buttons[value] = b
        grid.addSpacing(12)
        show = QPushButton(_("Show me"))
        show.clicked.connect(lambda: self.show_splash())
        grid.addWidget(show)
        grid.addStretch(1)
        rows.addLayout(grid)
        rows.addWidget(self.about(_("KDE's animation speed set to instant (System Settings) keeps it still too.")))

        # (below a line: what removes things)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separator")
        rows.addSpacing(10)
        rows.addWidget(line)

        # Uninstalling: what happens to a tweak's settings (lib/sft.py UNINSTALL_PREF, which
        # ./install.sh uninstall reads, so the terminal does the same).
        rows.addWidget(self.heading(_("Uninstalling a tweak")))
        rows.addWidget(self.note(_("When you uninstall a tweak, its settings can stay, so it's set up as before if "
                                   "you install it again, or be removed along with it.")))
        rows.addWidget(self.note(_("Removing settings also signs you out of Claude Desktop and deletes NordVPN's key "
                                   "(setting NordVPN up again then needs a new access token).")))
        rows.addWidget(self.note(_("Your own data is never removed: your dictation history, adb's pairing keys and "
                                   "Claude Code's ~/.claude folder stay either way.")))
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
        rows.addWidget(self.note(_("What happens to the tweaks:")))
        apps = ", ".join(sorted(c["app"] for c in sft.components() if c["app"]))
        self.tweaks_choice = {}
        group = QButtonGroup(self)
        for value, label, about in (
                ("keep-apps", _("Uninstall the tweaks, but keep third-party apps"),
                 _("These stay installed and keep working, with the tweaks that installed them: {apps}.").format(apps=apps)),
                ("all", _("Uninstall every tweak, third-party apps too"),
                 _("Homebrew itself is never removed: other programs may live in it.")),
                ("none", _("Leave every tweak installed"),
                 _("They keep working, but nothing updates them, and removing them later takes Frame Tweaks again."))):
            b = QRadioButton(label)
            b.setChecked(value == "keep-apps")                  # (the safe choice: other projects' apps stay)
            group.addButton(b)
            self.tweaks_choice[value] = b
            rows.addWidget(b)
            rows.addWidget(self.about(about))
        self.drop_settings = QCheckBox(_("Also delete the settings"))
        self.drop_settings.setChecked(sft.uninstall_settings() == "remove")
        rows.addWidget(self.drop_settings)
        rows.addWidget(self.about(_("Deletes Frame Tweaks' own settings and those of every tweak it removes, now or "
                                    "earlier. Tweaks that stay installed keep theirs. Off: all settings are kept, "
                                    "for a later install.")))
        leave = QPushButton(_("Uninstall Frame Tweaks…"))
        leave.setObjectName("danger")
        leave.clicked.connect(lambda: self.ask_uninstall_self())
        rows.addWidget(leave, 0, Qt.AlignmentFlag.AlignLeft)
        self.leaving = self.ask_box(rows, _("Uninstall"), lambda: self.uninstall_self(), danger=True)

        rows.addStretch(1)

    def about(self, text):
        """An option's explanation, under it (plain text: an apostrophe is an apostrophe)."""
        a = self.note(text)
        a.setContentsMargins(34, 0, 0, 6)
        return a

    @staticmethod
    def note(text):
        a = QLabel(text)
        a.setTextFormat(Qt.TextFormat.PlainText)
        a.setObjectName("desc")
        a.setWordWrap(True)
        return a

    def ask_box(self, rows, yes_label, on_yes, danger=False, no_label=None):
        """A question shown in place (hidden until asked): its text, Cancel (or no_label) and a yes button."""
        box = QWidget()
        box.setObjectName("ask")
        lay = QVBoxLayout(box)
        box.text = QLabel()
        box.text.setWordWrap(True)
        box.text.setTextFormat(Qt.TextFormat.PlainText)
        lay.addWidget(box.text)
        buttons = QHBoxLayout()
        no = QPushButton(no_label or _("Cancel"))
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

    def ask(self, box):
        """Show a question box and scroll it into view: it opens below its button, which may be at
        the bottom of the page (Uninstall Frame Tweaks…), so it was easy to miss. (Once the page
        has laid it out: its place isn't known until then.)"""
        box.show()
        QTimer.singleShot(0, lambda: self.scroll.ensureWidgetVisible(box, 0, 16))

    def installed(self):
        """The tweaks that are (or may be) installed: any whose status isn't known yet counts."""
        state = getattr(self.window, "state", {}) or {}
        return {c["id"] for c in sft.components()                 # (1, and 4: uninstalled, until SteamVR restarts)
                if (state.get(c["id"]) or (0,))[0] not in (1, 4)}

    def list_leftovers(self):
        self.found = sft.leftover_settings(self.installed())
        if not self.found:
            self.leftovers.hide()
            self.window.say(_("No settings left behind by uninstalled tweaks."), good=True)
            return
        self.leftovers.text.setText(_("Delete these settings? Their tweaks aren't installed.") + "\n\n" + "\n".join(
            f"{sft.translated(c)['title']}: {p}" for c, p in self.found))
        self.ask(self.leftovers)

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
        choice = next(v for v, b in self.tweaks_choice.items() if b.isChecked())
        lines.append({"keep-apps": _("The tweaks are uninstalled first; third-party apps stay."),
                      "all": _("Every tweak is uninstalled first, third-party apps too."),
                      "none": _("The tweaks stay installed.")}[choice])
        lines.append(_("Settings are deleted.") if self.drop_settings.isChecked() else _("Settings are kept."))
        lines.append(_("Its folder ({folder}) goes too, unless it holds work of yours (changes, your own packs); "
                       "this window closes, and a terminal shows each step.").format(folder=sft.REPO))
        self.leaving.text.setText("\n".join(lines))
        self.ask(self.leaving)

    def uninstall_self(self):
        self.leaving.hide()
        self.window.uninstall_self(keep_tweaks=self.tweaks_choice["none"].isChecked(),
                                   settings="remove" if self.drop_settings.isChecked() else "keep",
                                   keep_apps=not self.tweaks_choice["all"].isChecked())

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

    def choose_splash(self, value):
        splash.set_setting(value)
        for v, b in self.splash_buttons.items():
            b.setChecked(v == value)
        self.window.say(_("Saved."), good=True)

    def show_splash(self):
        """A pretend install in a terminal (lib/splash.py --demo), as the choice has it."""
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would show: lib/splash.py --demo")
            return
        script = (f"python3 {shlex.quote(str(sft.REPO / 'lib/splash.py'))} --demo; echo; "
                  f"read -rsn1 -p {shlex.quote(_('Press any key to close'))}")
        QProcess.startDetached("konsole", ["--separate", "-e", "bash", "-c", script])

    def choose_channel(self, on):
        sft.set_release_channel("beta" if on else "stable")
        self.window.channel_changed()
        current = sft.current_release()
        if on:
            self.going_back.hide()
            self.window.say(_("Saved. ⟳ Check for updates finds test releases too."), good=True)
        elif "-" in current:                            # on a test release: back now, or with the next release
            self.going_back.text.setText(_("You're on {version}, a test release. Stay on it until the next stable "
                                           "release is out, or go back to the newest stable release now?").format(
                                               version=current))
            self.ask(self.going_back)
        else:
            self.window.say(_("Saved."), good=True)

    def go_back_to_stable(self):
        self.going_back.hide()
        self.window.run_update(None, to="stable")

    def set_pref(self, key, on):
        set_window_pref(key, on)
        self.window.prefs[key] = on
        self.window.say(_("Saved."), good=True)
