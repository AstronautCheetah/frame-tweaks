"""Text a window shows goes through _() (or ngettext/pgettext), so it can be translated: a
contributor who writes only English still writes it marked (locale/MARKING.md), and the
maintainers translate it later. Checked: string literals with words in them passed straight to
Qt's text setters and widget constructors, in the installer window and the tweaks' Qt programs."""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = sorted(ROOT.glob("gui/*.py")) + [ROOT / p for p in (
    "packs/core/arrowpad/arrowpad.py", "packs/core/snip/frame-snip",
    "packs/integrations/nordvpn/nordvpn-tray")]
SHOWN = {"setText", "setToolTip", "setWindowTitle", "setPlaceholderText", "setStatusTip", "addItem",
         "QLabel", "QPushButton", "QCheckBox", "QRadioButton", "QAction", "QToolButton", "QGroupBox",
         "say", "showMessage", "information", "warning", "critical", "question"}
WORDS = re.compile(r"[A-Za-z]{2,}")
# Names, which stay as they are in every language (glossary: locale/glossary/).
NAMES = ("Frame Tweaks", "NordVPN")


def words(text):
    """The words left in a text once HTML tags and names are out (markup and names aren't
    translated; the text around them is)."""
    text = re.sub(r"<[^>]*>|&\w+;", " ", text)
    for n in NAMES:
        text = text.replace(n, " ")
    return WORDS.search(text)


def unmarked(path):
    out = []
    for node in ast.walk(ast.parse(path.read_text(), str(path))):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        if name not in SHOWN:
            continue
        for arg in node.args[:3]:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and words(arg.value):
                out.append(f"{path.relative_to(ROOT)}:{node.lineno}: {name}({arg.value!r})")
            elif isinstance(arg, ast.JoinedStr) and words("".join(v.value for v in arg.values if isinstance(v, ast.Constant))):
                out.append(f"{path.relative_to(ROOT)}:{node.lineno}: {name}(f-string with words): "
                           "build it with _('… {x} …').format(x=…)")
    return out


class MarkedText(unittest.TestCase):
    def test_shown_text_is_marked(self):
        found = [u for f in FILES for u in unmarked(f)]
        self.assertEqual(found, [], "\n" + "\n".join(found))


    def test_the_check_finds_what_it_should(self):
        import tempfile
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as d:      # (paths are shown from ROOT)
            f = Path(d) / "sample.py"
            f.write_text('QLabel("Hello there")\nQLabel(_("Fine"))\nb.setText(f"<b>{x}</b>")\n'
                         'b.setText(f"Saved {x}")\nQLabel("Frame Tweaks")\nb.setToolTip("×")\n')
            found = unmarked(f)
        self.assertEqual([u.split(": ", 1)[1].split("(")[0] for u in found], ["QLabel", "setText"])
        self.assertIn("'Hello there'", found[0])


if __name__ == "__main__":
    unittest.main()
