"""lib/manifest.py (the YAML front matter reader) and lib/sft.py's packs: every official
manifest reads the same as with PyYAML; ambiguous YAML is refused; a user's pack is used only
once trusted (and again after it changes), may replace a tweak only by saying so, and a tweak
missing a dependency or needing a newer pack api isn't offered."""
import contextlib
import io
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
        files = sorted(p for pack in sft.OFFICIAL_PACKS for p in pack.glob("*/README.md")) + [p / "pack.md" for p in sft.OFFICIAL_PACKS]
        self.assertGreater(len(files), 20)
        for f in files:
            text = f.read_text()
            ours, _ = manifest.front_matter(text)
            end = text.find("\n---\n", 3)
            self.assertEqual(ours, yaml.safe_load(text[4:end + 1]), f)

    def test_refuses_what_readers_disagree_on(self):
        for bad in ("a: yes", "a: Off", "a: 2026-10-14", "a: 010", "a: 1_000", "a: &x 1", "a: *x",
                    "a: !tag x", "a: 1\na: 2", "a: b\n  c", "a: `x`", "a: x: y", "\ta: 1", "a: [1, 2",
                    # PyYAML: 1, True, a date as keys; inf; a {x: null} or an error for ? and :; no
                    # empty entry; the tab ends the value; the spaces past the indentation are text
                    "1: x", "on: x", "2026-10-14: x", "a: {true: x}", "a: +.inf", "a: ? x", "a: [?x]",
                    "a: [x?]", "a: [:x]", "a: [#x]", "a: [a, ]", "a: {k: }", "a: x\t# c", "a: =",
                    "a: |\n  x\n     \n  y\n"):
            with self.assertRaises(manifest.ManifestError, msg=bad):
                manifest.parse_yaml(bad)

    def test_list_items_as_pyyaml_reads_them(self):
        """A "- key: |" item's text keeps its first lines, blank or #; an item with only a
        comment is null (not the start of a list holding the next items)."""
        doc = "a:\n  - j: |\n\n      # not a comment\n      x\n    k: 1\nb:\n  - # nothing\n  - z\n"
        want = {"a": [{"j": "\n# not a comment\nx\n", "k": 1}], "b": [None, "z"]}
        self.assertEqual(manifest.parse_yaml(doc), want)
        if yaml:
            self.assertEqual(yaml.safe_load(doc), want)

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

    def test_dump_round_trips_awkward_values(self):
        """A small pack.md (the file itself is never {...}), lists of lists, text that | can't
        hold as it is, ? and : at the start, tabs, and floats Python writes as 1e-05."""
        awkward = ["?x", "? x", ":x", "a?b", "=", "<<", "+.inf", "a\tb", "a\n\n", "\n", "  a\nb", "a\n  \nb",
                   "x\n\ty", "#x\ny", "3rd", "y"]
        for data in ({"name": "My pack", "api": 1}, {"k": [["x\ny"], [{"a": 1}]]}, {"k": [{"j": "\nx", "l": [[1]]}]},
                     {"k": awkward, "m": {s: s for s in ("a", "b")}}, {"k": [{"v": s} for s in awkward]},
                     {"f": [5e-05, 1e+20, -0.0, 0.025]}):
            out = manifest.dump(data)
            self.assertEqual(manifest.parse_yaml(out), data, out)
            if yaml:
                self.assertEqual(yaml.safe_load(out), data, out)
        with self.assertRaises(ValueError):
            manifest.dump({"f": float("inf")})            # (no form the reader takes)


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
        """Original, Integrations and 3rd Party: in use without trusting; each can be turned off."""
        packs = {p["name"]: p for p in sft.load(refresh=True)["packs"]}
        self.assertEqual([packs[n]["state"] for n in ("Original", "Integrations", "3rd Party")], ["official"] * 3)
        self.assertEqual(self.ids()["signal"]["pack"], "Integrations")
        self.assertEqual((self.ids()["arrowpad"]["pack"], self.ids()["clipboard"]["pack"]), ("Original", "3rd Party"))
        self.assertTrue(self.ids()["clipboard"]["official"])
        sft.set_official(sft.THIRD_PARTY, False)
        self.assertNotIn("clipboard", self.ids())
        self.assertIn("arrowpad", self.ids())
        self.assertEqual({p["name"]: p["state"] for p in sft.load(refresh=True)["packs"]}["3rd Party"], "off")
        sft.set_official(sft.THIRD_PARTY, True)
        self.assertIn("clipboard", self.ids())

    def test_official_packs_share_the_category_order(self):
        cats = [sft.read_pack(p)[0]["categories"] for p in sft.OFFICIAL_PACKS]
        self.assertEqual(cats, [cats[0]] * len(cats))

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

    def test_trust_covers_names_contents_links_and_modes(self):
        """No two packs hash alike by moving bytes between a file and its name (an update could
        then pass for trusted); adding a link, or making a file executable, is a change."""
        a, b = Path(self.tmp.name) / "a", Path(self.tmp.name) / "b"
        a.mkdir()
        b.mkdir()
        (a / "x").write_bytes(b"1\0y\0" + b"2")             # (one file: "x", holding 1 NUL y NUL 2)
        (b / "x").write_bytes(b"1")
        (b / "y").write_bytes(b"2")                       # (two: "x" and "y", same bytes in a row)
        self.assertNotEqual(sft.pack_hash(a), sft.pack_hash(b))
        d = self.tweak("mypack", "hello")
        sft.set_trusted(d.parent, True)
        self.assertIn("hello", self.ids())
        (d.parent / "__pycache__").mkdir()                # (left out of the hash, as .git is)
        (d.parent / "__pycache__" / "x.pyc").write_bytes(b"x")
        self.assertIn("hello", self.ids())
        (d.parent / "more").symlink_to(d.parent / "__pycache__")   # (a new link counts, even to a left-out folder)
        self.assertNotIn("hello", self.ids())
        (d.parent / "more").unlink()
        self.assertIn("hello", self.ids())
        os.chmod(d / "status.sh", 0o755)
        self.assertNotIn("hello", self.ids())

    def test_a_broken_pack_md_is_a_problem_not_a_crash(self):
        """Any pack's pack.md is read, trusted or not: empty lists or wrong kinds of values must
        not stop the official tweaks from loading."""
        self.tweak("mypack", "hello", pack_md="---\nname: Mine\ncategories:\norder: 5\n---\n")
        data = sft.load(refresh=True)
        self.assertIn("arrowpad", self.ids())
        self.assertTrue(any("categories must be a list" in p for p in data["problems"]))
        self.assertTrue(any("order must be a list" in p for p in data["problems"]))
        (self.user / "mypack" / "pack.md").write_bytes(b"---\nname: Caf\xe9\n---\n")   # (not UTF-8)
        self.assertTrue(any("pack.md" in p for p in sft.load(refresh=True)["problems"]))

    def test_wrong_kinds_of_values_leave_the_tweak_out(self):
        """processes as plain text would be a pattern per letter (install.sh stops whatever matches
        "^" or "."); source and run as text, or settings: actions: left empty, crashed the loader."""
        bad = {"processes": "processes: ^~/.local/bin/hello-daemon\n", "source": "source: https://example.com\n",
               "run": "run: Open\n", "settings.actions": "settings:\n  file: ~/.config/x.conf\n  format: shell\n"
               "  options:\n    - {key: A, title: A, default: a, choices: [{label: A, value: a}]}\n  actions:\n",
               "settings.file": "settings:\n  file: ~/.config/../.bashrc\n  format: shell\n"
               "  options:\n    - {key: A, title: A, default: a, choices: [{label: A, value: a}]}\n"}
        for key, extra in bad.items():
            d = self.tweak("mypack", "hello", extra=extra)
            (d / "run.sh").write_text("#!/bin/bash\n")
            sft.set_trusted(d.parent, True)
            self.assertNotIn("hello", self.ids(), key)
            self.assertTrue(any(f"hello: {key}" in p for p in sft.load()["problems"]), key)

    def test_config_lists_only_its_own_settings_places(self):
        """config: is what an uninstall may remove (⚙ Preferences): a path below ~/.config/,
        ~/.var/app/<app> or ~/.local/state/frame-tweaks/, never one of those folders whole, nor a
        way out of them. The settings file counts without being listed."""
        for bad in ("~/.config/", "~/.config", "~/.bashrc", "~/.config/../.ssh", "~/.var/app/", "~/.var/app/a/b",
                    "~/.local/state/frame-tweaks", "/etc/x", "~/.config/~/x", ".config/x"):
            d = self.tweak("mypack", "hello", extra=f"config: [{bad!r}]\n")
            sft.set_trusted(d.parent, True)
            self.assertNotIn("hello", self.ids(), bad)
            self.assertTrue(any("hello: config" in p for p in sft.load()["problems"]), bad)
        d = self.tweak("mypack", "hello", extra="config: [~/.config/hello.json, ~/.var/app/org.example.Hello, "
                       "~/.local/state/frame-tweaks/hello]\nsettings:\n  file: ~/.config/frame-tweaks/hello.conf\n"
                       "  format: shell\n  options:\n    - {key: A, title: A, default: a, choices: [{label: A, value: a}]}\n")
        sft.set_trusted(d.parent, True)
        self.assertEqual(self.ids()["hello"]["config"], ["~/.config/hello.json", "~/.var/app/org.example.Hello",
                                                         "~/.local/state/frame-tweaks/hello", "~/.config/frame-tweaks/hello.conf"])

    def test_official_tweaks_settings_places(self):
        ids = self.ids()
        self.assertEqual(ids["arrowpad"]["config"], ["~/.config/arrowpad.json", "~/.config/arrowpad-vr.json"])
        self.assertEqual(ids["snip"]["config"], ["~/.config/frame-tweaks/snip.json"])
        self.assertEqual(ids["claude-code"]["config"], [])      # (~/.claude holds its sign-in, history and memory)
        # Third-party apps, left installed when Frame Tweaks is uninstalled (unless --remove-apps)
        self.assertEqual({i for i, c in ids.items() if c["app"]},
                         {"homebrew", "vscodium", "claude-desktop", "claude-code", "full-keyboard", "clipboard"})

    def test_trusting_by_name_needs_a_name_only_one_pack_has(self):
        """A pack can call itself anything, so `mods trust NAME` mustn't pick one of two."""
        mine = self.tweak("mypack", "hello").parent
        self.tweak("aaa", "other", pack_md="---\nname: mypack\n---\n")      # (listed first)
        sft.load(refresh=True)
        with self.assertRaises(SystemExit):
            sft.find_pack("mypack")
        self.assertEqual(sft.find_pack(str(mine))["dir"], mine.resolve())

    def test_check_reports_the_pack_md_too(self):
        self.tweak("future", "later", pack_md="---\napi: 99\norder:\n---\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as e:
            sft.mods(["check", str(self.user / "future")])
        self.assertEqual(e.exception.code, 1)
        self.assertIn("newer Frame Tweaks", out.getvalue())
        self.assertIn("order must be a list", out.getvalue())

    def test_dependency_cycle_and_registry_lines(self):
        """deps stops where a cycle began (as install.sh's with_deps); a summary with a line
        break doesn't make a row of its own in the registry install.sh reads."""
        self.tweak("mypack", "one", extra="depends: [two]\n")
        d = self.tweak("mypack", "two", extra="depends: [one]\n")
        (d / "README.md").write_text((d / "README.md").read_text().replace("summary: A test tweak", "summary: |\n  A\n  B"))
        sft.set_trusted(self.user / "mypack", True)
        sft.load(refresh=True)
        for argv, check in ((["deps", "one"], lambda s: self.assertEqual(s.split(), ["two"])),
                            (["registry"], lambda s: self.assertEqual(len(s.splitlines()), len(sft.components())))):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                sft.main(argv)
            check(out.getvalue())

    def test_new_category_comes_after_the_official_ones(self):
        d = self.tweak("mypack", "hello", category="Games")
        self.tweak("mypack", "hello2", category="Accessibility")
        sft.set_trusted(d.parent, True)
        rows = [c["id"] for c in sft.load(refresh=True)["components"]]
        self.assertEqual(rows[-1], "hello")                          # its own category, last
        self.assertLess(rows.index("hello2"), rows.index("vscodium"))   # joins Accessibility


if __name__ == "__main__":
    unittest.main()
