"""The installer window's Apply changes: what's ticked differently from what's installed, the
confirm page that says it by name first (with what those need, and which ask for the sudo
password), and the bar that sets a password for a user who has none. A part of Window (a mixin:
its methods use the window's rows, state and stack); what runs the changes is Window.run_changes."""
import html
import os
import shlex

from PyQt6.QtCore import QProcess, Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

import sft  # (lib/ is on the path)
from i18n import _  # (translations: locale/README.md)
from window_logic import GONE, close_prompt, in_terminal


class ApplyChanges:
    def make_confirm_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addStretch(1)
        text = QLabel()
        text.setObjectName("title")
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(text)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        no = QPushButton(_("Cancel"))
        no.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        yes = QPushButton()
        yes.setObjectName("apply")
        buttons.addWidget(no)
        buttons.addWidget(yes)
        buttons.addStretch(1)
        lay.addLayout(buttons)
        lay.addStretch(2)
        return page, text, yes

    # ---- apply --------------------------------------------------------------
    def pending_changes(self):
        """(install, remove): ticked but not installed, unticked but installed. Rows whose status
        isn't known yet don't count; a tweak with a warning is reinstalled with its ↻ button."""
        known = [c["id"] for c in self.rows if self.state.get(c["id"]) is not None]
        want = {cid: self.wanted.get(cid, self.state[cid][0] not in GONE) for cid in known}
        return ([cid for cid, on in want.items() if on and self.state[cid][0] in GONE],
                [cid for cid, on in want.items() if not on and self.state[cid][0] not in GONE])

    def update_apply(self):
        """Apply changes is dimmed while there's nothing to change."""
        button = getattr(self, "apply_button", None)
        if button is None:
            return
        add, remove = self.pending_changes()
        button.setEnabled(bool(add or remove))
        button.setToolTip((_("Install: %s") % ", ".join(add) if add else "") + ("; " if add and remove else "")
                          + (_("Remove: %s") % ", ".join(remove) if remove else "")
                          or _("Nothing to change: tick or untick a tweak first"))

    def apply(self):
        if self.futures:
            self.say(_("Still checking status; try again in a moment."))
            return
        # From what you ticked (self.wanted), so rows in collapsed or hidden categories count too.
        add, remove = self.pending_changes()
        if not add and not remove:
            self.say(_("Nothing to change."))
            return
        blocked = self.needs_password(add)
        if blocked:                  # (sudo can't work yet: set a password first, then Apply again)
            self.confirm(_("{tweaks} need your sudo password, and your user has none yet. Set one, then "
                           "Apply changes again.").format(tweaks=", ".join(blocked))
                         + "<br><br>" + self.changes_text(add, remove), _("Set a password…"), self.set_password)
            return
        self.confirm(self.changes_text(add, remove), _("Apply"), lambda: self.run_changes(add, remove))

    def needs_password(self, add):
        """The titles of the tweaks in add, and those they need, that would ask for the sudo
        password now, if your user has no password (empty when it has one, or none would ask)."""
        if sft.has_password():
            return []
        comps = {c["id"]: c for c in self.rows}
        installed = {cid for cid, st in self.state.items() if st[0] not in GONE}
        ids, queue = [], list(add)
        while queue:
            cid = queue.pop(0)
            if cid in comps and cid not in ids:
                ids.append(cid)
                queue += [d for d in comps[cid].get("deps", []) if d not in installed]
        return [comps[cid]["title"] for cid in ids if sft.sudo_note(comps[cid])]

    def make_password_bar(self):
        """While your user has no password (a new Frame's), a line saying the tweaks that ask for
        the sudo password can't install yet, with a button that sets one."""
        bar = QWidget()
        bar.setObjectName("passwordbar")
        bar.setStyleSheet("QWidget#passwordbar { background: #3a3020; border-radius: 6px; }")
        row = QHBoxLayout(bar)
        row.setContentsMargins(12, 8, 12, 8)
        text = QLabel("🔑 " + _("Your user has no password yet, so tweaks that ask for the sudo password (tagged "
                               "sudo) can't install. Set one first: you'll type it when they ask."))
        text.setWordWrap(True)
        row.addWidget(text, 1)
        b = QPushButton(_("Set a password…"))
        b.clicked.connect(self.set_password)
        row.addWidget(b)
        self.password_bar = bar
        bar.setVisible(not sft.has_password())
        return bar

    def set_password(self):
        """passwd in a terminal, with a word on what it asks; the bar goes once it's set."""
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):      # for tests: show the plan, change nothing
            print("would run: passwd")
            return
        intro = _("Choose a password for your user (sudo asks for it). Type it, press Enter, then type "
                  "it again: nothing shows as you type.")
        cmd = f"echo {shlex.quote(intro)}; echo; passwd; echo; read -rp {close_prompt()}"
        self.password_proc = QProcess(self)
        self.password_proc.finished.connect(lambda *_: self.password_checked())
        in_terminal(self.password_proc, cmd)

    def password_checked(self):
        has = sft.has_password()
        self.password_bar.setVisible(not has)
        self.say(_("Password set: the tweaks tagged sudo can install now.") if has
                 else _("No password yet: Set a password… again when you're ready."))

    def changes_text(self, add, remove):
        """What Apply changes will do, for the confirm page, by name: the tweaks installed (with the
        ones they need that aren't installed yet, and which ask for the sudo password) and removed."""
        comps = {c["id"]: c for c in self.rows}
        dim = "<span style='font-size:14px;color:#9aa6b2'>%s</span>"
        title = lambda cid: html.escape(comps[cid]["title"] if cid in comps else cid)   # noqa: E731  (a one-line helper for this method only)

        def sudo(cid):
            note = sft.sudo_note(comps[cid]) if cid in comps else ""
            return " " + dim % html.escape(_("(asks for your sudo password: %s)") % note) if note else ""
        parts = []
        if add:
            lines = [title(cid) + sudo(cid) for cid in add]
            # (./install.sh installs what they depend on first, from any pack in use)
            installed = {cid for cid, st in self.state.items() if st[0] not in GONE}
            needed, queue = {}, list(add)
            while queue:
                for d in comps.get(queue.pop(0), {}).get("deps", []):
                    if d in comps and d not in add and d not in installed and d not in needed:
                        needed[d] = next(c["id"] for c in comps.values() if d in c["deps"] and (c["id"] in add or c["id"] in needed))
                        queue.append(d)
            for d, by in needed.items():
                lines.append(title(d) + " " + dim % html.escape(_("(needed by %s)") % comps[by]["title"]) + sudo(d))
            parts.append("<b>" + _("Install:") + "</b><br>" + "<br>".join("• " + line for line in lines))
        if remove:
            parts.append("<b>" + _("Remove:") + "</b><br>" + "<br>".join("• " + title(cid) for cid in remove)
                         + "<br>" + dim % (_("Their settings are removed too (⚙ Preferences); their data is kept.")
                                           if sft.uninstall_settings() == "remove" else _("Their settings and data are kept.")))
        return "<br><br>".join(parts)

    def confirm(self, text, yes_label, on_yes):
        """Ask on the confirm page (text: rich text): Cancel goes back to the list, the yes button
        (yes_label) back too, then does on_yes."""
        self.confirm_text.setText(text)
        self.confirm_yes.setText(yes_label)
        try:
            self.confirm_yes.clicked.disconnect()
        except TypeError:
            pass
        self.confirm_yes.clicked.connect(lambda: (self.stack.setCurrentIndex(0), on_yes()))
        self.stack.setCurrentWidget(self.confirm_page)
