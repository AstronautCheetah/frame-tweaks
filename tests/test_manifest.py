"""lib/manifest.py (the YAML front matter reader) and lib/sft.py's packs: every official
manifest reads the same as with PyYAML; ambiguous YAML is refused; a user's pack is used only
once trusted (and again after it changes), may replace a tweak only by saying so, and a tweak
missing a dependency or needing a newer pack api isn't offered."""
import contextlib
import io
import os
import shutil
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
        # (every file under CONF: HIDDEN and the rest were made from the real one as sft loaded)
        for name, value in (("USER_PACKS", self.user), ("TRUSTED", t / "trusted"), ("OFF_PACKS", t / "off"), ("CONF", t),
                            ("HIDDEN", t / "hidden"), ("SHOWN", t / "shown"), ("COLLAPSED", t / "collapsed"),
                            ("HIDDEN_CATS", t / "hidden-categories")):
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
        """Core, Integrations and 3rd Party: in use without trusting; each can be turned off."""
        packs = {p["name"]: p for p in sft.load(refresh=True)["packs"]}
        self.assertEqual([packs[n]["state"] for n in ("Core", "Integrations", "3rd Party")], ["official"] * 3)
        self.assertEqual(self.ids()["signal"]["pack"], "Integrations")
        self.assertEqual((self.ids()["arrowpad"]["pack"], self.ids()["recline"]["pack"]), ("Core", "3rd Party"))
        self.assertTrue(self.ids()["recline"]["official"])
        sft.set_official(sft.THIRD_PARTY, False)
        self.assertNotIn("recline", self.ids())
        self.assertIn("arrowpad", self.ids())
        self.assertEqual({p["name"]: p["state"] for p in sft.load(refresh=True)["packs"]}["3rd Party"], "off")
        sft.set_official(sft.THIRD_PARTY, True)
        self.assertIn("recline", self.ids())

    def test_core_turned_off_as_original_stays_off(self):
        """Core was "Original" (packs/original) before 0.6.6: turned off then, it stays off."""
        sft.OFF_PACKS.write_text("original\n")
        self.assertEqual(sft.off_packs(), {"core"})
        packs = {p["name"]: p for p in sft.load(refresh=True)["packs"]}
        self.assertEqual(packs["Core"]["state"], "off")
        sft.set_official(sft.CORE, True)
        self.assertEqual(sft.off_packs(), set())

    def test_what_an_update_left_of_the_old_folder_isnt_a_pack(self):
        """An update to Core's new folder can leave packs/original behind with only ignored files
        (Python's caches): not a pack of the user's. A pack.md there would make it one."""
        packs = Path(tempfile.mkdtemp()) / "packs"
        self.addCleanup(shutil.rmtree, packs.parent, True)
        for name in ("core", "integrations", "third-party", "original/arrowpad/__pycache__", "mine"):
            (packs / name).mkdir(parents=True)
        dirs = [packs / "core", packs / "integrations", packs / "third-party"]
        (packs / "core/pack.md").write_text("---\nname: Core\nformerly: [original]\n---\n")
        with mock.patch.object(sft, "CORE", dirs[0]), mock.patch.object(sft, "OFFICIAL_PACKS", dirs):
            self.assertEqual([d.name for d in sft.pack_dirs()][:4], ["core", "integrations", "third-party", "mine"])
            (packs / "original/pack.md").write_text("---\nname: Mine too\n---\n")
            self.assertIn("original", [d.name for d in sft.pack_dirs()])

    def test_a_tweak_this_frame_doesnt_need_is_hidden_unless_installed(self):
        """needed.sh exit 1 (one line: why): hidden by default, like hidden_by_default, until
        it's installed (then its status says so); exit 0, or no needed.sh: offered."""
        d = self.tweak("mypack", "gone", extra="")
        (d / "needed.sh").write_text("#!/bin/bash\necho 'SteamOS does it now'\necho more\nexit 1\n")
        (self.tweak("mypack", "kept") / "needed.sh").write_text("#!/bin/bash\nexit 0\n")
        (self.tweak("mypack", "failed") / "needed.sh").write_text("#!/bin/bash\nset -e\nfalse\necho never\n")
        self.tweak("mypack", "plain")
        sft.set_trusted(d.parent, True)
        rows = sft.load(refresh=True)["components"]
        mine = [c for c in rows if c["id"] in ("gone", "kept", "failed", "plain")]   # (failed: exit 1, no why)
        self.assertEqual(sft.not_needed(mine, refresh=True), {"gone": "SteamOS does it now"})
        rows = mine
        state = Path(self.tmp.name) / "state"
        with mock.patch.object(sft, "STATE", state):
            self.assertIn("gone", sft.hidden(rows))
            self.assertFalse({"kept", "failed", "plain"} & sft.hidden(rows))
            (state / "installed").mkdir(parents=True)
            (state / "installed/gone").write_text("0.6.8\n")
            self.assertNotIn("gone", sft.hidden(rows))
            sft.set_hidden("gone", True)                    # (still yours to hide)
            self.assertIn("gone", sft.hidden(rows))

    def test_formerly_a_tweaks_earlier_ids(self):
        """formerly: (a renamed tweak): its earlier ids still name it in depends:, and what's kept
        under one (install record, held, hidden) moves to its id once."""
        d = self.tweak("mypack", "hello", extra="formerly: [hi, hey]\n")
        self.tweak("mypack", "hello2", extra="depends: [hi]\n")
        sft.set_trusted(d.parent, True)
        ids = self.ids()
        self.assertEqual(ids["hello2"]["deps"], ["hello"])
        self.assertEqual(sft.load()["renamed"], {"hi": "hello", "hey": "hello"})
        state = Path(self.tmp.name) / "state"
        for sub in ("installed", "held"):
            (state / sub).mkdir(parents=True)
            (state / sub / "hi").write_text("0.6.5\n")
        sft.write_set(sft.HIDDEN, {"hi", "other"})
        with mock.patch.object(sft, "STATE", state):
            moved = sft.apply_formerly()
            self.assertEqual(sft.apply_formerly(), [])                      # (once)
        self.assertIn("installed/hi -> hello", moved)
        self.assertEqual((state / "installed/hello").read_text(), "0.6.5\n")
        self.assertTrue((state / "held/hello").exists() and not (state / "held/hi").exists())
        self.assertEqual(sft.read_set(sft.HIDDEN), {"hello", "other"})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sft.main(["renamed", "hi"])
        self.assertEqual(out.getvalue(), "hello\n")

    def test_formerly_wrong(self):
        for extra, says in (("formerly: [Not An Id]\n", "formerly must be"), ("formerly: [hello]\n", "formerly must be")):
            d = self.tweak("mypack", "hello", extra=extra)
            sft.set_trusted(d.parent, True)
            self.assertNotIn("hello", self.ids(), extra)
            self.assertTrue(any(says in p for p in sft.load()["problems"]), extra)
        d = self.tweak("mypack", "hello", extra="formerly: [hello2]\n")      # (another tweak's id)
        self.tweak("mypack", "hello2")
        sft.set_trusted(d.parent, True)
        self.assertNotIn("hello2", sft.load(refresh=True)["renamed"])
        self.assertTrue(any("another tweak's id" in p for p in sft.load()["problems"]))

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
        self.assertEqual((c["title"], c["replaced"]), ("My cursor", "3rd Party"))
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

    def test_sudo_says_when_and_why(self):
        """sudo: text for the window's tag and page (and ./install.sh list), or homebrew: only while
        Homebrew isn't installed."""
        d = self.tweak("mypack", "hello", extra="sudo: once, to add a udev rule\n")
        sft.set_trusted(d.parent, True)
        c = self.ids()["hello"]
        self.assertEqual(sft.sudo_note(c), "once, to add a udev rule")
        self.assertIn("Asks for your sudo password: once, to add a udev rule", sft.info("hello"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sft.main(["registry"])
        line = next(l for l in out.getvalue().splitlines() if l.startswith("hello\x1f"))
        self.assertEqual(line.split("\x1f")[7], "1")                     # (./install.sh list's mark)
        c = dict(c, sudo="homebrew")
        with tempfile.TemporaryDirectory() as brew:
            with mock.patch.object(sft, "BREW", Path(brew) / "brew"):
                self.assertIn("/home/linuxbrew", sft.sudo_note(c))
                (Path(brew) / "brew").touch()
                self.assertEqual(sft.sudo_note(c), "")
        (d / "README.md").write_text(TWEAK.format(id="hello", title="Mine", category="Mods", extra="sudo: [install]\n"))
        sft.set_trusted(d.parent, True)
        self.assertNotIn("hello", self.ids())
        self.assertTrue(any("sudo must be text" in p for p in sft.load()["problems"]), sft.load()["problems"])

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

    def test_a_settings_option_needs_a_default_and_a_shell_key_a_variable_name(self):
        """Without default: (a null choice made it look present) every command crashed as sft
        loaded, mods untrust included; a shell file's key like a[$(cmd)] would run cmd when the
        setting is read (bash's ${!key}). Both leave the tweak out, saying why."""
        opts = "settings:\n  file: ~/.config/x.conf\n  format: shell\n  options:\n"
        cases = {"needs key, title, default and choices":
                 opts + "    - {key: A, title: A, choices: [{label: Auto, value: null}, {label: Fast, value: fast}]}\n",
                 "keys are variable names":
                 opts + "    - {key: \"a[$(touch x)]\", title: A, default: a, choices: [{label: A, value: a}]}\n"}
        for says, extra in cases.items():
            d = self.tweak("mypack", "hello", extra=extra)
            sft.set_trusted(d.parent, True)
            self.assertNotIn("hello", self.ids(), says)
            self.assertTrue(any(says in p for p in sft.load()["problems"]), (says, sft.load()["problems"]))
            sft.settings_specs()                                                  # (and no crash)

    def test_mods_check_sees_a_pack_with_its_own_readme(self):
        """A shared pack often has a README.md at its top and no pack.md (optional): it's still a
        pack, its tweaks checked, as load() treats it; only a folder with no tweak folders in it is
        a single tweak."""
        d = self.tweak("my-pack", "hello")
        (d.parent / "README.md").write_text("# My pack\n")
        lines, bad = sft.check_folder(d.parent)
        self.assertEqual(bad, 0, lines)
        self.assertIn("ok  hello", lines)
        lines, bad = sft.check_folder(d)                                          # (a single tweak)
        self.assertEqual((bad, lines[-1]), (0, "ok  hello"))

    def test_update_checks_run_git_only_in_trusted_packs(self):
        """Looking for a pack's updates runs git in its folder, and git reads that repository's own
        .git/config, which can run commands (here remote.origin.uploadpack, used by ls-remote).
        So a pack you haven't trusted (or that changed since) is never looked at."""
        import subprocess
        d = self.tweak("their-pack", "hello")
        mark = Path(self.tmp.name) / "ran"
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        run = lambda *a: subprocess.run(["git", *a], cwd=d.parent, env=env, check=True, capture_output=True)
        run("init", "-q", "-b", "main")
        run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "x")
        run("remote", "add", "origin", "https://example.invalid/their-pack.git")
        run("config", "remote.origin.uploadpack", f"touch {mark}; git-upload-pack")
        with mock.patch.object(sft, "pack_has_update", wraps=sft.pack_has_update) as check:
            self.assertEqual(sft.packs_with_updates(), [])
            check.assert_not_called()
        self.assertFalse(mark.exists())
        sft.set_trusted(d.parent, True)
        with mock.patch.object(sft, "pack_has_update", return_value=True) as check:
            self.assertEqual([p["name"] for p in sft.packs_with_updates()], ["their-pack"])

    def test_mods_lists_a_packs_own_text_without_control_characters(self):
        """An untrusted pack's name could hold terminal escapes that rewrite its line to look like
        an official pack's "official: in use"."""
        self.tweak("evil", "hello", pack_md='---\nname: "x\x1b[2K\x1b[1GCore  official: in use"\n---\n')
        self.assertIn("\x1b", sft.read_pack(self.user / "evil")[0]["name"])        # (the escape got in)
        sft.load(refresh=True)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sft.mods([])
        self.assertIn("official: in use", out.getvalue())                       # (it's listed)
        self.assertNotIn("\x1b", out.getvalue())

    def test_a_link_needs_no_scripts_and_says_what_it_runs(self):
        """link: (docs/mods.md, Linking a project): no scripts, and lib/link.sh runs in their place."""
        good = ("link:\n  install: curl -fsSL https://example.org/get.sh | bash\n"
                "  installed: [~/project, /opt/elsewhere]\n  run: project-app\n  readme: https://example.org\n"
                "run: {label: Open}\n")
        d = self.tweak("mine", "linked", extra=good)
        for script in d.glob("*.sh"):
            script.unlink()
        sft.set_trusted(self.user / "mine", True)
        c = self.ids()["linked"]
        self.assertEqual(c["link"]["installed"], ["~/project", "/opt/elsewhere"])
        self.assertEqual(c["run_label"], "Open")
        self.assertEqual(sft.script(c, "status")[1:], [str(sft.LINK_HELPER), "status", "linked"])
        self.assertIsNone(sft.script(c, "check-system"))
        for bad, says in (("link:\n  installed: ~/p\n", "link.install is missing"),
                          ("link:\n  install: x\n  installed: project\n", "link.installed must be a path"),
                          ("link:\n  install: x\n  installed: ~/p/*/bin\n", "not a pattern"),
                          ("link:\n  install: x\n  installed: ~/p\n  readme: http://x\n", "https://"),
                          ("link:\n  install: x\n  installed: ~/p\n  restart: plasma\n", "link.restart can only be steamvr"),
                          ("link: x\n", "link must be a mapping")):
            (d / "README.md").write_text(TWEAK.format(id="linked", title="Mine", category="Mods", extra=bad))
            sft.set_trusted(self.user / "mine", True)
            problems = sft.load(refresh=True)["problems"]
            self.assertTrue(any(says in pr for pr in problems), (bad, problems))
            self.assertNotIn("linked", self.ids())

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
        # Third-party apps, left installed when Frame Tweaks is uninstalled (unless --remove-apps)
        self.assertEqual({i for i, c in ids.items() if c["app"]},
                         {"homebrew", "claude-desktop", "full-keyboard", "clipboard"})

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
        self.assertLess(rows.index("hello2"), rows.index("claude-desktop"))   # joins Accessibility


if __name__ == "__main__":
    unittest.main()
