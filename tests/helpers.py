"""What many tests share: a stub command, the environment of a program run in a throwaway home,
and a program file loaded as a module. (Imported with tests/ on sys.path: see the top of any
test that uses it.)"""
import importlib.machinery
import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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
    """A Python program (with or without .py, e.g. packs/original/snip/frame-snip) as a module."""
    path = Path(path)
    name = name or path.stem.replace("-", "_")
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(module)
    return module
