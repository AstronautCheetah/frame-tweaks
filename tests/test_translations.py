"""Every translation in locale/*.po keeps its English text's placeholders, so a translator's slip
can't crash a program that is shown in that language: `_("{n} tweaks").format(n=n)` raises
KeyError on a {name} the English doesn't have, and `"%d tweaks" % n` raises TypeError (the
shell's printf repeats the message instead) when the %s/%d specifiers differ."""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRACE = re.compile(r"(?<!\{)\{([A-Za-z_]\w*)?(?:[!:][^{}]*)?\}(?!\})")     # {name}, {name:>3}; not {{
# (dev/i18n.py's rule) A text printf or Python's % formats has a conversion or a %% in its English;
# in it, a translation's "100 % de" is a conversion too (the space flag). In other text a % is
# just a percent sign: "50% de" in a manifest's text is fine.
FORMAT_TEXT = re.compile(r"%(?:\([A-Za-z_]\w*\))?[-#0+]*\d*(?:\.\d+)?[sdifxXr]|%%")
PRINTF = re.compile(r"%(?:\([A-Za-z_]\w*\))?[-#0+ ']*\d*(?:\.\d+)?[sdifxXr]")


def specs(text, english=None):
    if not FORMAT_TEXT.search(english if english is not None else text):
        return []
    return sorted(PRINTF.findall(text.replace("%%", "")))


def entries(text):
    """(msgid, msgid_plural or None, [msgstr…]) for each translated, non-fuzzy entry."""
    out, entry, field, fuzzy = [], {}, None, False
    for line in text.splitlines() + [""]:
        line = line.strip()
        if not line:
            strs = [v for k, v in sorted(entry.items()) if k.startswith("msgstr") and v]
            if entry.get("msgid") and strs and not fuzzy:
                out.append((entry["msgid"], entry.get("msgid_plural"), strs))
            entry, field, fuzzy = {}, None, False
        elif line.startswith("#,"):
            fuzzy = "fuzzy" in line
        elif line.startswith('"') and field:
            entry[field] += ast.literal_eval(line)
        elif not line.startswith("#"):
            field, value = line.split(None, 1)
            entry[field] = ast.literal_eval(value)
    return out


class Placeholders(unittest.TestCase):
    def test_translations_keep_the_placeholders(self):
        files = sorted((ROOT / "locale").glob("*.po"))
        self.assertTrue(files)
        for po in files:
            for msgid, plural, strs in entries(po.read_text(encoding="utf-8")):
                english = msgid + (plural or "")
                for s in strs:
                    with self.subTest(po=po.name, msgid=msgid[:60]):
                        # A translation may leave a {name} out (unused arguments are fine), but
                        # never add or rename one.
                        self.assertLessEqual(set(BRACE.findall(s)), set(BRACE.findall(english)))
                        # Specifiers exactly as in the English (either form, for a plural one).
                        self.assertIn(specs(s, english), [specs(msgid), specs(plural or msgid)])


if __name__ == "__main__":
    unittest.main()
