"""Your edits to a menu entry (a .desktop file), kept when Frame Tweaks writes the entry again.

Frame Tweaks keeps a copy of the entry as it last wrote it. Whatever the entry says differently
now is yours (a new name or icon from KDE's menu editor, an option added to its command), and
goes into the new version too: a three-way merge, key by key, with that copy as the common
ancestor. The entry's file name is its identity: KDE's menu editor saves a rename into the same
file. (wallet-launcher, lib/common.sh install_desktop; installed beside i18n.py: install_i18n.)

  menuedits.py keep CURRENT BASE < NEW    # NEW with your edits to CURRENT since BASE, on stdout
"""
import shlex
import sys
from pathlib import Path

# Put in the keyboard's language by lib/i18n.py relabel, from the entry's X-Frame-Tweaks-<key>
# English (its MENU_KEYS): such a change isn't yours.
LABELS = ("Name", "GenericName", "Comment")
_KEEP = object()


def keys(text):
    """{(group, key): value} for the key lines of an entry, in file order."""
    entry, group = {}, ""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            group = s[1:-1]
        elif s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            entry[(group, k.strip())] = v.strip()
    return entry


def translations_of(english):
    """Every language file's translation of english (lib/i18n.py, beside this file), or none."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import i18n
        return i18n.translations_of(english)
    except Exception:                         # (no i18n.py, or no language files: the entry's own)
        return set()


def frame_label(entry, group, key, value):
    """value is a label Frame Tweaks gave key (its English, or a translation: the entry's own or any
    language file's, as an entry installed before a language was added has no line for it), not
    one you typed. entry: keys(). (lib/i18n.py relabel goes by the same rule.)"""
    english = entry.get((group, f"X-Frame-Tweaks-{key}"))
    return english is not None and (value == english or any(
        g == group and k.startswith(f"{key}[") and v == value for (g, k), v in entry.items())
        or value.strip() in translations_of(english.strip()))


def _same(group, key, old, new, base):
    """old and new mean the same: a command written another way (KDE's menu editor writes the
    whole command again when it saves an entry), or a label put in another language."""
    if key == "Exec":
        try:
            return shlex.split(old) == shlex.split(new)
        except ValueError:
            return False
    return key in LABELS and frame_label(base, group, key, new)


def yours(base, current):
    """Your edits: what changed from base (the entry as Frame Tweaks last wrote it) to current,
    as {(group, key): your value, or None for a line you removed}."""
    b, c = keys(base), keys(current)
    edits = {}
    for gk in [*c, *(gk for gk in b if gk not in c)]:
        old, new = b.get(gk), c.get(gk)
        if old != new and (old is None or new is None or not _same(*gk, old, new, b)):
            edits[gk] = new
    return edits


def with_yours(text, edits, owned=(), command=None):
    """text (a new version of the entry) with your edits: a line you changed has your value, one
    you removed goes, one you added joins its group (a group of yours goes at the end). owned:
    keys text keeps as it has them. command(group, your command): the Exec line's value for a
    command you changed, or None for text's. (An entry keeps its command: removing it isn't
    carried over.)"""
    def mine(gk):                          # your value for gk, None to remove it, or _KEEP
        group, key = gk
        v = edits[gk]
        if key in owned or (key == "Exec" and v is None):
            return _KEEP
        if key == "Exec" and command:
            v = command(group, v)
            return _KEEP if v is None else v
        return v

    out, group, done = [], "", set()

    def add_new():                         # your lines for this group that text hasn't: at its end
        new = []
        for gk in edits:
            if gk[0] == group and gk not in done:
                done.add(gk)
                v = mine(gk)
                if v is not None and v is not _KEEP:
                    new.append(f"{gk[1]}={v}")
        end = len(out)
        while end and not out[end - 1].strip():      # (before the blank lines between groups)
            end -= 1
        out[end:end] = new

    for line in text.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            add_new()
            group = s[1:-1]
        elif s and not s.startswith("#") and "=" in s and (group, s.split("=", 1)[0].strip()) in edits:
            gk = (group, s.split("=", 1)[0].strip())
            done.add(gk)
            v = mine(gk)
            if v is None:
                continue
            if v is not _KEEP:
                line = f"{gk[1]}={v}"
        out.append(line)
    add_new()
    for group in dict.fromkeys(g for g, k in edits if (g, k) not in done):     # groups text hasn't
        start = len(out)
        out += ["", f"[{group}]"]
        add_new()
        if len(out) == start + 2:          # (only removals: nothing to show)
            del out[start:]
    return "\n".join(out) + "\n"


def merge(base, new, current, owned=(), command=None, words=shlex.split):
    """new (the entry as Frame Tweaks writes it now), with your edits: what current (the entry in
    the menu) says differently from base (as Frame Tweaks last wrote it). A command you changed
    stays yours unless the new version changed it too: then it's the new one, as yours may not
    run any more (a program moved, an option gone). words(command): how a command reads, to tell
    whether it changed. owned, command: as with_yours."""
    edits, b, n = yours(base, current), keys(base), keys(new)
    for gk in [gk for gk in edits if gk[1] == "Exec"]:
        try:
            changed = words(b.get(gk, "")) != words(n.get(gk, ""))
        except ValueError:
            changed = True
        if changed:
            del edits[gk]
    return with_yours(new, edits, owned, command)


if __name__ == "__main__":
    if sys.argv[1:2] == ["keep"] and len(sys.argv) == 4:
        new = sys.stdin.read()
        try:                                  # (either missing: nothing to tell yours by)
            current, base = Path(sys.argv[2]).read_text(), Path(sys.argv[3]).read_text()
        except (OSError, UnicodeDecodeError):
            sys.stdout.write(new)
        else:
            sys.stdout.write(merge(base, new, current))
    else:
        sys.exit("menuedits.py keep CURRENT BASE < NEW")
