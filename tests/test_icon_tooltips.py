"""Every button in the SteamVR dashboard patches (packs/*/*/*.js) whose face has no word on it
(a ⚙ drawn as an SVG, a ✕, a circle of colour) has a title: in VR the laser's hover tooltip is
the only way to learn what such a button does. The Qt windows' buttons are checked where each
window is built (helpers.untipped_icon_buttons: the installer window, Arrow Pad, Narrate, Wallet
apps, Memory limits).

Read from the source, not run: a button is an el('div' | 'span' | 'button', {props}, ...children)
whose props have an onClick (or phone-touch.js's own(), which brings one). Its face is a word when
a child is translated text (T(...)), a string with a letter or digit, or anything computed (a
label passed in: the caller's to name); an SVG, an image, a string of symbols alone, or no child
at all is not, and then the props need a title."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = sorted(ROOT.glob("packs/*/*/*.js"))
# Being reworked in another change: its gear, its settings' ✕, and the typing pad's ⌫ and ↵ (a
# label passed to key(), which this check can't see) have no title yet. Take it out of here once
# they do.
NOT_YET = set()
CALL = re.compile(r"\bel\(\s*'(?:div|span|button)'\s*,")
OPENERS, CLOSERS = "([{", ")]}"


def skip_string(s, i):
    """The index after the '...' or "..." starting at i."""
    q, i = s[i], i + 1
    while i < len(s) and s[i] != q:
        i += 2 if s[i] == "\\" else 1
    return i + 1


def skip_template(s, i):
    """The index after the `...` starting at i, its ${...} parts (templates in them too) skipped."""
    i += 1
    while i < len(s) and s[i] != "`":
        if s[i] == "\\":
            i += 2
        elif s.startswith("${", i):
            i = skip_group(s, i + 1)
        else:
            i += 1
    return i + 1


def skip_group(s, i):
    """The index after the bracket opened at i and its match, past strings, templates and comments
    (a comment's apostrophe isn't a quote)."""
    depth = 0
    while i < len(s):
        c = s[i]
        if c in "'\"":
            i = skip_string(s, i)
            continue
        if c == "`":
            i = skip_template(s, i)
            continue
        if s.startswith("//", i):
            i = s.find("\n", i)
            i = len(s) if i < 0 else i
            continue
        if s.startswith("/*", i):
            i = s.index("*/", i) + 2
            continue
        if c in OPENERS:
            depth += 1
        elif c in CLOSERS:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced")


def arguments(s):
    """The top-level comma-separated parts of an argument list's inside."""
    parts, start, i = [], 0, 0
    while i < len(s):
        c = s[i]
        if c in "'\"":
            i = skip_string(s, i)
        elif c == "`":
            i = skip_template(s, i)
        elif s.startswith("//", i):
            i = s.find("\n", i)
            i = len(s) if i < 0 else i
        elif c in OPENERS:
            i = skip_group(s, i)
        elif c == ",":
            parts.append(s[start:i])
            start = i = i + 1
        else:
            i += 1
    parts.append(s[start:])
    return [p.strip() for p in parts if p.strip()]


def strip_comments(s):
    return re.sub(r"^\s*//[^\n]*\n?", "", s, flags=re.M).strip()


def is_word(child):
    """Does this child put a word on the button's face?"""
    child = strip_comments(child)
    if re.match(r"el\(\s*'(?:svg|img|path)'", child):
        return False
    m = re.fullmatch(r"""'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)\"""", child)
    if m:
        return any(ch.isalnum() for ch in (m[1] if m[1] is not None else m[2]))
    return True                      # T(...), a label passed in, a nested element: the caller's


def untitled(text):
    """(line, first line of the call) for each button in a file's text with no word and no title."""
    found = []
    for m in CALL.finditer(text):
        paren = text.index("(", m.start())
        end = skip_group(text, paren)
        args = arguments(text[paren + 1:end - 1])
        props = args[1] if len(args) > 1 and args[1].startswith("{") else ""
        if not re.search(r"\bonClick\b|\.\.\.own\(", props):
            continue
        if re.search(r"(?:^|[{,\s])title\s*:", props):
            continue
        children = args[2:] if props else args[1:]
        if any(is_word(c) for c in children):
            continue
        line = text.count("\n", 0, m.start()) + 1
        found.append((line, text[m.start():].split("\n", 1)[0].strip()))
    return found


class DashboardButtons(unittest.TestCase):
    def test_every_button_without_a_word_has_a_title(self):
        self.assertGreater(len(FILES), 4)
        found = [f"{f.relative_to(ROOT)}:{line}: {start}" for f in FILES
                 if str(f.relative_to(ROOT)) not in NOT_YET for line, start in untitled(f.read_text())]
        self.assertEqual(found, [], "\n" + "\n".join(found))

    def test_the_check_finds_one(self):
        """(and leaves alone a button with a word, a title, or a label passed in, and what isn't a
        button at all)"""
        src = """
          const close = el('div', { ...tap(), onClick: () => shut(),
                                    style: { color: `hsl(${h}, 5%, ${on ? `${l}%` : '50%'})` } }, '✕');
          const gear = el('div', { key: 'g', onClick: open },
            // (it's the gear: an apostrophe here isn't a quote)
            el('svg', { width: 40 }, el('path', { d: GEAR })));
          const swatch = el('div', { key: 'c', onClick: () => save(v), style: { background: c } });
          const named = el('div', { ...own(fn), title: T('Close') }, '✕');
          const worded = el('div', { onClick: go }, T('Reset to defaults'));
          const digit = el('div', { onClick: go }, '2.5');
          const passed = el('div', { onClick, style: {} }, label);
          const strip = el('div', { style, onMouseDown: (ev) => grab(ev) }, '⠿');
        """
        self.assertEqual([line for line, _start in untitled(src)], [2, 4, 7])

    def test_every_file_scans(self):
        """(a bracket the scanner miscounts raises ValueError: a check that sees nothing passes)"""
        for f in FILES:
            with self.subTest(file=f.name):
                untitled(f.read_text())


if __name__ == "__main__":
    unittest.main()
