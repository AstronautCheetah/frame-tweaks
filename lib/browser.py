#!/usr/bin/env python3
"""Open a web link, a folder or a file in its default app, in whichever session it's already running.

The Frame runs two sessions: Steam's VR session (X display :0, where floating windows live) and
the desktop mode (Plasma on Wayland, nested in VR). A browser started in one session can't hand
a link to a copy running in the other (Firefox then says it's "already running, but is not
responding"). So: find the default app (as desktop mode sets it: the VR session doesn't read
KDE's defaults, so a folder there would open in Kate, not Dolphin); if it's running in this
program's session, send the link there; if only in the other session, launch it with that
session's environment (display, runtime folder, session bus) so it reaches the running copy; if it isn't running, open it in VR.

  browser.py URL|PATH             open it
  browser.py --where URL|PATH     say what it would do, without opening anything
"""
import os
import re
import shlex
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import i18n  # noqa: E402
from i18n import _, N_  # noqa: E402  (translations: locale/README.md)
import ftconf  # noqa: E402

VR, DESKTOP = N_("VR"), N_("desktop mode")      # (also keys: translated where they're shown)
# What makes a program part of one session or the other; copied from a process of the target
# session (anything else is kept from ours). Desktop mode has its own runtime folder and session
# bus, where a running app is found (Flatpak Firefox's remote lives there): without them a second
# copy can't reach it and says it's "already running".
SESSION_KEYS = ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS",
                "DISPLAY", "WAYLAND_DISPLAY", "XDG_CURRENT_DESKTOP", "XDG_SESSION_TYPE",
                "XDG_SESSION_DESKTOP", "DESKTOP_SESSION", "KDE_FULL_SESSION", "KDE_SESSION_VERSION",
                "XDG_DESKTOP_PORTAL_DIR", "XAUTHORITY", "GDK_BACKEND", "QT_QPA_PLATFORM")
REFERENCE = {DESKTOP: ("plasmashell",), VR: ("steam", "steamwebhelper")}
WRAPPERS = {"env", "wallet-gate", "flatpak-spawn"}
SHELLS = {"sh", "bash", "dash", "zsh"}


def session_of(env):
    """VR, DESKTOP, or None for a process environment."""
    desk = env.get("XDG_CURRENT_DESKTOP", "")
    if desk == "gamescope":
        return VR
    if "KDE" in desk.split(":") or env.get("WAYLAND_DISPLAY"):
        return DESKTOP
    if env.get("DISPLAY") == ":0":
        return VR
    return None


def choose(own, running):
    """Where to open: our own session if the browser runs there, else wherever it runs, else VR."""
    if own in running:
        return own
    if running:
        return DESKTOP if DESKTOP in running else VR
    return VR


def proc_env(pid):
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except OSError:
        return None
    return dict(kv.split("=", 1) for kv in raw.decode(errors="replace").split("\0") if "=" in kv)


def proc_cmd(pid):
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace").split("\0")
    except OSError:
        return []


def pids():
    me = os.getuid()
    for p in Path("/proc").iterdir():
        if p.name.isdigit():
            try:
                if p.stat().st_uid == me:
                    yield int(p.name)
            except OSError:
                pass


def xdg_mime(*args, env=None):
    try:
        return subprocess.run(["xdg-mime", *args], env=env, capture_output=True, text=True,
                              timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def default_app(*kinds):
    """The default app's desktop file id for the first of these MIME types that has one, as
    desktop mode sets it (KDE's defaults), else as this session sees it; or None."""
    for env in ({**os.environ, "XDG_CURRENT_DESKTOP": "KDE"}, None):
        for kind in kinds:
            out = xdg_mime("query", "default", kind, env=env)
            if out.endswith(".desktop"):
                return out
    return None


def default_browser():
    """The default browser's desktop file id (e.g. org.mozilla.firefox.desktop), or None."""
    return default_app("x-scheme-handler/https", "x-scheme-handler/http", "text/html")


def usable(app_id):
    """Whether app_id is installed and opens a link itself: not a placeholder that only offers to
    install a browser (SteamOS's "Install Chromium" opens the software store, and without a
    default of your own it's the system's first choice for links)."""
    path = desktop_file(app_id) if app_id else None
    if not path:
        return False
    try:
        keys = entry(path)
    except OSError:                                    # (unreadable: not one to use)
        return False
    cmd = keys.get("Exec", "")
    if "appstream:" in cmd or keys.get("Hidden") == "true":
        return False
    if keys.get("TryExec") and not (shutil.which(keys["TryExec"]) or Path(keys["TryExec"]).is_file()):
        return False
    try:
        words = [w for w in shlex.split(cmd) if not re.match(r"^\w+=", w) and Path(w).name != "env"]
    except ValueError:
        return False
    return bool(words) and bool(shutil.which(words[0]) or Path(words[0]).is_file())


def installed_browsers():
    """The usable apps that open https links, in the system's order of preference (each data
    folder's mimeinfo.cache, yours first; then any other entry that says it takes them)."""
    found = []
    for d in data_dirs():
        try:
            lines = (Path(d) / "applications/mimeinfo.cache").read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if line.startswith("x-scheme-handler/https="):
                found += [a for a in line.split("=", 1)[1].split(";") if a and a not in found]
    for d in data_dirs():
        for f in sorted((Path(d) / "applications").glob("*.desktop")):
            if f.name in found or not f.is_file():         # (a link to an app since removed, say)
                continue
            try:
                takes = "x-scheme-handler/https" in entry(f).get("MimeType", "")
            except OSError:                                # (one it can't read: the others still count)
                continue
            if takes:
                found.append(f.name)
    return [a for a in found if usable(a)]


def browser_choice():
    """(browser, unusable default): the default browser; or, when that's no browser (a
    placeholder, or uninstalled) or none is set, an installed one, one already running first,
    with the default it stands in for ("" for none set). (None, …) without any browser."""
    default = default_browser()
    if usable(default):
        return default, None
    others = installed_browsers()
    others.sort(key=lambda a: not running_sessions(a))       # (stable: running ones first)
    choice = others[0] if others else None
    if choice:
        STOOD_IN[choice] = default or ""      # (for launch's note, without asking the system again)
    return choice, default or ""


STOOD_IN = {}           # browser chosen → the unusable default it stood in for ("" for none set)


def target_app(target):
    """The default app for a URL, folder or file."""
    if target.startswith("file://"):
        target = urllib.parse.unquote(target[7:])
    if re.match(r"^[a-z][a-z0-9+.-]*://", target):
        return browser_choice()[0]
    if os.path.isdir(target):
        return default_app("inode/directory")
    kind = xdg_mime("query", "filetype", target)
    return default_app(kind) if kind else None


def data_dirs():
    """Where desktop entries live: XDG_DATA_HOME, XDG_DATA_DIRS, and Flatpak's exports (a
    session's XDG_DATA_DIRS can leave them out)."""
    dirs = [os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")]
    dirs += (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    for extra in (str(Path.home() / ".local/share/flatpak/exports/share"), "/var/lib/flatpak/exports/share"):
        if extra not in dirs:
            dirs.append(extra)
    return [d for d in dirs if d]


def desktop_file(app_id):
    for d in data_dirs():
        f = Path(d) / "applications" / app_id
        if f.is_file():
            return f
    return None


def entry(path):
    """The [Desktop Entry] keys of a desktop file."""
    keys, inside = {}, False
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("["):
            inside = line.strip() == "[Desktop Entry]"
        elif inside and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            keys.setdefault(k.strip(), v.strip())
    return keys


def matcher(keys):
    """A test for whether a process belongs to the browser: its Flatpak id, or its program's name."""
    if keys.get("X-Flatpak"):
        app = keys["X-Flatpak"]
        return lambda pid, env: env.get("FLATPAK_ID") == app
    try:
        words = shlex.split(keys.get("Exec", ""))
    except ValueError:
        words = []
    words = [w for w in words if not re.match(r"^\w+=", w) and Path(w).name not in WRAPPERS]
    if not words:
        return lambda pid, env: False
    name = Path(words[0]).name
    if name in SHELLS:                        # ("sh -c …": every shell would match; can't tell)
        return lambda pid, env: False
    return lambda pid, env: Path((proc_cmd(pid) or [""])[0]).name == name     # (read once: it may just have ended)


def running_sessions(app_id):
    path = desktop_file(app_id)
    if not path:
        return set()
    test, found = matcher(entry(path)), set()
    for pid in pids():
        if pid == os.getpid():
            continue
        env = proc_env(pid)
        if env and test(pid, env):
            s = session_of(env)
            if s:
                found.add(s)
    return found


def session_env(target):
    """Our environment with the target session's display keys, taken from one of its programs."""
    own = dict(os.environ)
    if session_of(own) == target:
        return own
    for pid in pids():
        cmd = proc_cmd(pid)
        if cmd and Path(cmd[0]).name in REFERENCE[target]:
            ref = proc_env(pid)
            if ref and session_of(ref) == target:
                for k in SESSION_KEYS:
                    own.pop(k, None)
                    if k in ref:
                        own[k] = ref[k]
                return own
    return None


def plan(url):
    """(app desktop id, session, environment) for opening url (or a path), or None without an app."""
    app = target_app(url)
    if not app:
        return None
    own = session_of(os.environ) or DESKTOP
    target = choose(own, running_sessions(app))
    env = session_env(target)
    if env is None:                      # that session isn't up: use ours
        target, env = own, dict(os.environ)
    return app, target, env


def browser_name(app_id):
    path = desktop_file(app_id)
    return (i18n.entry_name(entry(path)) if path else None) or app_id.removesuffix(".desktop")


LOG = Path.home() / ".local/state/frame-tweaks/logs/links.log"


def log(msg):
    """What happened to each link (for a bug report: it's in the diagnostics report)."""
    ftconf.append_log(LOG, msg, max_bytes=50_000, stamp="%Y-%m-%d %H:%M:%S")


def launch(url):
    """Opens url: (note, process, handoff) or None when it couldn't (the caller falls back to its
    own way). handoff: the app already runs there, so the process should only pass the link on
    and exit; one still running after a few seconds is stuck (Firefox: "already running, but is
    not responding", when its running copy doesn't answer): see still_stuck."""
    p = plan(url)
    if not p:
        log(f"no plan for {url!r}: no default app found")
        return None
    app, target, env = p
    handoff = target in running_sessions(app)
    before = {pid for pid in pids() if url in proc_cmd(pid)}   # (e.g. a browser first started with this link)
    try:
        proc = subprocess.Popen(["gtk-launch", app, url], env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError as e:
        log(f"couldn't start {app} for {url!r}: {e}")
        return None
    proc.had_link = before                     # (still_stuck leaves those alone)
    log(f"{url!r} -> {app} in {target} (from {session_of(os.environ)}; {'hand-off' if handoff else 'new window'})")
    note = _("Opened in {app} ({session})").format(app=browser_name(app), session=_(target))
    # proc.warning: the default isn't a browser (it stood in for it): what to set, for the caller to show
    proc.warning = ""
    if re.match(r"^[a-z][a-z0-9+.-]*://", url) and not url.startswith("file://"):
        default = STOOD_IN.pop(app, None)
        if default is not None:
            log(f"the default browser {default or '(none set)'} can't open links; used {app}")
            proc.warning = (_("Your default browser, {default}, can't open links, so {app} did. Choose one in "
                              "System Settings → Default Applications → Web browser.") if default else
                            _("No default browser is set, so {app} opened it. Choose one in System Settings → "
                              "Default Applications → Web browser.")).format(
                                  default=browser_name(default) if default else "", app=browser_name(app))
    return note, proc, handoff


def still_stuck(proc, url):
    """After a hand-off: True if the launched copy is still up (it shows "not responding" instead
    of passing the link on); those processes (ones with this link on their command line) are
    stopped. gtk-launch itself exits at once, so it's the browser's own processes that tell. Ones
    that had the link before the launch aren't its: the running browser, if this link started it."""
    import signal
    stuck = [pid for pid in pids() if pid != os.getpid() and pid not in getattr(proc, "had_link", ())
             and url in proc_cmd(pid)]
    for pid in stuck:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    if stuck:
        log(f"{url!r}: the running copy didn't answer; stopped the stuck launch ({len(stuck)} processes)")
    return bool(stuck)


def open_url(url):
    """Opens url; returns a short note on where it went (and what to set, when the default isn't
    a browser), or None when it couldn't (the caller falls back to its own way)."""
    r = launch(url)
    return " ".join(filter(None, (r[0] + ".", getattr(r[1], "warning", "")))) if r else None


def open_path(path):
    """open_url for a folder or file (a path or a file:// URL)."""
    if path.startswith("file://"):
        path = urllib.parse.unquote(path[7:])
    return open_url(os.path.abspath(path))


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0)
    if args[0] == "--where":
        p = plan(args[1] if len(args) > 1 else "https://example.com")
        if not p:
            sys.exit(_("No default app found."))
        app = p[0]
        default = browser_choice()[1]
        print(f"app: {app}; running in: {', '.join(sorted(running_sessions(app))) or 'neither'}; "
              f"this program: {session_of(os.environ)}; would open in: {p[1]}"
              + (f"; default browser {default or '(none set)'} can't open links, so this one instead"
                 if default is not None and "://" in (args[1] if len(args) > 1 else "https:") else ""))
    else:
        note = open_url(args[0]) if "://" in args[0] and not args[0].startswith("file:") else open_path(args[0])
        print(note or _("Couldn't open it."))
        sys.exit(0 if note else 1)
