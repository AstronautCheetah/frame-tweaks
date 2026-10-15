"""Settings files and logs, kept one way by every Frame Tweaks program: the installer (sft.py),
the window, and the programs tweaks install (which find this file beside i18n.py in
~/.local/share/frame-tweaks/i18n: lib/common.sh install_i18n).

- JSON settings (~/.config/arrowpad.json, snip.json, …): an object; anything else in the file
  (null, a list, half a file) reads as no settings, rather than crashing whoever reads it.
- Shell settings (KEY=value lines, which scripts also source: phone.conf, speech.conf, …):
  other lines are kept as they are; values are quoted only where they must be.
- Writes go to a new file that then replaces the old one, so a crash can't leave half a file.
- Logs rotate: past max_bytes, the log becomes NAME.1 and a new one starts."""
import json
import os
import shlex
import tempfile
import time
from pathlib import Path


def write_text(path, text):
    """path's new content, all at once (a link is written through, not replaced)."""
    path = Path(path)
    if path.is_symlink():
        path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        try:
            os.chmod(tmp, path.stat().st_mode & 0o777)     # (the file's own permissions, if it had any)
        except OSError:
            os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_json(path):
    """The settings object in path; {} when there's none, or it isn't an object."""
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def update_json(path, changes=None, drop=()):
    """Set these keys and remove those (other keys kept); returns the whole object."""
    data = read_json(path)
    for k in drop:
        data.pop(k, None)
    data.update(changes or {})
    write_text(path, json.dumps(data) + "\n")
    return data


def _value(text):
    """A shell value as text: K='a b' → a b, K=a → a (as `source` would read it)."""
    try:
        words = shlex.split(text)
    except ValueError:
        return text.strip().strip("'\"")
    return " ".join(words)


def read_shell(path):
    """{KEY: value} from a file of KEY=value lines (comments and other lines skipped)."""
    out = {}
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        return out
    for line in lines:
        k, eq, v = line.partition("=")
        k = k.strip()
        if eq and k and not k.startswith("#") and " " not in k:
            out[k] = _value(v)
    return out


def set_shell(path, changes=None, drop=()):
    """Set KEY=value lines (where the key was, else at the end) and remove those of drop, keeping
    every other line as it is."""
    changes = {k: str(v) for k, v in (changes or {}).items()}
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        lines = []
    out, done = [], set()
    for line in lines:
        k = line.partition("=")[0].strip()
        if k in changes:
            if k not in done:
                out.append(f"{k}={shlex.quote(changes[k])}")
                done.add(k)
            continue
        if k in drop:
            continue
        out.append(line)
    out += [f"{k}={shlex.quote(v)}" for k, v in changes.items() if k not in done]
    write_text(path, "".join(f"{line}\n" for line in out))


def append_log(path, line, max_bytes=200_000, stamp="%H:%M:%S"):
    """One line, after the time (stamp: strftime; "%H:%M:%S.ms" adds milliseconds), in a log
    that rotates past max_bytes. Never raises: a log mustn't stop what it logs."""
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > max_bytes:
            path.replace(path.with_name(path.name + ".1"))
        now = time.time()
        when = time.strftime(stamp.replace(".ms", ""), time.localtime(now))
        if stamp.endswith(".ms"):
            when += f".{int(now * 1000) % 1000:03d}"
        with open(path, "a") as f:
            f.write(f"{when} {line}\n")
    except OSError:
        pass
