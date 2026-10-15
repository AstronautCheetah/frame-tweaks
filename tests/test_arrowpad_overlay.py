"""Arrow Pad's VR overlay (vroverlay.py) reads the pad's state (p.layer, p.lang, self.pad.scale, …):
everything it reads must still exist on the pad (arrowpad.py), or the VR pad crashes on its
first redraw (a removed `lang` did, once)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAD = ROOT / "packs/core/arrowpad"
QT_WIDGET = {"grab", "show", "hide", "move", "pos", "width", "height", "size", "isVisible", "update",
             "close", "setVisible", "raise_", "activateWindow", "windowHandle", "geometry", "devicePixelRatioF",
             "childAt", "mapToGlobal", "mapFromGlobal"}


class OverlayReadsThePad(unittest.TestCase):
    def test_every_attribute_exists(self):
        overlay, pad = (PAD / "vroverlay.py").read_text(), (PAD / "arrowpad.py").read_text()
        used = set(re.findall(r"\b(?:p|self\.pad)\.(\w+)", overlay)) - QT_WIDGET
        missing = [a for a in sorted(used)
                   if not re.search(rf"(self\.{a}\s*(?:,\s*self\.\w+\s*)*=|\bdef {a}\b|self\.{a}\s*:)", pad)
                   and not re.search(rf"self\.\w+(?:,\s*self\.\w+)*,\s*self\.{a}\s*=", pad)]
        self.assertEqual(missing, [], "vroverlay.py reads these, arrowpad.py doesn't have them")


if __name__ == "__main__":
    unittest.main()
