"""lib/xkb.py: which key, and which modifiers, type a character on a keyboard layout, worked out
with libxkbcommon as KWin does (Arrow Pad's shortcuts and Dictation's typing on non-US layouts).
The layouts are XKB's own (xkeyboard-config); skipped where libxkbcommon or they are missing."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT, sandbox_env  # noqa: E402
import xkb  # noqa: E402  (lib/, put on sys.path by helpers)


def compiles():
    try:
        xkb.Keymap("fr")
        return True
    except OSError:
        return False


def composes():
    """The compose table programs use for dead keys is here (libX11's, /usr/share/X11/locale)."""
    x = xkb.library()
    ctx = x.xkb_context_new(0)
    table = x.xkb_compose_table_new_from_locale(ctx, b"C.UTF-8", 0)
    if table:
        x.xkb_compose_table_unref(table)
    x.xkb_context_unref(ctx)
    return bool(table)


S, G = xkb.SHIFT, xkb.ALTGR
# The keys (Linux key codes, as ydotool sends them) for these characters on each layout.
TYPED = {
    "us": {"a": 30, "q": 16, "z": 44, "y": 21, "w": 17, "m": 50, "?": (S, 53), "!": (S, 2), ":": (S, 39),
           ";": 39, "'": 40, '"': (S, 40), "é": None},
    "fr": {"a": 16, "q": 30, "z": 17, "y": 21, "w": 44, "m": 39, "?": (S, 50), "!": 53, ":": 52, ";": 51,
           "'": 5, '"': 4, "é": 3},
    "de": {"a": 30, "q": 16, "z": 21, "y": 44, "w": 17, "m": 50, "?": (S, 12), "!": (S, 2), ":": (S, 52),
           ";": (S, 51), "'": (S, 43), '"': (S, 3), "é": "dead"},
    "latam": {"a": 30, "q": 16, "z": 44, "y": 21, "w": 17, "m": 50, "?": (S, 12), "!": (S, 2), ":": (S, 52),
              ";": (S, 51), "'": 12, '"': (S, 3), "é": "dead"},
}
# é where the layout has no key of its own for it: a dead key (´), then e.
DEAD_ACUTE = {"de": [(13, ()), (18, ())], "latam": [(26, ()), (18, ())]}


@unittest.skipUnless(compiles(), "needs libxkbcommon and XKB's layouts")
class Layouts(unittest.TestCase):
    def test_characters_on_each_layout(self):
        for layout, chars in TYPED.items():
            km = xkb.Keymap(layout)
            for ch, want in chars.items():
                with self.subTest(layout=layout, char=ch):
                    got = km.keys(ch)
                    if want == "dead":
                        self.assertEqual(got, DEAD_ACUTE[layout] if composes() else None)
                    elif want is None:
                        self.assertIsNone(got)
                    else:
                        mods, code = (want[:-1], want[-1]) if isinstance(want, tuple) else ((), want)
                        self.assertEqual(got, [(code, mods)])

    def test_ydotool_events(self):
        """Each key pressed and let go, inside its modifiers; nothing at all if a character has no key."""
        km = xkb.Keymap("fr")
        self.assertEqual(km.ydotool("Qa"), ["42:1", "30:1", "30:0", "42:0", "16:1", "16:0"])
        self.assertEqual(km.ydotool("@"), ["100:1", "11:1", "11:0", "100:0"])         # AltGr+à
        with self.assertRaises(xkb.Untypeable) as e:
            km.ydotool("a漢b漢")
        self.assertEqual(str(e.exception), "漢")

    def test_only_keys_the_desktop_gets(self):
        """Not the Euro or other media keys above X11's 255 (they never arrive), nor the keypad's
        "+" where the typing keys have one."""
        km = xkb.Keymap("us")
        self.assertEqual(km.keys("#"), [(4, (S,))])
        self.assertEqual(km.keys("+"), [(13, (S,))])
        self.assertIsNone(km.keys("€"))
        self.assertEqual(xkb.Keymap("de").keys("€"), [(18, (G,))])

    def test_shortcut_letters(self):
        self.assertEqual([xkb.Keymap("fr").letter(c) for c in "azqwm"], [16, 17, 30, 44, 39])
        self.assertIsNone(xkb.Keymap("ru").letter("a"))         # (no Latin letters: the US keys, then)
        self.assertIsNone(xkb.Keymap("de").letter("A"))         # (unshifted only)

    def test_a_layout_it_cant_compile(self):
        with self.assertRaises(OSError), mock.patch.dict(os.environ, {"XKB_LOG_LEVEL": "critical"}):
            xkb.Keymap("no-such-layout")


@unittest.skipUnless(compiles(), "needs libxkbcommon and XKB's layouts")
class CurrentLayout(unittest.TestCase):
    """KDE's current layout (kxkbrc), looked at no more than once every 5 s, for Arrow Pad."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.config = Path(tmp.name)
        for p in (mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp.name}),
                  mock.patch.dict(xkb._current, {"at": None, "kb": None})):
            p.start()
            self.addCleanup(p.stop)

    def test_letter_keys(self):
        self.assertEqual(xkb.letter_key("A", 30), 30)                       # no kxkbrc: a US keyboard
        (self.config / "kxkbrc").write_text("[Layout]\nLayoutList=fr\nUse=true\n")
        self.assertEqual(xkb.letter_key("A", 30), 30)                       # (not looked at again yet)
        xkb._current["at"] -= xkb.CHECK_EVERY
        self.assertEqual(xkb.letter_key("A", 30), 16)
        with mock.patch.dict(xkb._lib, {"lib": None}), mock.patch.dict(xkb._keymaps, clear=True):
            self.assertEqual(xkb.letter_key("A", 30), 30)                   # no libxkbcommon: the US key
        (self.config / "kxkbrc").write_text("[Layout]\nLayoutList=ru\n")
        xkb._current["at"] = None
        self.assertEqual(xkb.letter_key("A", 30), 30)


@unittest.skipUnless(compiles(), "needs libxkbcommon and XKB's layouts")
class Command(unittest.TestCase):
    """xkb.py ydotool TEXT, as Dictation runs it: exit 3 for the plain US layout (ydotool type
    then), 0 and the key events, or 2 and the characters the layout has no key for."""

    def run_xkb(self, kxkbrc, text):
        with tempfile.TemporaryDirectory() as home:
            if kxkbrc:
                (Path(home) / ".config").mkdir()
                (Path(home) / ".config/kxkbrc").write_text(kxkbrc)
            r = subprocess.run([sys.executable, str(ROOT / "lib/xkb.py"), "ydotool", text],
                               env=sandbox_env(home), capture_output=True, text=True, timeout=60)
        return r.returncode, r.stdout.strip()

    def test_exit_codes(self):
        self.assertEqual(self.run_xkb(None, "Hello"), (3, ""))
        self.assertEqual(self.run_xkb("[Layout]\nLayoutList=us\n", "Hello"), (3, ""))
        self.assertEqual(self.run_xkb("[Layout]\nLayoutList=fr\n", "aQ"), (0, "16:1 16:0 42:1 30:1 30:0 42:0"))
        self.assertEqual(self.run_xkb("[Layout]\nLayoutList=us\nVariantList=intl\n", "'")[0], 0)   # (' is a dead key)
        self.assertEqual(self.run_xkb("[Layout]\nLayoutList=fr\n", "a漢"), (2, "漢"))


if __name__ == "__main__":
    unittest.main()
