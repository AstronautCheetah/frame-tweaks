"""dev/record-tested.sh and steam-frame.yml: a test record is read from the Frame (here: this
machine's os-release and a stand-in vrserver log), its versions quoted as the steam-frame.yml spec
asks (YAML would read 2.10 as 2.1); results other than works/partial/broken, and notes that would
break the line, are refused; every record already in steam-frame.yml has the required fields."""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT  # noqa: E402

SCRIPT = ROOT / "dev/record-tested.sh"
RECORD = re.compile(r'^  - \{ steamos: "[0-9][^"]*"(, build: "[^"]+")?(, steamvr: "[0-9][^"]*")?'
                    r'(, channel: (stable|beta|preview))?, date: "\d{4}-\d{2}-\d{2}", '
                    r'result: (works|partial|broken)(, notes: "[^"\n]{1,200}")? \}$')


class RecordTested(unittest.TestCase):
    def run_it(self, *args):
        with tempfile.TemporaryDirectory() as t:
            log = Path(t) / "vrserver.txt"
            log.write_text("[Info] - vrserver 2.18.2 startup with PID=1, config=x\n")
            env = dict(os.environ, FRAME_TWEAKS_VRSERVER_LOG=str(log))
            return subprocess.run(["bash", str(SCRIPT), "--print", ".", *args], env=env, capture_output=True,
                                  text=True, timeout=30)

    @unittest.skipUnless(Path("/etc/os-release").is_file(), "needs /etc/os-release (Linux)")
    def test_a_record_as_the_spec_has_it(self):
        r = self.run_it("works", "0.7.0: install, Dictation")
        self.assertEqual(r.returncode, 0, r.stderr)
        line = r.stdout.rstrip("\n")
        self.assertRegex(line, RECORD)
        self.assertIn('steamvr: "2.18.2"', line)

    def test_bad_result_or_notes_are_refused(self):
        for args in (("fine", "x"), ("works", 'a "quoted" word'), ("works", "two\nlines"), ("works", "x" * 201)):
            r = self.run_it(*args)
            self.assertEqual(r.returncode, 2, (args, r.stdout, r.stderr))

    def test_the_records_in_steam_frame_yml(self):
        """Each record as dev/record-tested.sh writes it, and the whole file fine by the catalog's
        own checker (dev/fccatalog_manifest.py, when PyYAML is there) and Frame Tweaks' reader."""
        text = (ROOT / "steam-frame.yml").read_text()
        records = text.split("\ntested:\n", 1)[1].splitlines()
        for line in records:
            self.assertRegex(line, RECORD)
        sys.path.insert(0, str(ROOT / "dev"))
        import steam_frame_yml
        found, _ran = steam_frame_yml.problems()
        self.assertEqual(found, [])
        self.assertEqual(len(steam_frame_yml.records()), len(records))

    def test_the_catalog_checker_refuses_what_it_should(self):
        """Its copy here still refuses an unquoted version and an unknown term (if it didn't, the
        file's check would mean nothing)."""
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("needs PyYAML")
        sys.path.insert(0, str(ROOT / "dev"))
        import fccatalog_manifest as catalog
        with self.assertRaises(catalog.ManifestError) as e:
            catalog.parse("provides: [tooling, sorcery]\ntested:\n  - { steamos: 0.5, date: 2026-11-02, result: works }\n")
        self.assertTrue(any("sorcery" in p for p in e.exception.problems))
        self.assertTrue(any("quote" in p for p in e.exception.problems))


if __name__ == "__main__":
    unittest.main()
