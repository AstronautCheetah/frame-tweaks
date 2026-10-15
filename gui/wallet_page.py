"""The installer window's Wallet apps page: which apps open with the shared KDE wallet
(wallet-launcher), their password gate and Close-after timers (app-timers), and the wallet's
lock state (wallet-unlock). Part of gui/frame-tweaks-gui.py's window."""
import html
import json
import os
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path

from PyQt6 import sip
from PyQt6.QtCore import QProcess, Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout,
                             QWidget)

from i18n import _, N_, ngettext  # noqa: E402  (translations: locale/README.md; lib/ is on the path)

from sft import components  # (the tweaks: which one set up an app; lib/ is on the path)
import ftconf  # noqa: E402  (settings files; lib/ is on the path)

FLATPAK_ICONS = Path("/var/lib/flatpak/exports/share/icons/hicolor")
WALLET_LAUNCHER = Path.home() / ".local/bin/wallet-launcher"
APP_TIMERS = Path.home() / ".local/bin/app-timers"
WALLET_UNLOCK = Path.home() / ".local/bin/wallet-unlock"
TIMER_STEPS = [0, 5, 10, 15, 30, 60, 120, 240]          # minutes; 0 = never close
LAUNCHERS = Path.home() / ".local/share/applications"
FLATPAK_APPS = [Path.home() / ".local/share/flatpak/exports/share/applications",
                Path("/var/lib/flatpak/exports/share/applications")]
FLATPAK_ROOTS = [Path.home() / ".local/share/flatpak/app", Path("/var/lib/flatpak/app")]
SYSTEM_APPS = [Path("/usr/local/share/applications"), Path("/usr/share/applications")]
WALLET_MARK = "X-FrameTweaks-Wallet=true"
# Menu entries that aren't apps with secrets: Steam game shortcuts, SteamVR's link handler, the
# wallet's own Lock entry.
NOT_WALLET_APP = re.compile(r"steam://|/vrurlhandler\b|wallet-unlock")
# Entries a tweak sets up itself (removing one here lasts until that tweak is reinstalled): app
# id -> that tweak's title, looked up as the page fills (in the window's language of the moment).
def wallet_owners():
    return {app: c["title"] for c in components() for app in c["wallet_apps"]}   # (wallet_apps: in manifests)


def desktop_entry(path):
    """Keys of a .desktop file's [Desktop Entry] group (unlocalised)."""
    keys, section = {}, None
    try:
        lines = Path(path).read_text(errors="replace").splitlines()
    except OSError:
        return keys
    for line in lines:
        if line.startswith("["):
            section = line.strip()
        elif section == "[Desktop Entry]" and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            keys.setdefault(k.strip(), v.strip())
    return keys


def protected_apps():
    """Apps wallet-launcher has wrapped: id, name, icon and which protections are on."""
    apps = []
    for f in sorted(LAUNCHERS.glob("*.desktop")):
        try:
            text = f.read_text(errors="replace")
        except OSError:                     # (a broken link, say)
            continue
        if WALLET_MARK not in text:
            continue
        e = desktop_entry(f)
        cmd = e.get("Exec", "")
        apps.append({"id": f.stem, "name": e.get("Name", f.stem), "icon": e.get("Icon", ""),
                     "shared": "/.local/bin/frame-outer-bus" in cmd, "gate": "/.local/bin/wallet-gate" in cmd,
                     "electron": "--password-store=kwallet6" in cmd})
    return sorted(apps, key=lambda a: a["name"].lower())


def app_timers():
    """app-id -> (minutes of no activity before app-timers closes it, also on headset off)."""
    if not APP_TIMERS.exists():
        return {}
    out = subprocess.run([str(APP_TIMERS), "--list"], capture_output=True, text=True).stdout
    timers = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) in (2, 3):
            try:
                timers[parts[0]] = (float(parts[1]), parts[2:] == ["headset"])
            except ValueError:
                pass
    return timers


def span_text(seconds):
    """3 h 5 min / 12 min / under a minute."""
    m = int(seconds // 60)
    if m < 1:
        return _("under a minute")
    h, m = divmod(m, 60)
    return (_("{h} h {m} min").format(h=h, m=m) if h and m else _("{h} h").format(h=h) if h
            else _("{m} min").format(m=m))


LOCK_CONF = Path.home() / ".config/frame-tweaks/wallet.conf"
DEFAULT_LOCK_HOURS = 4
LOCK_STEPS = (1, 2, 3, 4, 6, 8, 12, 24)


def lock_hours():
    """The auto-lock length in hours, as wallet-unlock reads it (WALLET_LOCK_HOURS, else
    wallet.conf's, else 4)."""
    for v in (os.environ.get("WALLET_LOCK_HOURS"), ftconf.read_shell(LOCK_CONF).get("WALLET_LOCK_HOURS")):
        try:
            if v and float(v) > 0:
                return float(v)
        except ValueError:
            pass
    return DEFAULT_LOCK_HOURS


def autolock_on():
    """Whether the wallet locks itself, as wallet-unlock reads it (WALLET_AUTOLOCK, else
    wallet.conf's; on unless 0)."""
    return (os.environ.get("WALLET_AUTOLOCK") or ftconf.read_shell(LOCK_CONF).get("WALLET_AUTOLOCK") or "1") != "0"


def set_lock_hours(hours):
    """Save it for wallet-unlock (other lines in wallet.conf are kept). Takes effect at the next
    unlock or Extend timer."""
    ftconf.set_shell(LOCK_CONF, {"WALLET_LOCK_HOURS": f"{hours:g}"})


def wallet_state_text(info, now):
    """The status line atop Wallet apps, from wallet-unlock --info."""
    if info is None:
        return "<span style='color:#9aa6b2'>" + _("Wallet state unknown (is the Wallet tweak installed?)") + "</span>"
    if info["state"] == "locked":
        return ("<b style='color:#5cc77a'>" + _("🔒 Wallet locked.") + "</b> "
                + _("Protected apps ask for the password before they open."))
    bold = "<b style='color:#e0b33a'>" + _("🔓 Wallet open") + "</b>"
    if info.get("unlocked_at"):
        text = _("{wallet_open} for {time}.").format(wallet_open=bold, time=span_text(now - info["unlocked_at"]))
    else:
        text = bold + "."
    if info.get("locks_at"):
        at = time.strftime("%H:%M", time.localtime(info["locks_at"]))
        left = span_text(max(0, info["locks_at"] - now))
        if info.get("idle_close_minutes"):
            text += " " + _("Locks by itself at {at} (in {time}), or sooner after {idle} unused.").format(
                at=f"<b>{at}</b>", time=left, idle=timer_text(info["idle_close_minutes"]))
        else:
            text += " " + _("Locks by itself at {at} (in {time}).").format(at=f"<b>{at}</b>", time=left)
    elif info.get("autolock") is False:
        text += " " + _("It stays unlocked until you lock it (auto-lock is off).")
    elif info.get("idle_close_minutes"):
        text += " " + _("Locks by itself after {idle} unused.").format(idle=timer_text(info["idle_close_minutes"]))
    else:
        text += " <span style='color:#e0b33a'>" + _("No automatic lock is scheduled.") + "</span>"
    return text


def timer_text(minutes):
    if not minutes:
        return _("Never")
    return _("{h} h").format(h=f"{minutes / 60:g}") if minutes >= 60 else _("{m} min").format(m=f"{minutes:g}")


def timer_step(minutes, step, floor=0):
    """The next/previous preset from minutes (a custom value snaps to its neighbour)."""
    if step > 0:
        nxt = [m for m in TIMER_STEPS if m > minutes]
        return nxt[0] if nxt else TIMER_STEPS[-1]
    prev = [m for m in TIMER_STEPS if m < minutes and m >= floor]
    return prev[-1] if prev else max(floor, TIMER_STEPS[0])


def is_electron(app):
    """Electron (and Chromium-based) apps ship resources.pak next to their program; they must be
    told to use the wallet. Flatpaks: looked up in the app's files; others: from Exec's program."""
    if app["kind"] == "Flatpak":
        for root in FLATPAK_ROOTS:
            files = root / app["id"] / "current" / "active" / "files"
            for pattern in ("resources.pak", "*/resources.pak", "*/*/resources.pak", "lib/*/resources.pak"):
                if any(files.glob(pattern)):
                    return True
        return False
    try:
        args = shlex.split(app.get("exec", ""))
    except ValueError:
        return False
    while args and (args[0] == "env" or "=" in args[0]):
        args = args[1:]
    prog = args and shutil.which(os.path.expanduser(args[0]))
    if not prog:
        return False
    d = Path(os.path.realpath(prog)).parent
    return (d / "resources.pak").exists() or (d.parent / "resources.pak").exists()


def wallet_candidates(protected_ids):
    """Every installed app shown in menus (Flatpak, your own launchers, the system's) that isn't
    protected yet. An app with entries in several places counts once (the one menus use)."""
    seen = {}
    # (kind: also a key; translated where it's shown)
    for kind, dirs in ((N_("Your app"), [LAUNCHERS]), ("Flatpak", FLATPAK_APPS), (N_("System app"), SYSTEM_APPS)):
        for d in dirs:
            for f in sorted(d.glob("*.desktop")) if d.is_dir() else []:
                if f.stem in seen:
                    continue
                e = desktop_entry(f)
                seen[f.stem] = None          # hidden or not: this entry is what menus see
                if (f.stem in protected_ids or e.get("Type", "Application") != "Application"
                        or e.get("NoDisplay") == "true" or e.get("Hidden") == "true" or "Exec" not in e
                        or NOT_WALLET_APP.search(e["Exec"])):
                    continue
                if kind == "Your app" and any((d2 / f.name).exists() for d2 in FLATPAK_APPS):
                    kind_here = "Flatpak"    # your override of a Flatpak's entry
                else:
                    kind_here = kind
                seen[f.stem] = {"id": f.stem, "name": e.get("Name", f.stem), "icon": e.get("Icon", ""),
                                "kind": kind_here, "exec": e.get("Exec", "")}
    return sorted((a for a in seen.values() if a), key=lambda a: a["name"].lower())


def app_icon(name):
    if not name:
        return QIcon()
    if name.startswith("/"):
        return QIcon(name)
    for base in (Path.home() / ".local/share/icons/hicolor",
                 Path.home() / ".local/share/flatpak/exports/share/icons/hicolor", FLATPAK_ICONS):
        hits = sorted(base.glob(f"*/apps/{name}.png"), key=lambda p: p.parent.parent.name) + \
            sorted(base.glob(f"scalable/apps/{name}.svg"))
        if hits:
            return QIcon(str(hits[-1]))
    return QIcon.fromTheme(name)




class WalletApps(QWidget):
    """Choose which apps open with the shared KDE wallet (wallet-launcher), inside the window."""

    def __init__(self, window):
        super().__init__()
        self.window = window
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        back = QPushButton(_("← Back"))
        back.clicked.connect(window.go_back)
        head.addWidget(back)
        title = QLabel(_("Wallet apps"))
        title.setObjectName("title")
        head.addWidget(title, 1)
        lay.addLayout(head)
        why = QLabel(_(
            "<b>Why use this?</b> Many people don't put a password on their Steam Frame: it's quicker "
            "to pick up, and it gets passed around to family and friends. But the apps you use in it "
            "can still hold sensitive things, like messages, notes and signed-in accounts. Here you "
            "can keep those apps behind <b>one password, your KDE wallet's</b>, without locking the "
            "whole headset: the wallet is unlocked once when you need it, and locks again by itself."))
        why.setWordWrap(True)
        lay.addWidget(why)
        # Wallet state: open or locked, since when, when it locks by itself; Lock / Unlock.
        status_row = QHBoxLayout()
        self.wallet_state = QLabel()
        self.wallet_state.setWordWrap(True)
        self.wallet_state.setTextFormat(Qt.TextFormat.RichText)
        status_row.addWidget(self.wallet_state, 1)
        self.extend = QPushButton(_("⏱ Extend timer"))
        self.extend.clicked.connect(self.extend_timer)
        status_row.addWidget(self.extend)
        self.wallet_toggle = QPushButton()
        self.wallet_toggle.clicked.connect(self.toggle_wallet)
        status_row.addWidget(self.wallet_toggle)
        lay.addLayout(status_row)
        # How long an unlock lasts (wallet.conf; wallet-unlock reads it). Buttons, not a drop-down:
        # a pop-up list opens as a window of its own in VR.
        hours_row = QHBoxLayout()
        self.autolock = QCheckBox(_("Auto-lock"))
        self.autolock.setToolTip(_("Lock the wallet by itself: a set time after unlocking, or after 4 h unused"))
        self.autolock.clicked.connect(self.toggle_autolock)
        hours_row.addWidget(self.autolock)
        hours_label = QLabel(_("after unlocking:"))
        hours_label.setObjectName("desc")
        hours_row.addWidget(hours_label)
        self.shorter = QPushButton("−")
        self.shorter.clicked.connect(lambda: self.step_hours(-1))
        self.hours_text = QLabel()
        self.longer = QPushButton("+")
        self.longer.clicked.connect(lambda: self.step_hours(+1))
        for w in (self.shorter, self.hours_text, self.longer):
            hours_row.addWidget(w)
        hours_row.addStretch(1)
        lay.addLayout(hours_row)
        self.show_hours()
        self.wallet_locked = None
        self.state_timer = QTimer(self, interval=30000, timeout=self.show_wallet_state)
        self.state_timer.start()
        self.show_wallet_state()
        about = QLabel(_(
            "Apps listed here open with the <b>shared KDE wallet</b>, the same one in VR and in desktop "
            "mode, so the logins and keys they save are kept and stay encrypted. Electron apps are also "
            "told to use it (without that they can't keep a sign-in). <b>Password first</b> asks for "
            "the wallet password before the app opens, when the wallet is locked. <b>Close after</b> quits the "
            "app after that long with no activity (no keyboard, mouse or controller input), so opening it "
            "again needs the wallet again; <b>Headset off</b> also quits it ~10 s after the headset is taken off."))
        about.setWordWrap(True)
        about.setObjectName("desc")
        lay.addWidget(about)
        self.notice = QLabel()
        self.notice.setObjectName("notice")
        self.notice.setWordWrap(True)
        lay.addWidget(self.notice)
        self.body = QWidget()
        self.rows = QVBoxLayout(self.body)
        self.rows.setSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.body)
        lay.addWidget(scroll, 1)
        self.fill()

    def show_wallet_state(self):
        try:
            r = subprocess.run([str(WALLET_UNLOCK), "--info"], capture_output=True, text=True, timeout=10)
            info = json.loads(r.stdout)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            info = None
        self.wallet_locked = None if info is None else info["state"] == "locked"
        self.wallet_state.setText(wallet_state_text(info, time.time()))
        self.wallet_toggle.setVisible(info is not None)
        on = autolock_on() if info is None else info.get("autolock", True)
        self.autolock.setChecked(on)
        self.extend.setVisible(info is not None and not self.wallet_locked and on)
        self.extend.setToolTip(_("Start the {time} countdown to the auto-lock again, from now").format(
            time=timer_text(lock_hours() * 60)))
        self.wallet_toggle.setText(_("🔓 Unlock…") if self.wallet_locked else _("🔒 Lock now"))
        self.wallet_toggle.setToolTip(_("Asks for the wallet password") if self.wallet_locked else
                                      _("Lock the wallet now: protected apps need the password again"))

    def wallet_unlock(self, args, then):
        """wallet-unlock with args, in the background; then() when it's done, if this page is still
        open. (The window's process, not the page's: going Back mustn't stop an unlock waiting
        for its password.)"""
        proc = QProcess(self.window)
        proc.finished.connect(lambda *_: (proc.deleteLater(), sip.isdeleted(self) or then()))
        proc.start(str(WALLET_UNLOCK), args)

    def extend_timer(self):
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run: wallet-unlock --schedule-lock")
            return
        self.wallet_unlock(["--schedule-lock"], self.show_wallet_state)

    def toggle_autolock(self, on):
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run: wallet-unlock --autolock", "on" if on else "off")
            return
        self.wallet_unlock(["--autolock", "on" if on else "off"], lambda: (self.show_hours(), self.show_wallet_state()))

    def show_hours(self):
        on = autolock_on()
        for w in (self.shorter, self.longer, self.hours_text):
            w.setEnabled(on)
        h = lock_hours()
        self.hours_text.setText(f"<b>{timer_text(h * 60)}</b>" + ("" if h == DEFAULT_LOCK_HOURS else " " + _("(default 4 h)")))
        self.shorter.setEnabled(on and h > LOCK_STEPS[0])
        self.longer.setEnabled(on and h < LOCK_STEPS[-1])

    def step_hours(self, direction):
        h = lock_hours()
        options = [x for x in LOCK_STEPS if (x < h if direction < 0 else x > h)]
        if options:
            hours = options[-1] if direction < 0 else options[0]
            if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
                print(f"would save: WALLET_LOCK_HOURS={hours:g}")
                return
            set_lock_hours(hours)
        self.show_hours()
        self.show_wallet_state()

    def toggle_wallet(self):
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run: wallet-unlock", "" if self.wallet_locked else "--lock")
            return
        if self.wallet_locked:
            # The password dialog opens on this display; the window stays usable meanwhile.
            self.wallet_unlock([], self.show_wallet_state)
            self.wallet_state.setText(_("Waiting for the wallet password (look for the dialog)…"))
        else:
            self.wallet_unlock(["--lock"], self.show_wallet_state)   # (not waited for: the window stays usable)

    def fill(self):
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        protected = protected_apps()
        timers = app_timers()
        owners = wallet_owners()
        self.rows.addWidget(self.heading(_("Protected ({n})").format(n=len(protected))))
        for a in protected:
            what = (([_("shared wallet")] if a["shared"] else []) + ([_("Electron told to use it")] if a["electron"] else [])
)
            note = " · ".join(what) or _("password only (keeps its own session)")
            if a["id"] in owners:
                note += "<br><span style='color:#6b7783'>" + _(
                    "Set up by the “{tweak}” tweak: reinstalling it (↻) adds it back if removed here.").format(
                    tweak=owners[a["id"]]) + "</span>"
            gate = QCheckBox(_("Password first"))
            gate.setChecked(a["gate"])
            gate.setToolTip(_("Ask for the wallet password before the app opens (when the wallet is locked)"))
            gate.toggled.connect(lambda on, a=a: self.set_gate(a, on))
            remove = QPushButton(_("Remove"))
            remove.setToolTip(_("Open it the way it opened before (its original launcher)"))
            remove.clicked.connect(lambda _checked=False, a=a: self.run(
                ["--remove", a["id"]], _("{app}: removed").format(app=a["name"])))
            controls = [self.timer_control(a, *timers.get(a["id"], (0, False)))] if APP_TIMERS.exists() else []
            self.rows.addWidget(self.row(a, note, controls + [gate, remove]))
        candidates = wallet_candidates({a["id"] for a in protected})
        self.rows.addWidget(self.heading(ngettext("Add an app ({n} installed app)", "Add an app ({n} installed apps)",
                                                  len(candidates)).format(n=len(candidates))))
        for a in candidates:
            electron = is_electron(a)
            note = f"{_(a['kind'])} · {a['id']}" + (" · " + _("Electron app: will be told to use the wallet")
                                                    if electron else "")
            add = QPushButton(_("Protect"))
            add.setObjectName("run")
            add.clicked.connect(lambda _checked=False, a=a, el=electron: self.run(
                (["--electron"] if el else []) + [a["id"]],
                _("{app}: protected. Reopen it if it's running.").format(app=a["name"])))
            self.rows.addWidget(self.row(a, note, [add]))
        self.rows.addStretch(1)

    @staticmethod
    def heading(text):
        label = QLabel(text.upper())
        label.setStyleSheet("color: #7fb2e5; font-weight: 600; letter-spacing: 1px; margin-top: 8px;")
        return label

    @staticmethod
    def row(app, note, buttons):
        w = QWidget()
        w.setObjectName("row")
        w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        g = QHBoxLayout(w)
        g.setContentsMargins(12, 8, 12, 8)
        g.setSpacing(14)
        icon = QLabel()
        icon.setPixmap(app_icon(app["icon"]).pixmap(32, 32))
        g.addWidget(icon)
        text = QLabel(f"<b>{html.escape(app['name'], quote=False)}</b><br>"
                      f"<span style='color:#9aa6b2;font-size:13px'>{note}</span>")
        text.setWordWrap(True)
        g.addWidget(text, 1)
        for b in buttons:
            g.addWidget(b)
        return w

    def timer_control(self, app, minutes, headset):
        """Close after: [−] 15 min [+]  (steppers, not a drop-down: in VR a drop-down's list
        opens as a separate window in the dashboard)."""
        box = QWidget()
        box.setObjectName("timer")
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        label = QLabel(_("Close after"))
        label.setObjectName("desc")
        value = QLabel(timer_text(minutes))
        value.setMinimumWidth(64)
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        floor = 0
        less, more = QPushButton("−"), QPushButton("+")
        for b, step in ((less, -1), (more, 1)):
            b.setObjectName("info")
            b.setToolTip(_("Shorter") if step < 0 else _("Longer"))
            b.clicked.connect(lambda _=False, st=step: self.set_timer(app, timer_step(minutes, st, floor)))
        less.setEnabled(minutes > floor)
        more.setEnabled(minutes < TIMER_STEPS[-1])
        box.setToolTip(_("Quit the app after this long with no keyboard, mouse or controller input"))
        for w in (label, less, value, more):
            lay.addWidget(w)
        off = QCheckBox(_("Headset off"))
        off.setChecked(headset)
        off.setEnabled(minutes > 0)
        off.setToolTip(_("Also quit it about 10 s after the headset is taken off") if minutes else
                       _("Set a Close after time first"))
        off.toggled.connect(lambda on: self.set_headset(app, on))
        lay.addSpacing(10)
        lay.addWidget(off)
        return box

    def set_timer(self, app, minutes):
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run: app-timers --set", app["id"], minutes)
            return
        r = subprocess.run([str(APP_TIMERS), "--set", app["id"], f"{minutes:g}"], capture_output=True, text=True)
        self.notice.setText(html.escape(
            (_("{app}: closes after {time} with no activity").format(app=app["name"], time=timer_text(minutes))
             if minutes else _("{app}: no timer").format(app=app["name"])) if r.returncode == 0 else
            _("Didn't work: %s") % (r.stderr or r.stdout).strip(), quote=False))
        QTimer.singleShot(0, self.fill)

    def set_headset(self, app, on):
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run: app-timers --headset", app["id"], "on" if on else "off")
            return
        r = subprocess.run([str(APP_TIMERS), "--headset", app["id"], "on" if on else "off"],
                           capture_output=True, text=True)
        self.notice.setText(html.escape(
            (f"{app['name']}: " + (_("also closes when the headset is taken off") if on else
                                   _("no longer closes when the headset is taken off"))) if r.returncode == 0 else
            _("Didn't work: %s") % (r.stderr or r.stdout).strip(), quote=False))
        QTimer.singleShot(0, self.fill)

    def set_gate(self, app, on):
        args = (["--gate"] if on else ["--no-gate"]) + ([] if app["shared"] else ["--no-shared"]) + [app["id"]]
        self.run(args, f"{app['name']}: " + (_("asks for the wallet password first") if on else
                                             _("opens without asking for the password")))

    def run(self, args, done):
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run: wallet-launcher", " ".join(args))
            return
        r = subprocess.run([str(WALLET_LAUNCHER)] + args, capture_output=True, text=True)
        self.notice.setText(html.escape(done if r.returncode == 0 else
                                        _("Didn't work: %s") % (r.stderr or r.stdout).strip(), quote=False))
        QTimer.singleShot(0, self.fill)
