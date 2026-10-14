#!/usr/bin/env python3
"""Open a web link in the default browser, in whichever session it's already running.

The Frame runs two sessions: Steam's VR session (X display :0, where floating windows live) and
the desktop mode (Plasma on Wayland, nested in VR). A browser started in one session can't hand
a link to a copy running in the other (Firefox then says it's "already running, but is not
responding"). So: find the default browser; if it's running in this program's session, send
the link there; if only in the other session, launch it with that session's environment so it
reaches the running copy; if it isn't running, open it in VR.

  browser.py URL             open it
  browser.py --where URL     say what it would do, without opening anything
"""
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

VR, DESKTOP = "VR", "desktop mode"
# What makes a program part of one session or the other; copied from a process of the target
# session (anything else is kept from ours).
SESSION_KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XDG_CURRENT_DESKTOP", "XDG_SESSION_TYPE",
                "XDG_SESSION_DESKTOP", "DESKTOP_SESSION", "KDE_FULL_SESSION", "KDE_SESSION_VERSION",
                "XDG_DESKTOP_PORTAL_DIR", "XAUTHORITY", "GDK_BACKEND", "QT_QPA_PLATFORM")
REFERENCE = {DESKTOP: ("plasmashell",), VR: ("steam", "steamwebhelper")}
WRAPPERS = {"env", "wallet-gate", "flatpak-spawn"}


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


def default_browser(env=None):
    """The default browser's desktop file id (e.g. org.mozilla.firefox.desktop), or None."""
    for kind in ("x-scheme-handler/https", "x-scheme-handler/http", "text/html"):
        try:
            out = subprocess.run(["xdg-mime", "query", "default", kind], env=env, capture_output=True,
                                 text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            out = ""
        if out.endswith(".desktop"):
            return out
    return None


def desktop_file(app_id):
    data = [os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))]
    data += os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":")
    for d in data:
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
    return lambda pid, env: bool(proc_cmd(pid)) and Path(proc_cmd(pid)[0]).name == name


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
    """(browser desktop id, session, environment) for opening url, or None when there's no browser."""
    app = default_browser()
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
    return (entry(path).get("Name") if path else None) or app_id.removesuffix(".desktop")


def open_url(url):
    """Opens url; returns a short note on where it went, or None when it couldn't (the caller
    falls back to its own way)."""
    p = plan(url)
    if not p:
        return None
    app, target, env = p
    try:
        subprocess.Popen(["gtk-launch", app, url], env=env, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        return None
    return f"Opened in {browser_name(app)} ({target})"


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0)
    if args[0] == "--where":
        p = plan(args[1] if len(args) > 1 else "https://example.com")
        if not p:
            sys.exit("No default browser found.")
        app = p[0]
        print(f"browser: {app}; running in: {', '.join(sorted(running_sessions(app))) or 'neither'}; "
              f"this program: {session_of(os.environ)}; would open in: {p[1]}")
    else:
        note = open_url(args[0])
        print(note or "Couldn't open it.")
        sys.exit(0 if note else 1)
