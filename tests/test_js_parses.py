"""The SteamVR dashboard's JavaScript (vr-dashboard's lib.js and each tweak's patch) parses: a
syntax error there only shows in the headset, as a patch that silently doesn't load. Checked
with `node --check` (CI's runner has Node; skipped where it's missing, as on SteamOS)."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = sorted(ROOT.glob("packs/*/*/*.js"))
NODE = shutil.which("node")


def problem(path):
    r = subprocess.run([NODE, "--check", str(path)], capture_output=True, text=True, timeout=60)
    return None if r.returncode == 0 else (r.stderr.strip().splitlines() or ["?"])[0:5]


@unittest.skipUnless(NODE, "needs node")
class JavaScript(unittest.TestCase):
    def test_each_file_parses(self):
        self.assertGreater(len(FILES), 4)
        found = [f"{f.relative_to(ROOT)}: {p}" for f in FILES if (p := problem(f))]
        self.assertEqual(found, [], "\n" + "\n".join(found))

    def test_the_check_finds_a_syntax_error(self):
        with tempfile.TemporaryDirectory() as d:
            ok, bad = Path(d) / "ok.js", Path(d) / "bad.js"
            ok.write_text("const a = { ...{ b: 1 } }; window.x ??= {}; const c = a?.b ?? 1;\n")
            bad.write_text("const a = 1;\nconst b = ;\n")
            self.assertIsNone(problem(ok))
            self.assertIsNotNone(problem(bad))


if __name__ == "__main__":
    unittest.main()
