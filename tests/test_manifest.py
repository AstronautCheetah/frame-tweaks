"""lib/manifest.py (the YAML front matter reader) and lib/sft.py's packs: every official
manifest reads the same as with PyYAML; ambiguous YAML is refused; a user's pack is used only
once trusted (and again after it changes), may replace a tweak only by saying so, and a tweak
missing a dependency or needing a newer pack api isn't offered."""
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import manifest  # noqa: E402
import sft  # noqa: E402

try:
    import yaml
except ImportError:
    yaml = None


class Reader(unittest.TestCase):
    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_official_manifests_read_as_pyyaml_reads_them(self):
        files = sorted(ROOT.glob("packs/[ot]*/*/README.md")) + sorted(ROOT.glob("packs/[ot]*/pack.md"))
        self.assertGreater(len(files), 20)
        for f in files:
            text = f.read_text()
            ours, _ = manifest.front_matter(text)
            end = text.find("\n---\n", 3)
            self.assertEqual(ours, yaml.safe_load(text[4:end + 1]), f)

    def test_refuses_what_readers_disagree_on(self):
        for bad in ("a: yes", "a: Off", "a: 2026-10-14", "a: 010", "a: 1_000", "a: &x 1", "a: *x",
                    "a: !tag x", "a: 1\na: 2", "a: b\n  c", "a: `x`", "a: x: y", "\ta: 1", "a: [1, 2"):
            with self.assertRaises(manifest.ManifestError, msg=bad):
                manifest.parse_yaml(bad)

    def test_values(self):
        doc = textwrap.dedent("""\
            n: 42
            f: 0.5
            t: true
            nul: ~
            q: "a \\"b\\" `c` #d"
            s: 'it''s'
            flow: [{label: "Off", value: "off"}, 2]
            text: >-
              one
              two

              three
            lit: |
              a
                b
            items:
              - x
              - key: v
                more: w
            url: https://example.com/a#b   # a comment
            """)
        self.assertEqual(manifest.parse_yaml(doc), {
            "n": 42, "f": 0.5, "t": True, "nul": None, "q": 'a "b" `c` #d', "s": "it's",
            "flow": [{"label": "Off", "value": "off"}, 2], "text": "one two\nthree", "lit": "a\n  b\n",
            "items": ["x", {"key": "v", "more": "w"}], "url": "https://example.com/a#b"})

    def test_dump_round_trips(self):
        data = {"title": "X: y", "list": ["on", "1.0", "a b"], "n": 3, "long": "word " * 40,
                "nested": {"k": [{"label": "2", "value": 0.02}]}, "empty": [], "flag": False}
        data["long"] = data["long"].strip()
        self.assertEqual(manifest.parse_yaml(manifest.dump(data)), data)
        if yaml:
            self.assertEqual(yaml.safe_load(manifest.dump(data)), data)


TWEAK = """\
---
title: {title}
emoji: 🧩
category: {category}
tier: extras
summary: A test tweak
what: It does a thing.
why: Because.
author: Someone
changes: Nothing
access: None
survives_updates: "Yes"
undo: ./install.sh uninstall {id}
{extra}---
# {title}
"""


class Packs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        self.user = t / "packs"
        for name, value in (("USER_PACKS", self.user), ("TRUSTED", t / "trusted"), ("OFF_PACKS", t / "off"), ("CONF", t)):
            p = mock.patch.object(sft, name, value)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.dict(os.environ, {"FRAME_TWEAKS_PACKS": ""})
        p.start()
        self.addCleanup(p.stop)

    def tweak(self, pack, cid, title="Mine", category="Mods", extra="", pack_md=None):
        d = self.user / pack / cid
        d.mkdir(parents=True, exist_ok=True)
        (d / "README.md").write_text(TWEAK.format(id=cid, title=title, category=category, extra=extra))
        for s in ("install.sh", "uninstall.sh", "status.sh"):
            (d / s).write_text("#!/bin/bash\n")
        if pack_md is not None:
            (self.user / pack / "pack.md").write_text(pack_md)
        return d

    def ids(self):
        return {c["id"]: c for c in sft.load(refresh=True)["components"]}

    def test_official_pack_is_valid(self):
        data = sft.load(refresh=True)
        self.assertEqual([p for p in data["problems"] if not p.startswith("warning")], [])
        self.assertIn("scroll-strips", self.ids())

    def test_two_official_packs_on_until_turned_off(self):
        """Original and 3rd Party: both in use without trusting; either can be turned off."""
        packs = {p["name"]: p for p in sft.load(refresh=True)["packs"]}
        self.assertEqual((packs["Original"]["state"], packs["3rd Party"]["state"]), ("official", "official"))
        self.assertEqual((self.ids()["arrowpad"]["pack"], self.ids()["recline"]["pack"]), ("Original", "3rd Party"))
        self.assertTrue(self.ids()["recline"]["official"])
        sft.set_official(sft.THIRD_PARTY, False)
        self.assertNotIn("recline", self.ids())
        self.assertIn("arrowpad", self.ids())
        self.assertEqual({p["name"]: p["state"] for p in sft.load(refresh=True)["packs"]}["3rd Party"], "off")
        sft.set_official(sft.THIRD_PARTY, True)
        self.assertIn("recline", self.ids())

    def test_official_packs_share_the_category_order(self):
        cats = [sft.read_pack(p)[0]["categories"] for p in sft.OFFICIAL_PACKS]
        self.assertEqual(cats[0], cats[1])

    def test_untrusted_pack_is_listed_not_used(self):
        self.tweak("mypack", "hello")
        data = sft.load(refresh=True)
        self.assertNotIn("hello", self.ids())
        self.assertEqual([p["state"] for p in data["packs"] if p["name"] == "mypack"], ["untrusted"])

    def test_trusted_until_it_changes(self):
        d = self.tweak("mypack", "hello")
        sft.set_trusted(d.parent, True)
        c = self.ids()["hello"]
        self.assertFalse(c["official"])
        self.assertEqual(c["category"], "Mods")
        (d / "install.sh").write_text("#!/bin/bash\necho changed\n")
        self.assertNotIn("hello", self.ids())
        self.assertEqual([p["state"] for p in sft.load(refresh=True)["packs"] if p["name"] == "mypack"], ["changed"])

    def test_same_id_needs_replaces(self):
        d = self.tweak("mypack", "cursor", title="My cursor")
        sft.set_trusted(d.parent, True)
        self.assertTrue(self.ids()["cursor"]["official"])
        self.assertTrue(any("replaces: true" in p for p in sft.load()["problems"]))
        d = self.tweak("mypack", "cursor", title="My cursor", extra="replaces: true\n")
        sft.set_trusted(d.parent, True)
        rows = sft.load(refresh=True)["components"]
        c = next(c for c in rows if c["id"] == "cursor")
        self.assertEqual((c["title"], c["replaced"]), ("My cursor", "Original"))
        self.assertEqual(len([r for r in rows if r["id"] == "cursor"]), 1)

    def test_missing_dependency_and_bad_manifest(self):
        self.tweak("mypack", "needy", extra="depends: [nothing-here]\n")
        bad = self.tweak("mypack", "broken")
        (bad / "README.md").write_text("---\ntitle: x\n---\n")
        sft.set_trusted(self.user / "mypack", True)
        ids, problems = self.ids(), sft.load()["problems"]
        self.assertNotIn("needy", ids)
        self.assertNotIn("broken", ids)
        self.assertTrue(any("nothing-here" in p for p in problems))
        self.assertTrue(any("broken: why is missing" in p for p in problems))

    def test_newer_pack_api_is_refused(self):
        d = self.tweak("future", "later", pack_md="---\nname: Future\napi: 99\n---\n")
        sft.set_trusted(d.parent, True)
        self.assertNotIn("later", self.ids())
        self.assertTrue(any("newer Frame Tweaks" in p for p in sft.load()["problems"]))

    def test_new_category_comes_after_the_official_ones(self):
        d = self.tweak("mypack", "hello", category="Games")
        self.tweak("mypack", "hello2", category="Accessibility")
        sft.set_trusted(d.parent, True)
        rows = [c["id"] for c in sft.load(refresh=True)["components"]]
        self.assertEqual(rows[-1], "hello")                          # its own category, last
        self.assertLess(rows.index("hello2"), rows.index("vscodium"))   # joins Accessibility


if __name__ == "__main__":
    unittest.main()
