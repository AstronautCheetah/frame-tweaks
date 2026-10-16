"""What many tests share: a stub command, the environment of a program run in a throwaway home,
and a program file loaded as a module. (Imported with tests/ on sys.path: see the top of any
test that uses it.)"""
import importlib.machinery
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# A test file run alone starts as the whole suite does: in English, with throwaway settings files
# (test_00_english.py, which runs first), and the shared modules in lib/ importable, as the
# programs loaded here find them beside i18n.py when installed.
import test_00_english  # noqa: E402,F401
if str(ROOT / "lib") not in sys.path:
    sys.path.insert(0, str(ROOT / "lib"))


def stub(folder, name, body):
    """folder/name: a bash script running body, made executable (a stand-in for a command)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    f = folder / name
    f.write_text(f"#!/bin/bash\n{body}\n")
    f.chmod(0o755)
    return f


def sandbox_env(home, stubs=None, path=("/usr/bin", "/bin"), **extra):
    """The environment for a program run in a throwaway home: nothing of this session's but USER,
    the stubs first on PATH, and English (whatever language this machine's keyboard or an open
    installer window has: their announcement is looked for in the home, not /run/user)."""
    home = Path(home)
    env = {"HOME": str(home), "USER": os.environ.get("USER", "u"), "LANG": "C.UTF-8",
           "PATH": os.pathsep.join(([str(stubs)] if stubs else []) + list(path)),
           "FRAME_TWEAKS_LANGUAGE": "en", "FRAME_TWEAKS_LANG_RESOLVED": "en", "FRAME_TWEAKS_KEYBOARD": "0",
           "FRAME_TWEAKS_ANNOUNCE_FILE": str(home / ".announced-language"),
           "FRAME_TWEAKS_PYLIB": str(ROOT / "lib")}      # (the shared modules: the repo's, not an installed copy)
    env.update({k: str(v) for k, v in extra.items()})
    return env


def load_script(path, name=None):
    """A Python program (with or without .py, e.g. packs/core/snip/frame-snip) as a module."""
    path = Path(path)
    name = name or path.stem.replace("-", "_")
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(module)
    return module


def kde_saves(text, group="Desktop Entry", **changes):
    """A menu entry (text) as KDE's menu editor saves it after changes (key=value, "_" for "-"):
    KConfig writes groups and keys sorted, without comments or blank lines, adds the editor's own
    keys, and writes the command again (here: field codes quoted, which reads the same)."""
    entry, g = {}, ""
    for line in text.splitlines():
        if line.startswith("["):
            g = line.strip()[1:-1]
        elif "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            entry[(g, k.strip())] = v.strip()
    entry.update({(group, k.replace("_", "-")): v for k, v in changes.items()})
    for k, v in (("Path", ""), ("Terminal", "false"), ("X-KDE-SubstituteUID", "false")):
        entry.setdefault((group, k), v)
    if (group, "Exec") in entry:
        entry[(group, "Exec")] = entry[(group, "Exec")].replace(" %U", " '%U'")
    out = []
    for g in sorted({g for g, _k in entry}):
        out += [f"[{g}]"] + [f"{k}={v}" for (gg, k), v in sorted(entry.items()) if gg == g] + [""]
    return "\n".join(out)
