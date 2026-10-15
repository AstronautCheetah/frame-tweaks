"""A button's clicked signal passes `checked` (False) to the slot: connected straight to a method
whose first parameter has a default (toggle_collapsed(place=True)), that False lands in it
silently (Arrow Pad's Collapse then didn't keep the chevron under the laser). Wire such methods
through a lambda, or give them a parameter meant for `checked` (toggle_autolock(on))."""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [*ROOT.glob("gui/*.py"), ROOT / "packs/core/arrowpad/arrowpad.py", ROOT / "packs/core/snip/frame-snip"]
MEANT = {"toggle_autolock"}             # (these take `checked` on purpose)


class ClickedSlots(unittest.TestCase):
    def test_no_default_parameter_takes_checked(self):
        bad = []
        for f in FILES:
            src = f.read_text()
            tree = ast.parse(src)
            defaults = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                        and len(n.args.args) > 1 and n.args.defaults and len(n.args.defaults) == len(n.args.args) - 1}
            for m in re.finditer(r"clicked\.connect\(self\.(\w+)\)", src):
                if m[1] in defaults and m[1] not in MEANT:
                    bad.append(f"{f.relative_to(ROOT)}: clicked → {m[1]}")
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
