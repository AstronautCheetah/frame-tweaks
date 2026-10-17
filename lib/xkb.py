"""Typing on the desktop's keyboard layout. Arrow Pad and Dictation send keys as key codes (the
kernel's numbers, through ydotoold), and the desktop turns each into a character with its own
layout: the key that types "a" on a US keyboard types "q" on a French one, so Ctrl+A was Ctrl+Q
(Quit) there, and dictated text came out with the wrong letters. Which key, and which modifiers
(Shift, AltGr), type a character on KDE's current layout is worked out here with libxkbcommon
(SteamOS has it), from kxkbrc as KWin reads it (lib/i18n.py kde_keyboard). A character with no key
of its own is typed with a dead key where the layout has one (´ then e for é), as people type it.

Installed beside i18n.py (lib/common.sh install_i18n), for the programs tweaks install.
Dictation runs `python3 xkb.py ydotool TEXT`: the `ydotool key` events that type TEXT; and before
typing, `python3 xkb.py let-go`: those that let go of the modifiers held down on ydotoold's
keyboard (Arrow Pad's latched Ctrl turned dictated text into shortcuts: Ctrl+W, Ctrl+Q)."""
import ctypes
import fcntl
import glob
import os
import sys
import time
import unicodedata

SHIFT, ALTGR = 42, 100           # KEY_LEFTSHIFT, KEY_RIGHTALT (AltGr), as ydotool numbers them
ENTER, TAB = 28, 15
RIGHT_CTRL = 97                  # never sent, whatever a layout puts on it: it toggles desktop mode's input grab
LEVELS = ((), (SHIFT,), (ALTGR,), (SHIFT, ALTGR))     # the modifiers tried, fewest first
CHECK_EVERY = 5.0                # seconds: Arrow Pad looks at the layout no more than once per this
KEYPAD = range(0xff80, 0xffbe)   # keypad keysyms: KP_Add types "+" too, but isn't a typing key
DEAD = range(0xfe50, 0xfe94)     # dead keysyms (dead_grave … dead_longsolidusoverlay)
# Let go before typing: Shift (both), Ctrl; then Alt, AltGr and Super (both), which go up while F24
# (bound to nothing) is down: let go alone, they'd be a tap (a menu bar, the app launcher). Same keys
# as lib/common.sh's clear_stuck_modifiers, and never Right Ctrl.
PLAIN_MODIFIERS = (42, 54, 29)
TAP_MODIFIERS = (56, 100, 125, 126)
F24 = 194
YDOTOOLD = "ydotoold virtual device"     # (the name of ydotoold's keyboard)
KEY_MAX = 0x2ff


class Names(ctypes.Structure):
    _fields_ = [(f, ctypes.c_char_p) for f in ("rules", "model", "layout", "variant", "options")]


_lib = {}


def library():
    """libxkbcommon, or None where it can't be loaded."""
    if "lib" not in _lib:
        try:
            x = ctypes.CDLL("libxkbcommon.so.0")
        except OSError:
            _lib["lib"] = None
            return None
        p, u32 = ctypes.c_void_p, ctypes.c_uint32
        for name, res, args in (("xkb_context_new", p, [ctypes.c_int]), ("xkb_context_unref", None, [p]),
                                ("xkb_keymap_new_from_names", p, [p, ctypes.POINTER(Names), ctypes.c_int]),
                                ("xkb_keymap_unref", None, [p]), ("xkb_keymap_min_keycode", u32, [p]),
                                ("xkb_keymap_max_keycode", u32, [p]), ("xkb_state_new", p, [p]),
                                ("xkb_state_unref", None, [p]), ("xkb_state_update_key", ctypes.c_int, [p, u32, ctypes.c_int]),
                                ("xkb_state_key_get_one_sym", u32, [p, u32]), ("xkb_state_key_get_utf32", u32, [p, u32]),
                                ("xkb_compose_table_new_from_locale", p, [p, ctypes.c_char_p, ctypes.c_int]),
                                ("xkb_compose_table_unref", None, [p]), ("xkb_compose_state_new", p, [p, ctypes.c_int]),
                                ("xkb_compose_state_unref", None, [p]), ("xkb_compose_state_reset", None, [p]),
                                ("xkb_compose_state_feed", ctypes.c_int, [p, u32]),
                                ("xkb_compose_state_get_status", ctypes.c_int, [p]),
                                ("xkb_compose_state_get_utf8", ctypes.c_int, [p, ctypes.c_char_p, ctypes.c_size_t])):
            f = getattr(x, name)
            f.restype, f.argtypes = res, args
        _lib["lib"] = x
    return _lib["lib"]


class Untypeable(ValueError):
    """Characters the layout has no keys for."""


class Keymap:
    """One keyboard layout, compiled as KWin compiles it (rules "evdev"), and which keys type which
    characters on it. Raises OSError without libxkbcommon, or for a layout it can't compile."""

    def __init__(self, layout, variant="", model="pc104", options=""):
        x = library()
        if x is None:
            raise OSError("libxkbcommon isn't available")
        self.x, self.layout, self.variant = x, layout, variant or ""
        # (XKB_CONTEXT_NO_ENVIRONMENT_NAMES: the names given here, not XKB_DEFAULT_* of this process)
        self.ctx = x.xkb_context_new(2)
        names = Names(b"evdev", (model or "pc104").encode(), layout.encode(), self.variant.encode(),
                      (options or "").encode())
        km = x.xkb_keymap_new_from_names(self.ctx, ctypes.byref(names), 0) if self.ctx else None
        if not km:
            raise OSError(f"no keyboard layout {layout}({variant})")
        # Every key at every level: the character it types (direct), and the dead keys (dead). Keys
        # up to XKB's 255 only: the desktop gets them through X11, which has no higher key codes
        # (the Euro and other media keys above it never arrive).
        self.direct, self.dead, self.syms = {}, {}, {}
        found = {}
        for mods in LEVELS:
            st = x.xkb_state_new(km)
            for m in mods:
                x.xkb_state_update_key(st, m + 8, 1)          # (XKB numbers keys 8 above the kernel)
            for kc in range(max(9, x.xkb_keymap_min_keycode(km)), min(255, x.xkb_keymap_max_keycode(km)) + 1):
                sym, cp = x.xkb_state_key_get_one_sym(st, kc), x.xkb_state_key_get_utf32(st, kc)
                if kc - 8 == RIGHT_CTRL:
                    continue
                if sym in DEAD:
                    self.dead.setdefault(sym, (kc - 8, mods))
                elif 0x20 <= cp and cp != 0x7f:               # (no Return, Tab, Escape, Delete…)
                    # The typing keys first (up to F12's 88; not the keypad, nor an extra "(" key),
                    # then the fewest modifiers.
                    rank = (sym in KEYPAD, kc - 8 > 88, len(mods), kc)
                    if chr(cp) not in found or rank < found[chr(cp)][0]:
                        found[chr(cp)] = (rank, (kc - 8, mods), sym)
            x.xkb_state_unref(st)
        x.xkb_keymap_unref(km)
        self.direct = {ch: key for ch, (_rank, key, _sym) in found.items()}
        self.syms = {ch: sym for ch, (_rank, _key, sym) in found.items()}
        self.composed = {}

    def __del__(self):
        if getattr(self, "ctx", None):
            self.x.xkb_context_unref(self.ctx)

    def letter(self, ch):
        """The key that types ch with no modifier (for Ctrl+letter shortcuts), or None."""
        key = self.direct.get(ch)
        return key[0] if key and not key[1] else None

    def keys(self, ch):
        """The keys that type ch, in order: [(code, modifiers)], or None if it has none."""
        if ch == "\n":
            return [(ENTER, ())]
        if ch == "\t":
            return [(TAB, ())]
        if ch in self.direct:
            return [self.direct[ch]]
        if ch not in self.composed:
            self.composed[ch] = self.compose(ch)
        return self.composed[ch]

    def compose(self, ch):
        """A dead key, then another key (é: ´ then e; ^: ^ then space; ´: ´ twice), checked against
        the compose table programs use (the locale's, as Qt reads it), or None."""
        if not self.dead or len(ch) != 1:
            return None
        x = self.x
        locale = os.environ.get("LC_ALL") or os.environ.get("LC_CTYPE") or os.environ.get("LANG") or "C.UTF-8"
        table = None
        for loc in dict.fromkeys((locale, "C.UTF-8")):
            table = x.xkb_compose_table_new_from_locale(self.ctx, loc.encode(), 0)
            if table:
                break
        if not table:
            return None
        state = x.xkb_compose_state_new(table, 0)
        buf = ctypes.create_string_buffer(16)
        try:
            # after the dead key: the letter it accents, a space, or the dead key again
            base = unicodedata.normalize("NFD", ch)[0]
            then = [(self.syms[c], self.direct[c]) for c in dict.fromkeys((base, " ")) if c in self.direct]
            for dead_sym, dead_key in sorted(self.dead.items(), key=lambda d: (len(d[1][1]), d[1][0])):
                for sym, key in then + [(dead_sym, dead_key)]:
                    x.xkb_compose_state_reset(state)
                    x.xkb_compose_state_feed(state, dead_sym)
                    x.xkb_compose_state_feed(state, sym)
                    # (2: XKB_COMPOSE_COMPOSED)
                    if x.xkb_compose_state_get_status(state) == 2 and x.xkb_compose_state_get_utf8(state, buf, 16) > 0 \
                            and buf.value.decode("utf-8", "replace") == ch:
                        return [dead_key, key]
            return None
        finally:
            x.xkb_compose_state_unref(state)
            x.xkb_compose_table_unref(table)

    def ydotool(self, text):
        """`ydotool key` events (CODE:1 press, CODE:0 release) that type text; raises Untypeable."""
        out, missing = [], []
        for ch in text:
            keys = self.keys(ch)
            if keys is None:
                missing.append(ch)
                continue
            for code, mods in keys:
                out += [f"{m}:1" for m in mods] + [f"{code}:1", f"{code}:0"] + [f"{m}:0" for m in reversed(mods)]
        if missing:
            raise Untypeable("".join(dict.fromkeys(missing)))
        return out


def is_us(kb):
    """kb is the plain US layout (ydotool's own typing assumes it), or unknown (taken as US)."""
    return kb is None or (kb["layout"] == "us" and not kb["variant"])


def kde_keyboard():
    """KDE's current keyboard layout (lib/i18n.py kde_keyboard), or None where it can't be read."""
    try:
        import i18n              # (beside this file: on sys.path for the programs and for xkb.py run alone)
        return i18n.kde_keyboard()
    except Exception:            # (an unknown layout is typed as on a US keyboard, as before)
        return None


_current = {"at": None, "kb": None}
_keymaps = {}


def current():
    """The Keymap of KDE's current layout, looked at no more than once every CHECK_EVERY seconds;
    None for the plain US layout, or when it (or libxkbcommon) can't be read."""
    now = time.monotonic()
    if _current["at"] is None or now - _current["at"] >= CHECK_EVERY:
        _current.update(at=now, kb=kde_keyboard())
    kb = _current["kb"]
    if is_us(kb):
        return None
    key = tuple(sorted(kb.items()))
    if key not in _keymaps:
        try:
            _keymaps[key] = Keymap(**kb)
        except OSError:
            _keymaps[key] = None
    return _keymaps[key]


def letter_key(letter, us_code):
    """The key for a Ctrl+letter shortcut on the desktop's layout: the one that types `letter`
    there. us_code (its key on a US keyboard) when the layout or libxkbcommon can't be read, or
    the layout has no such key (a Cyrillic or Greek one: programs then match shortcuts by the US
    key, as KDE does)."""
    try:
        km = current()
        return (km.letter(letter.lower()) if km else None) or us_code
    except Exception:            # (a shortcut must still go out)
        return us_code


def key_bits(event):
    """The keys down on /dev/input/<event>, as the kernel's bitmap (EVIOCGKEY)."""
    bits = bytearray((KEY_MAX + 8) // 8)
    with open(f"/dev/input/{event}", "rb", buffering=0) as dev:
        fcntl.ioctl(dev, (2 << 30) | (len(bits) << 16) | (ord("E") << 8) | 0x18, bits)
    return bits


def keys_down(read=key_bits):
    """The keys the kernel has down on ydotoold's keyboard, or None where that can't be read:
    ydotoold isn't running, or its device can't be opened (only the input group can)."""
    down, found = set(), False
    for name in sorted(glob.glob(os.path.join(os.environ.get("FRAME_TWEAKS_INPUT", "/sys/class/input"),
                                              "event*", "device", "name"))):
        try:
            with open(name) as f:
                if f.read().strip() != YDOTOOLD:
                    continue
            bits = read(name.split(os.sep)[-3])
        except OSError:
            continue
        found = True
        down |= {code for code in range(len(bits) * 8) if bits[code // 8] >> (code % 8) & 1}
    return down if found else None


def let_go(down):
    """`ydotool key` events that let go of the modifiers in down (None, unknown: all of them, as
    the kernel drops the release of a key that's up; but F24 then goes down and up for nothing)."""
    plain = [f"{m}:0" for m in PLAIN_MODIFIERS if down is None or m in down]
    tap = [f"{m}:0" for m in TAP_MODIFIERS if down is None or m in down]
    return plain + ([f"{F24}:1", *tap, f"{F24}:0"] if tap else [])


def main(argv):
    """xkb.py ydotool TEXT: prints the `ydotool key` events that type TEXT on KDE's current layout
    (exit 0); exit 3 for the plain US layout (ydotool type is right there); exit 2, printing them,
    when characters have no key on the layout; 1 when the layout can't be compiled.
    xkb.py let-go: prints the `ydotool key` events that let go of the modifiers held down on
    ydotoold's keyboard (nothing when none is)."""
    if argv[1:] == ["let-go"]:
        print(" ".join(let_go(keys_down())))
        return 0
    if len(argv) != 3 or argv[1] != "ydotool":
        print("xkb.py ydotool TEXT | xkb.py let-go", file=sys.stderr)
        return 1
    kb = kde_keyboard()
    if is_us(kb):
        return 3
    try:
        print(" ".join(Keymap(**kb).ydotool(argv[2])))
    except OSError as e:
        print(e, file=sys.stderr)
        return 1
    except Untypeable as e:
        print(e)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
