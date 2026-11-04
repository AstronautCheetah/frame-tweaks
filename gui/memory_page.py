"""The installer window's Memory limits page (VR memory guard): the memory kept free for VR, and
each Flatpak app's own limit or "shared" (only the apps' pool applies to it). vr-memory-guard-tool
reads, checks and applies them; the page only shows them and says what changed. Part of
gui/frame-tweaks-gui.py's window."""
import html
import json
import os
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

import i18n  # noqa: E402
from i18n import _  # noqa: E402  (translations: locale/README.md; lib/ is on the path)

# (the Wallet apps page's rows, menu entries, and its way of running slow commands and writing numbers)
from wallet_page import FLATPAK_APPS, WalletApps, desktop_entry, in_background, local_number, no_answer

TOOL = Path.home() / ".local/bin/vr-memory-guard-tool"
INFO_TIMEOUT, APPLY_TIMEOUT = 90, 120   # s: info finds the apps (flatpak list); apply puts them in force
STEP = 512                 # MiB a press: half a GB, fine enough on 16 GB, few enough presses in VR
LOWEST = 512               # (the tool takes 256M, but an app limited that low is stopped as it opens)
NEW_LIMIT = 4096           # (an app given a limit of its own starts here, or at the pool if that's less)


def size_arg(v):
    """MiB as the tool takes a size: 5G, 2560M."""
    return f"{v // 1024}G" if v % 1024 == 0 else f"{v}M"


def gb_text(v):
    """MiB as the page shows it: 5 GB, 2.5 GB, 3.42 GB."""
    return _("{n} GB").format(n=local_number(f"{v / 1024:.2f}".rstrip("0").rstrip(".")))


def step(v, direction, lo, hi):
    """The next value a press of − or + gives, on the STEP grid (a value from the file between two
    steps goes to its neighbour), kept within lo..hi."""
    v = (v // STEP + 1) * STEP if direction > 0 else ((v - 1) // STEP) * STEP
    return max(lo, min(hi, v))


def read_info():
    """(the tool's info, None) or (None, why there's none)."""
    if not TOOL.exists():
        return None, _("This page needs vr-memory-guard-tool, which VR memory guard installs since this version: "
                       "reinstall it (↻) first.")
    try:
        r = subprocess.run([str(TOOL), "info"], capture_output=True, text=True, timeout=INFO_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, _("Didn't work: %s") % no_answer(TOOL, INFO_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as e:
        return None, _("Didn't work: %s") % e
    if r.returncode:
        return None, _("Didn't work: %s") % (r.stderr or r.stdout).strip()
    try:
        return json.loads(r.stdout), None
    except ValueError:
        return None, _("Didn't work: %s") % r.stdout.strip()[:300]


def run_calls(calls):
    """(ok, what the last said, or what the one that failed did): the tool's commands, in order,
    up to the first that fails (what ran before it is saved)."""
    said = ""
    for a in calls:
        try:
            r = subprocess.run([str(TOOL), *a], capture_output=True, text=True, timeout=APPLY_TIMEOUT)
            ok, out = r.returncode == 0, (r.stdout if r.returncode == 0 else r.stderr or r.stdout).strip()
        except subprocess.TimeoutExpired:
            ok, out = False, no_answer(TOOL, APPLY_TIMEOUT)
        except (OSError, subprocess.SubprocessError) as e:
            ok, out = False, str(e)
        if not ok:
            return False, out
        said = out
    return True, said


def app_entry(app):
    """(name, icon) from the app's menu entry, else its id."""
    for d in FLATPAK_APPS:
        f = d / f"{app}.desktop"
        if f.exists():
            e = desktop_entry(f)
            return i18n.entry_name(e, app), e.get("Icon") or app
    return app, app


class Stepper(QWidget):
    """[−] value [+]: big buttons, not a spin box or a drop-down (a spin box's arrows are too small
    for a laser; a drop-down's list opens as a window of its own in VR)."""

    def __init__(self, changed, less_tip, more_tip):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.less, self.more = QPushButton("−"), QPushButton("+")
        self.value = QLabel()
        self.value.setMinimumWidth(96)
        self.value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for b, direction, tip in ((self.less, -1, less_tip), (self.more, 1, more_tip)):
            b.setObjectName("info")
            b.setMinimumSize(52, 44)
            b.setToolTip(tip)
            b.clicked.connect(lambda _checked=False, d=direction: changed(d))
        for w in (self.less, self.value, self.more):
            lay.addWidget(w)

    def display(self, text, can_less, can_more, enabled=True):
        self.value.setText(text)
        self.value.setEnabled(enabled)
        self.less.setEnabled(enabled and can_less)
        self.more.setEnabled(enabled and can_more)


class MemoryLimits(QWidget):
    """The memory kept for VR and each Flatpak app's own limit, inside the window."""

    def __init__(self, window):
        super().__init__()
        self.window = window
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        back = QPushButton(_("← Back"))
        back.clicked.connect(window.go_back)
        head.addWidget(back)
        title = QLabel(_("Memory limits"))
        title.setObjectName("title")
        head.addWidget(title, 1)
        # (at the top right, as on a ⚙ Settings page: in sight however far the list is scrolled)
        self.apply = QPushButton(_("Apply"))
        self.apply.setObjectName("apply")
        self.apply.clicked.connect(self.run_apply)
        head.addWidget(self.apply)
        lay.addLayout(head)
        about = QLabel(_(
            "Flatpak apps (Firefox, and the apps you install from Discover) share the memory that isn't "
            "<b>kept free for VR</b>: past it, the app that asks for more is stopped, and SteamVR, Steam and "
            "your game keep running. An app can also have a <b>limit of its own</b>, so it's stopped before it "
            "takes the others' share; <b>shared</b> means only the apps' common limit applies to it. Games and "
            "the desktop itself aren't limited."))
        about.setWordWrap(True)
        about.setObjectName("desc")
        lay.addWidget(about)
        reserve_row = QHBoxLayout()
        label = QLabel(_("Kept free for VR"))
        label.setStyleSheet("font-weight: 600;")
        reserve_row.addWidget(label)
        self.reserve = Stepper(self.step_reserve, _("Keep less for VR: more for the apps"),
                               _("Keep more for VR: less for the apps"))
        self.reserve.setToolTip(_("Memory Flatpak apps leave free for SteamVR, Steam and your game"))
        reserve_row.addWidget(self.reserve)
        self.pool = QLabel()
        self.pool.setObjectName("desc")
        self.pool.setWordWrap(True)
        reserve_row.addWidget(self.pool, 1)
        lay.addLayout(reserve_row)
        self.notice = QLabel()
        self.notice.setObjectName("notice")
        self.notice.setWordWrap(True)
        lay.addWidget(self.notice)
        self.body = QWidget()
        self.rows = QVBoxLayout(self.body)
        self.rows.setSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.body)
        lay.addWidget(scroll, 1)
        self.fill()

    def fill(self, said=""):
        """The tool's settings, read again; what's shown becomes what's saved (Apply dims). Read in
        the background (in_background): the tool lists the Flatpak apps, which can take long, and
        the window froze meanwhile. said: the notice once they're in (what Apply did)."""
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.controls, self.info = {}, None
        self.reserve.setEnabled(False)
        self.show_values()
        self.notice.setText(html.escape(_("Reading the limits…"), quote=False))
        self.job = in_background(self, read_info, lambda fut: self.filled(fut, said))

    def filled(self, fut, said):
        self.job = None
        try:
            info, why = fut.result()
        except Exception as e:                  # (said on the page rather than lost in the worker)
            info, why = None, _("Didn't work: %s") % e
        self.info = info
        self.notice.setText(said)
        if info is None:
            self.notice.setText(html.escape(why, quote=False))
            self.reserve.setEnabled(False)
            self.show_values()
            return
        self.reserve.setEnabled(True)
        self.saved = {"reserve": info["reserve"], "apps": {a["id"]: a["limit"] for a in info["apps"]}}
        self.chosen = {"reserve": info["reserve"], "apps": dict(self.saved["apps"])}
        apps = [a for a in info["apps"] if a["installed"]]
        self.rows.addWidget(WalletApps.heading(_("Flatpak apps ({n})").format(n=len(apps))))
        if not apps:
            none = QLabel(_("No Flatpak apps are installed."))
            none.setObjectName("desc")
            self.rows.addWidget(none)
        for a in apps:
            name, icon = app_entry(a["id"])
            own = QCheckBox(_("Own limit"))
            own.setToolTip(_("A limit of its own; unticked, it's shared: only the limit all Flatpak apps share "
                             "applies to it"))
            own.clicked.connect(lambda on, app=a["id"]: self.set_own(app, on))
            stepper = Stepper(lambda d, app=a["id"]: self.step_app(app, d), _("Less memory for this app"),
                              _("More memory for this app"))
            stepper.setToolTip(_("Above this, the app is stopped (and it may use some swap on top)"))
            note = QLabel()
            row = WalletApps.row({"name": name, "icon": icon}, html.escape(a["id"], quote=False), [own, stepper],
                                 below=note)
            note.setWordWrap(True)
            self.controls[a["id"]] = (own, stepper, note)
            self.rows.addWidget(row)
        self.rows.addStretch(1)
        self.show_values()

    def pool_size(self):
        return self.info["total"] - self.chosen["reserve"]

    def show_values(self):
        """Every control's value, and Apply dimmed until something differs from what's saved."""
        if self.info is None:
            self.reserve.display("", False, False, enabled=False)
            self.pool.setText("")
            self.apply.setEnabled(False)
            self.apply.setToolTip(_("Nothing to apply"))
            return
        r, pool = self.chosen["reserve"], self.pool_size()
        self.reserve.display(f"<b>{gb_text(r)}</b>", r > self.info["min_reserve"], r < self.info["max_reserve"])
        self.pool.setText(_("Flatpak apps together: up to {pool} of {total}.").format(
            pool=gb_text(pool), total=gb_text(self.info["total"])))
        for app, (own, stepper, note) in self.controls.items():
            v = self.chosen["apps"].get(app)
            own.setChecked(v is not None)
            if v is None:
                stepper.display(_("shared"), False, False, enabled=False)
                note.setText("")
                note.setHidden(True)
            else:
                stepper.display(f"<b>{gb_text(v)}</b>", v > LOWEST, v < pool)
                note.setText("<span style='color:#e0b33a'>" + _("More than all Flatpak apps together may use: their "
                                                                 "common limit applies first.") + "</span>"
                             if v > pool else "")
                note.setHidden(v <= pool)
        pending = bool(self.commands())
        self.apply.setEnabled(pending)
        self.apply.setToolTip(_("Save these limits and put them in force, for the apps open now too") if pending
                              else _("Nothing to apply: change a limit first"))

    def step_reserve(self, direction):
        self.chosen["reserve"] = step(self.chosen["reserve"], direction, self.info["min_reserve"],
                                      self.info["max_reserve"])
        if direction > 0:                 # (a limit of its own can't be more than the apps' pool)
            for app in self.controls:     # (the apps shown: one in the file that isn't installed is left as it is)
                v = self.chosen["apps"].get(app)
                if v is not None and v > self.pool_size():
                    self.chosen["apps"][app] = self.pool_size()
        self.show_values()

    def step_app(self, app, direction):
        v = self.chosen["apps"].get(app)
        if v is not None:
            self.chosen["apps"][app] = step(v, direction, LOWEST, max(LOWEST, self.pool_size()))
        self.show_values()

    def set_own(self, app, on):
        if on:
            old = self.saved["apps"].get(app)
            self.chosen["apps"][app] = min(old if old is not None else NEW_LIMIT, self.pool_size())
        else:
            self.chosen["apps"][app] = None
        self.show_values()

    def commands(self):
        """The tool's commands for what changed: the reserve first (an app's new limit is checked
        against the pool it leaves), then each app."""
        if self.info is None:
            return []
        out = [] if self.chosen["reserve"] == self.saved["reserve"] else [["reserve", size_arg(self.chosen["reserve"])]]
        for app, v in sorted(self.chosen["apps"].items()):
            if v != self.saved["apps"].get(app):
                out.append(["set", app, "shared" if v is None else size_arg(v)])
        return out

    def run_apply(self):
        calls = self.commands() + [["apply"]]
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            for a in calls:
                print("would run: vr-memory-guard-tool", " ".join(a))
            self.saved = {"reserve": self.chosen["reserve"], "apps": dict(self.chosen["apps"])}
            self.show_values()
            return
        self.apply.setEnabled(False)                # (not twice while it runs)
        self.notice.setText(html.escape(_("Applying…"), quote=False))
        self.job = in_background(self, lambda: run_calls(calls), self.applied)

    def applied(self, fut):
        self.job = None
        try:
            ok, out = fut.result()
        except Exception as e:
            ok, out = False, str(e)
        # (read back either way: what ran before a failure is saved, so Apply offers only what's left)
        self.fill(html.escape(out, quote=False).replace("\n", "<br>") if ok
                  else html.escape(_("Didn't work: %s") % out, quote=False))
