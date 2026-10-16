"""The maintainer and contributor tools (dev/, .github/workflows/) catch what they're for. Run on
throwaway copies, with stand-ins for the network, gh and git (nothing leaves the machine):
the Release workflow's version after a pre-release and its empty-notes check; dev/check-docs.py
and HTML pictures; dev/gen-docs.py and an upstream README a tweak no longer names; dev/i18n.py
keeping removed texts' translations; dev/check-pins.sh comparing a Hugging Face file at main;
dev/check-upstream.sh reporting a check-pins.sh that stopped; dev/test-tweaks.sh catching writes
into the checkout and old-dated files left in /tmp."""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script, stub  # noqa: E402


def step_script(workflow, name):
    """The run: script of the workflow step called name."""
    lines = (ROOT / ".github/workflows" / workflow).read_text().splitlines()
    i = next(n for n, l in enumerate(lines) if l.strip() == f"- name: {name}")
    j = next(n for n in range(i, len(lines)) if lines[n].strip() == "run: |")
    indent = len(lines[j]) - len(lines[j].lstrip()) + 2
    body = []
    for l in lines[j + 1:]:
        if l.strip() and len(l) - len(l.lstrip()) < indent:
            break
        body.append(l[indent:])
    return "\n".join(body) + "\n"


def stubs(d, **scripts):
    for name, body in scripts.items():
        stub(d, name, body)
    d.mkdir(parents=True, exist_ok=True)
    return d


def copy_repo(dest):
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns(".git", "tmp", "references", "__pycache__"))
    return dest


class Temp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)


# git, as the Release workflow uses it: tag -l PATTERN, rev-parse -q --verify refs/tags/X ($TAGS)
GIT = '''case "$1" in
    tag) for t in $TAGS; do [[ $t == $3 ]] && echo "$t"; done; exit 0 ;;
    rev-parse) for t in $TAGS; do [ "refs/tags/$t" = "$4" ] && exit 0; done; exit 1 ;;
esac
exit 1'''


class ReleaseVersion(Temp):
    def version(self, current, bump, pre=False, tags=()):
        (self.d / "VERSION").write_text(current + "\n")
        out = self.d / "github-output"
        out.write_text("")
        bin_ = stubs(self.d / "bin", git=GIT)
        r = subprocess.run(["bash", "-e", "-c", step_script("release.yml", "Work out the version")], cwd=self.d,
                           env={**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "BUMP": bump,
                                "PRE": "true" if pre else "false", "TAGS": " ".join(tags), "GITHUB_OUTPUT": str(out)},
                           capture_output=True, text=True, timeout=30)
        return r.returncode, out.read_text().strip().removeprefix("version="), r.stdout

    def test_after_a_release(self):
        self.assertEqual(self.version("0.6.1", "patch")[1], "0.6.2")
        self.assertEqual(self.version("0.6.1", "minor")[1], "0.7.0")
        self.assertEqual(self.version("0.6.1", "major")[1], "1.0.0")
        self.assertEqual(self.version("0.6.1", "patch", pre=True, tags=("v0.6.1",))[1], "0.6.2-rc.1")

    def test_after_a_pre_release(self):
        """X.Y.Z-rc.N: the next rc, then X.Y.Z itself (not X.Y.Z+1)."""
        tags = ("v0.6.1", "v0.6.2-rc.1")
        self.assertEqual(self.version("0.6.2-rc.1", "patch", pre=True, tags=tags)[1], "0.6.2-rc.2")
        self.assertEqual(self.version("0.6.2-rc.2", "patch", tags=tags + ("v0.6.2-rc.2",))[1], "0.6.2")
        self.assertEqual(self.version("0.6.2-rc.1", "minor", tags=tags)[1], "0.7.0")     # (a bigger bump)
        self.assertEqual(self.version("0.7.0-rc.1", "minor", tags=("v0.7.0-rc.1",))[1], "0.7.0")
        self.assertEqual(self.version("0.7.0-rc.1", "major", tags=("v0.7.0-rc.1",))[1], "1.0.0")
        self.assertEqual(self.version("1.0.0-rc.1", "major", tags=("v1.0.0-rc.1",))[1], "1.0.0")

    def test_an_existing_tag_is_refused(self):
        rc, _v, out = self.version("0.6.1", "patch", tags=("v0.6.2",))
        self.assertNotEqual(rc, 0)
        self.assertIn("v0.6.2 already exists", out)


class ReleaseNotes(Temp):
    def run_step(self, unreleased, version="0.6.2"):
        (self.d / "CHANGELOG.md").write_text(f"# Changelog\n\n## Unreleased\n{unreleased}\n## 0.6.1 (2026-10-14)\n\n- Old.\n")
        (self.d / "share/metainfo").mkdir(parents=True, exist_ok=True)
        (self.d / "share/metainfo/x.metainfo.xml").write_text('<component>\n  <releases>\n    <release version="0.6.1"/>\n'
                                                               '  </releases>\n</component>\n')
        (self.d / "VERSION").write_text("0.6.1\n")
        return subprocess.run(["bash", "-e", "-c", step_script("release.yml", "Changelog and VERSION")], cwd=self.d,
                              env={**os.environ, "V": version}, capture_output=True, text=True, timeout=30)

    def test_an_empty_section_is_refused(self):
        r = self.run_step("\n")        # (the heading's blank line, nothing else)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("the Unreleased section is empty", r.stdout)
        self.assertEqual((self.d / "VERSION").read_text(), "0.6.1\n")

    def test_notes_changelog_version_metainfo(self):
        r = self.run_step("\n### Fixed\n- A fix.\n", version="0.6.2-rc.1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("- A fix.", (self.d / "notes.md").read_text())
        self.assertNotIn("Old.", (self.d / "notes.md").read_text())
        self.assertRegex((self.d / "CHANGELOG.md").read_text(), r"\n## 0\.6\.2-rc\.1 \(\d{4}-\d\d-\d\d\)\n")
        self.assertEqual((self.d / "VERSION").read_text(), "0.6.2-rc.1\n")
        self.assertRegex((self.d / "share/metainfo/x.metainfo.xml").read_text(),
                         r'<releases>\n    <release version="0\.6\.2-rc\.1" date="[0-9-]+" type="development"/>\n    <release version="0\.6\.1"/>')


class CheckDocs(Temp):
    def test_a_broken_html_picture_is_reported(self):
        (self.d / "dev").mkdir()
        shutil.copy(ROOT / "dev/check-docs.py", self.d / "dev")
        for pack in ("core", "integrations", "third-party"):
            (self.d / "packs" / pack).mkdir(parents=True)
        (self.d / "docs").mkdir()
        (self.d / "docs/here.png").write_bytes(b"")
        (self.d / "README.md").write_text('<p align="center"><img src="docs/here.png" width="9" alt="ok"></p>\n\n'
                                          '<img src="docs/gone.png" alt="moved">\n\n[here](docs/here.png) `<img src="code.png">`\n')
        r = subprocess.run([sys.executable, str(self.d / "dev/check-docs.py")], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(r.stdout.strip(), "README.md: broken link docs/gone.png")


class GenDocs(Temp):
    def test_an_upstream_readme_no_longer_named_goes(self):
        repo = copy_repo(self.d / "repo")
        official = [p for pack in ("core", "integrations", "third-party") for p in sorted(repo.glob(f"packs/{pack}/*/README.md"))]
        readme = next((p for p in official            # (not a local pack's: gen-docs leaves those alone)
                       if any(l.startswith("upstream_readme:") for l in p.read_text().splitlines())), None)
        if not readme:
            self.skipTest("no tweak has upstream_readme:")
        text = readme.read_text()
        self.assertIn("<!-- generated:upstream ", text)
        readme.write_text("".join(l for l in text.splitlines(True) if not l.startswith("upstream_readme:")))
        gen = [sys.executable, str(repo / "dev/gen-docs.py")]
        self.assertNotEqual(subprocess.run(gen + ["--check"], capture_output=True, timeout=120).returncode, 0)
        subprocess.run(gen, check=True, capture_output=True, timeout=120)
        after = readme.read_text()
        self.assertNotIn("generated:upstream", after)
        self.assertTrue(after.endswith("\n") and not after.endswith("\n\n"))
        self.assertEqual(subprocess.run(gen + ["--check"], capture_output=True, timeout=120).returncode, 0)


i18ntool = load_script(ROOT / "dev/i18n.py", "i18ntool")
HEADER = 'msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n'


class Translations(Temp):
    """dev/i18n.py update and import: a removed text's translation stays as a #~ comment."""
    LONG = "Una traducción bastante larga, de más de setenta caracteres, como la de casi cualquier frase."

    def setUp(self):
        super().setUp()
        self.po = self.d / "xx.po"
        self.po.write_text(HEADER + '\n#: a.py:1\nmsgid "Kept"\nmsgstr "Queda"\n\n#: a.py:2\nmsgid "Removed"\nmsgstr "Quitado"\n\n'
                           '#: a.py:3\nmsgid "A long one"\nmsgstr ' + i18ntool.quote(self.LONG) + '\n\n#: a.py:4\nmsgid "To do"\nmsgstr ""\n')
        self.pot = HEADER + '\n#: a.py:1\nmsgid "Kept"\nmsgstr ""\n\n#: a.py:4\nmsgid "To do"\nmsgstr ""\n'

    def test_kept_through_later_updates_and_imports(self):
        i18ntool.update(self.po, self.pot)
        first = self.po.read_text()
        self.assertIn('#~ msgid "Removed"\n#~ msgstr "Quitado"', first)
        self.assertIn(self.LONG, first)                       # (a long translation spans two lines)
        i18ntool.update(self.po, self.pot)
        self.assertEqual(self.po.read_text(), first)
        i18ntool.fill(self.po, {(None, "To do"): "Hecho"})
        self.assertIn('#~ msgid "Removed"', self.po.read_text())
        self.assertIn('msgstr "Hecho"', self.po.read_text())

    def test_back_in_use_when_the_text_returns(self):
        i18ntool.update(self.po, self.pot)
        i18ntool.update(self.po, self.pot + '\n#: b.py:7\nmsgid "Removed"\nmsgstr ""\n')
        text = self.po.read_text()
        self.assertIn('#: b.py:7\nmsgid "Removed"\nmsgstr "Quitado"', text)
        self.assertNotIn('#~ msgid "Removed"', text)


class CheckPins(Temp):
    def test_a_hugging_face_file_is_compared_at_main(self):
        """version= is the revision's start; the url has all of it. The file at main changed."""
        rev = "5359861c739e955e79d9a303bcbc70fb988958b1"
        (self.d / "dev").mkdir()
        shutil.copy(ROOT / "dev/check-pins.sh", self.d / "dev")
        (self.d / "lib").mkdir()
        (self.d / "lib/python-constraints.txt").write_text("")
        (self.d / "packs/core/model").mkdir(parents=True)
        (self.d / "packs/core/model/pin").write_text(
            f"version={rev[:8]}\nurl=https://huggingface.co/o/r/resolve/{rev}/m.bin\nsha256={'a' * 64}\n"
            "latest=https://huggingface.co/api/models/o/r/revision/main\n")
        log = self.d / "curl.log"
        bin_ = stubs(self.d / "bin", curl=f'''url=; for a in "$@"; do case $a in http*) url=$a ;; esac; done
echo "$url" >> {log}
case $url in
    */revision/main) echo '{{"sha": "{"b" * 40}"}}' ;;
    */resolve/main/m.bin) printf 'HTTP/2 200\\r\\nx-linked-etag: "{"c" * 64}"\\r\\n\\r\\n' ;;
    */resolve/{rev}/m.bin) printf 'HTTP/2 200\\r\\nx-linked-etag: "{"a" * 64}"\\r\\n\\r\\n' ;;
    *) exit 22 ;;
esac''')
        r = subprocess.run(["bash", str(self.d / "dev/check-pins.sh")], env={**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}"},
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("model: pinned 5359861c; the file changed at bbbbbbbb", r.stdout)
        self.assertIn("/resolve/main/m.bin", log.read_text())


class CheckUpstream(Temp):
    def test_a_check_pins_that_stopped_is_reported(self):
        (self.d / "dev").mkdir()
        shutil.copy(ROOT / "dev/check-upstream.sh", self.d / "dev")
        stubs(self.d / "dev", **{"check-pins.sh": 'echo "speech: pinned 1.0; upstream has 2.0"; exit 1'})
        (self.d / "lib").mkdir()
        (self.d / "lib/tested-versions").write_text("scrcpy=3.3\nsteamos-glibc=2.41\nsteamos-glibcxx=3.4.34\n")
        (self.d / "lib/common.sh").write_text('ALARM_MIRROR="${ALARM_MIRROR:-https://alarm.invalid/aarch64}"\n')
        bin_ = stubs(self.d / "bin", curl="exit 7", gh="exit 1", git="exit 1")      # no network, gh or git
        r = subprocess.run(["bash", str(self.d / "dev/check-upstream.sh")], env={**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}"},
                           capture_output=True, text=True, timeout=120)
        self.assertIn("- speech: pinned 1.0; upstream has 2.0", r.stdout)
        self.assertIn("`dev/check-pins.sh` stopped early (exit 1)", r.stdout)
        self.assertNotIn("All clear", r.stdout)


class UpstreamIssue(Temp):
    def test_an_empty_report_leaves_the_issue_alone(self):
        """(dev/check-upstream.sh broke): the run fails instead of emptying the open issue."""
        log = self.d / "gh.log"
        bin_ = stubs(self.d / "bin", gh=f'echo "gh $*" >> {log}\ncase "$1 $2" in "issue list") echo 7 ;; '
                                         f'"issue view") printf "Checked.\\n\\n- old\\n" ;; esac')
        (self.d / "report.md").write_text("")
        r = subprocess.run(["bash", str(ROOT / "dev/upstream-issue.sh"), str(self.d / "report.md")],
                           env={**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}"}, capture_output=True, text=True, timeout=60)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("issue edit", log.read_text() if log.exists() else "")


class AgentWorktree(Temp):
    def test_a_worktree_holding_others_isnt_removed(self):
        """Removing tmp/a would delete tmp/a/tmp/b (and its uncommitted work) with it. (git: a stand-in)"""
        log = self.d / "git.log"
        bin_ = stubs(self.d / "bin", git=f'''echo "git $*" >> {log}
case "$*" in
    "rev-parse --show-toplevel") echo /r ;;
    "worktree list --porcelain") printf "worktree /r\\n\\nworktree /r/tmp/a\\n\\nworktree /r/tmp/a/tmp/b\\n\\nworktree /r/tmp/ab\\n" ;;
esac
exit 0''')
        run = lambda *a: subprocess.run(["bash", str(ROOT / "dev/agent-worktree.sh"), *a], env={**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}"},
                                        capture_output=True, text=True, timeout=60)
        r = run("remove", "a")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("holds 1 other worktree", r.stderr)
        self.assertNotIn("worktree remove", log.read_text())
        self.assertEqual(run("remove", "ab").returncode, 0)            # (tmp/ab is not inside tmp/a)
        self.assertIn("git worktree remove --force /r/tmp/ab", log.read_text())
        r = run("prune", "--apply")
        self.assertIn("keep:   /r/tmp/a (other worktrees inside it)", r.stdout)
        self.assertNotIn("worktree remove --force /r/tmp/a\n", log.read_text())


MANIFEST = """---
title: {id}
emoji: 🧪
category: Examples
tier: extras
summary: A test tweak
what: Nothing useful.
why: It tests dev/test-tweaks.sh.
author: test
changes: nothing
access: None
survives_updates: Yes (it is all in the home folder)
undo: nothing
test: {{offline: true}}
---
# {id}
"""


class TestTweaks(Temp):
    """dev/test-tweaks.sh notices a write into the checkout (its copy in the work folder) and files
    left in /tmp that kept an old date (as files unpacked from an archive do), but not a file a
    program already running writes meanwhile (a live adb server's log)."""

    def tweak(self, repo, tid, install):
        d = repo / "packs/core" / tid
        d.mkdir()
        (d / "README.md").write_text(MANIFEST.format(id=tid))
        for script, body in (("install.sh", install), ("status.sh", 'status_ok "fine"'), ("uninstall.sh", ":")):
            (d / script).write_text(f'#!/bin/bash\nsource "$FRAME_TWEAKS_LIB/common.sh"\n{body}\n')

    def test_writes_outside_the_home_are_caught(self):
        repo = copy_repo(self.d / "repo")
        token = uuid.uuid4().hex[:12]
        self.addCleanup(lambda: [shutil.rmtree(p, ignore_errors=True) for p in Path("/tmp").glob(f"ft-leak-{token}.*")])
        self.tweak(repo, "leak-repo", 'echo state > "$TWEAK_DIR/state.txt"')
        self.tweak(repo, "leak-tmp", f'T=$(mktemp -d /tmp/ft-leak-{token}.XXXXXX); echo x > "$T/file"; touch -d @1000000000 "$T/file"')
        path = os.environ["PATH"]
        if not shutil.which("bsdtar"):          # (the harness asks for it; these tweaks unpack nothing)
            path = f"{stubs(self.d / 'bin', bsdtar='exit 1')}:{path}"
        r = subprocess.run(["bash", str(repo / "dev/test-tweaks.sh"), "leak-repo", "leak-tmp"],
                           env={**os.environ, "PATH": path}, capture_output=True, text=True, timeout=300)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        out = r.stdout.split("\nFAIL leak-tmp")
        self.assertIn("FAIL leak-repo: wrote outside the test home:", out[0])
        self.assertRegex(out[0], r"(?m)^    \S*/repo/packs/core/leak-repo/state\.txt$")
        self.assertEqual(len(out), 2, r.stdout + r.stderr)
        self.assertTrue(out[1].startswith(": wrote outside the test home:\n"), out[1])
        self.assertRegex(out[1], rf"(?m)^    /tmp/ft-leak-{token}\.\w+/file$")

    def test_a_file_a_running_program_writes_isnt_the_tweaks(self):
        repo = copy_repo(self.d / "repo")
        log = Path(f"/tmp/ft-held-{uuid.uuid4().hex[:12]}.log")
        self.addCleanup(log.unlink, missing_ok=True)
        writer = subprocess.Popen(["bash", "-c", f'exec 3>>"{log}"; while :; do echo x >&3; sleep 0.2; done'])
        self.addCleanup(writer.wait)
        self.addCleanup(writer.kill)
        for _ in range(100):                      # (open, and written, before the run starts)
            if log.exists() and log.stat().st_size:
                break
            time.sleep(0.05)
        self.tweak(repo, "quiet", ":")
        path = os.environ["PATH"]
        if not shutil.which("bsdtar"):
            path = f"{stubs(self.d / 'bin', bsdtar='exit 1')}:{path}"
        r = subprocess.run(["bash", str(repo / "dev/test-tweaks.sh"), "quiet"],
                           env={**os.environ, "PATH": path}, capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ok   quiet", r.stdout)

    @unittest.skipUnless(subprocess.run(["unshare", "-cn", "true"], capture_output=True).returncode == 0
                         if shutil.which("unshare") else False, "no unprivileged network namespaces here")
    def test_no_network_for_the_scripts(self):
        """A tweak that reaches a local service (as one did SteamVR's 127.0.0.1:8087) can't."""
        repo = copy_repo(self.d / "repo")
        server = socket.socket()
        self.addCleanup(server.close)
        server.bind(("127.0.0.1", 0))
        server.listen(8)
        port = server.getsockname()[1]
        self.tweak(repo, "netcheck", f"""python3 -c 'import socket; socket.create_connection(("127.0.0.1", {port}), 3)' 2>/dev/null &&
    {{ echo "reached 127.0.0.1:{port}"; exit 1; }}
true""")
        path = os.environ["PATH"]
        if not shutil.which("bsdtar"):
            path = f"{stubs(self.d / 'bin', bsdtar='exit 1')}:{path}"
        harness = lambda p: subprocess.run(["bash", str(repo / "dev/test-tweaks.sh"), "netcheck"],     # (writes elsewhere: not this test's)
                                           env={**os.environ, "PATH": p, "TEST_IGNORE": "."}, capture_output=True, text=True, timeout=300)
        r = harness(path)
        self.assertEqual(r.stdout.strip(), "ok   netcheck", r.stdout + r.stderr)
        r = harness(f"{stubs(self.d / 'nons', unshare='exit 1')}:{path}")      # (no namespaces: as before)
        self.assertIn("note: no network namespace here", r.stderr)
        self.assertIn("FAIL netcheck: install failed", r.stdout)
        self.assertIn(f"reached 127.0.0.1:{port}", r.stdout)


if __name__ == "__main__":
    unittest.main()
