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
from window_logic import GONE, REPO, close_prompt, in_terminal


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
        self.update_blocks()
        button = getattr(self, "apply_button", None)
        if button is None:
            return
        add, remove = self.pending_changes()
        button.setEnabled(bool(add or remove))
        button.setToolTip((_("Install: %s") % ", ".join(add) if add else "") + ("; " if add and remove else "")
                          + (_("Remove: %s") % ", ".join(remove) if remove else "")
                          or _("Nothing to change: tick or untick a tweak first"))
        self.update_reinstall_changed()

    # ---- what can't be ticked: a newer Frame Tweaks needed, a conflict with an installed tweak ---
    def staying_installed(self):
        """The tweaks installed that stay so with what's ticked now (unticked ones are removed
        before anything is installed: Window.run_changes)."""
        return {cid for cid, st in self.state.items()
                if st is not None and st[0] not in GONE and self.wanted.get(cid, True)}

    def update_blocks(self):
        """A tweak not installed that needs a newer Frame Tweaks, or conflicts with one that stays
        installed (lib/registry.py install_block), can't be ticked: its box is off, its tooltip says
        why and names the other. Unticking that other frees it again. (A box a status made blocked
        after it was ticked is unticked: a box that's off couldn't be.)"""
        boxes = getattr(self, "boxes", None) or {}
        installed = self.staying_installed()
        self.blocked = {}
        for c in self.rows:
            st = self.state.get(c["id"])
            if st is not None and st[0] not in GONE:
                continue                                  # (installed: its box removes it)
            why = sft.install_block(c, installed, self.rows)
            if why:
                self.blocked[c["id"]] = why
        for cid, box in boxes.items():
            why = self.blocked.get(cid)
            if why:
                if box.isChecked():
                    box.blockSignals(True)
                    box.setChecked(False)
                    box.blockSignals(False)
                self.wanted.pop(cid, None)
                box.setEnabled(False)
                box.setToolTip(why)
            else:                                         # (as rebuild made it: not needed, say)
                box.setEnabled(box.property("base_enabled") is not False)
                box.setToolTip(box.property("base_tip") or box.toolTip())

    # ---- files changed since installed: ↻ Reinstall updated ------------------------------------
    def files_updated(self, cid):
        """cid's files changed since it was installed (sft.files_changed), and it's installed."""
        state = self.state.get(cid)
        return cid in self.files_changed and state is not None and state[0] not in GONE

    def updated_ids(self):
        """The installed tweaks whose files changed since they were installed, in the list's order."""
        return [c["id"] for c in self.rows if self.files_updated(c["id"])]

    def update_reinstall_changed(self):
        """↻ Reinstall updated (N), shown only while there's a tweak to reinstall."""
        button = getattr(self, "changed_button", None)
        if button is None:
            return
        ids = self.updated_ids()
        button.setVisible(bool(ids))
        button.setText(_("↻ Reinstall updated ({n})").format(n=len(ids)))
        button.setToolTip(_("Their files changed since they were installed (Frame Tweaks updated, or a pack edited), "
                            "and the installed copies are still the old ones. Installs them again: %s")
                          % ", ".join(ids) if ids else "")

    def reinstall_changed(self):
        """↻ Reinstall updated: the confirm page names them first, as Apply changes does."""
        ids = self.updated_ids()
        if not ids:
            self.say(_("Nothing to reinstall: no installed tweak's files changed since it was installed."))
            return
        comps = {c["id"]: c for c in self.rows}
        dim = "<span style='font-size:14px;color:#9aa6b2'>%s</span>"
        lines = []
        for cid in ids:
            note = sft.sudo_note(comps[cid])
            lines.append(html.escape(comps[cid]["title"])
                         + (" " + dim % html.escape(_("(asks for your sudo password: %s)") % note) if note else ""))
        text = ("<b>" + _("Install again, with the files that changed since they were installed:") + "</b><br>"
                + "<br>".join("• " + line for line in lines) + "<br>" + dim % _("Their settings and data are kept."))
        self.confirm(text, _("Reinstall"), lambda: self.run_reinstall_changed(ids))

    def ask_reinstall(self, cid):
        """↻ on a row (and its Reinstall link): the confirm page says what reinstalling does first, as
        Apply changes does, then run_reinstall."""
        comp = next((c for c in self.rows if c["id"] == cid), None)
        title = comp["title"] if comp else cid
        dim = "<span style='font-size:14px;color:#9aa6b2'>%s</span>"
        lines = [_("Removes it and installs it again in one step, stopping its running programs first.")]
        if comp is not None and comp.get("link"):
            lines = [_("Runs its own uninstaller, then its own installer again.")]
        if comp is not None and self.files_updated(cid):
            lines.append(_("Its files changed since it was installed: the new ones are used."))
        note = sft.sudo_note(comp) if comp is not None else ""
        if note:
            lines.append(_("Asks for your sudo password: %s") % note)
        text = ("<b>" + html.escape(_("Reinstall {title}?").format(title=title)) + "</b><br>"
                + "<br>".join("• " + html.escape(line) for line in lines) + "<br>"
                + dim % html.escape(_("Its settings and data are kept.")))
        self.confirm(text, _("Reinstall"), lambda: self.run_reinstall(cid))

    def run_reinstall_changed(self, ids):
        """./install.sh reinstall-changed in a terminal, for the tweaks the confirm page named (a tweak
        whose files are as installed again by then is left out there)."""
        cmd = "./install.sh reinstall-changed " + " ".join(shlex.quote(cid) for cid in ids)
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):      # for tests: show the plan, change nothing
            print("would run:", cmd)
            return
        full = f"cd {shlex.quote(str(REPO))} && {cmd}; echo; read -rp {close_prompt()}"
        self.proc = QProcess(self)            # don't block the window while Konsole runs
        self.proc.finished.connect(lambda *_: self.changed(ids))
        in_terminal(self.proc, full)

    def apply(self):
        if self.futures:
            self.say(_("Still checking status; try again in a moment."))
            return
        # From what you ticked (self.wanted), so rows in collapsed or hidden categories count too.
        add, remove = self.pending_changes()
        if not add and not remove:
            self.say(_("Nothing to change."))
            return
        # (what they need is installed too, and checked as well: ./install.sh would refuse the lot)
        staying = [cid for cid, st in self.state.items() if st is not None and st[0] not in GONE and cid not in remove]
        problems = sft.install_problems(add + list(self.needed(add)), staying, self.rows, window=True)
        if problems:                 # (said, with Apply off: nothing of it could install)
            self.confirm("<b>" + html.escape(_("These changes can't be applied:"), quote=False) + "</b><br>"
                         + "<br>".join("• " + html.escape(p, quote=False) for p in problems)
                         + "<br><br>" + self.changes_text(add, remove), _("Apply"), lambda: None, enabled=False)
            return
        blocked = self.needs_password(add)
        if blocked:                  # (sudo can't work yet: set a password first, then Apply again)
            self.confirm(_("{tweaks} need your sudo password, and your user has none yet. Set one, then "
                           "Apply changes again.").format(tweaks=", ".join(blocked))
                         + "<br><br>" + self.changes_text(add, remove), _("Set a password…"), self.set_password)
            return
        # (a tweak that drives hardware: the yes button says what it agrees to, not just Apply)
        hw = any(c.get("hardware") for c in self.rows if c["id"] in add)
        self.confirm(self.changes_text(add, remove), _("I understand the risk: apply") if hw else _("Apply"),
                     lambda: self.run_changes(add, remove))

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

    def needed(self, add):
        """{id: the tweak needing it} for what the tweaks in add depend on that isn't installed yet
        (./install.sh installs those first, from any pack in use)."""
        comps = {c["id"]: c for c in self.rows}
        installed = {cid for cid, st in self.state.items() if st is not None and st[0] not in GONE}
        needed, queue = {}, list(add)
        while queue:
            for d in comps.get(queue.pop(0), {}).get("deps", []):
                if d in comps and d not in add and d not in installed and d not in needed:
                    needed[d] = next(c["id"] for c in comps.values() if d in c["deps"] and (c["id"] in add or c["id"] in needed))
                    queue.append(d)
        return needed

    def changes_text(self, add, remove):
        """What Apply changes will do, for the confirm page, by name: the tweaks installed (with the
        ones they need that aren't installed yet, and which ask for the sudo password) and removed."""
        comps = {c["id"]: c for c in self.rows}
        dim = "<span style='font-size:14px;color:#9aa6b2'>%s</span>"
        title = lambda cid: html.escape(comps[cid]["title"] if cid in comps else cid)   # noqa: E731  (a one-line helper for this method only)

        def sudo(cid):
            note = sft.sudo_note(comps[cid]) if cid in comps else ""
            return " " + dim % html.escape(_("(asks for your sudo password: %s)") % note) if note else ""
        def hardware(cid):
            c = comps.get(cid, {})
            if not c.get("hardware"):
                return ""
            return ("<br>&nbsp;&nbsp;<span style='color:#e0b33a'>" + html.escape(
                _("⚠ Drives the Frame's hardware: {hardware}. If something goes wrong: {fail_safe}").format(
                    hardware=c["hardware"], fail_safe=c["fail_safe"])) + "</span>")
        parts = []
        if add:
            lines = [title(cid) + sudo(cid) + hardware(cid) for cid in add]
            for d, by in self.needed(add).items():
                lines.append(title(d) + " " + dim % html.escape(_("(needed by %s)") % comps[by]["title"]) + sudo(d))
            parts.append("<b>" + _("Install:") + "</b><br>" + "<br>".join("• " + line for line in lines))
        if remove:
            parts.append("<b>" + _("Remove:") + "</b><br>" + "<br>".join("• " + title(cid) for cid in remove)
                         + "<br>" + dim % (_("Their settings are removed too (⚙ Preferences); their data is kept.")
                                           if sft.uninstall_settings() == "remove" else _("Their settings and data are kept.")))
        return "<br><br>".join(parts)

    def confirm(self, text, yes_label, on_yes, enabled=True):
        """Ask on the confirm page (text: rich text): Cancel goes back to the list, the yes button
        (yes_label) back too, then does on_yes. enabled false: the yes button is shown off (what
        the text says stops it), until the next question."""
        self.confirm_text.setText(text)
        self.confirm_yes.setText(yes_label)
        self.confirm_yes.setEnabled(enabled)
        try:
            self.confirm_yes.clicked.disconnect()
        except TypeError:
            pass
        self.confirm_yes.clicked.connect(lambda: (self.stack.setCurrentIndex(0), on_yes()))
        self.stack.setCurrentWidget(self.confirm_page)
