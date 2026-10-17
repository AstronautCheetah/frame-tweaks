"""get.sh, the bootstrap: it installs the newest release tag of the channel (stable, or beta with
pre-releases ranked below their release; given, or kept from before), says so when there is no
release, runs install.sh by its full path (FRAME_TWEAKS_DIR relative too), and on an existing
checkout runs ./install.sh update (signature check and all), stopping, without opening the old
version, when that fails. Against a stand-in repository whose install.sh only logs how it was run
(and fails "update" when FAIL_UPDATE is set)."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("git"), "needs git")
class GetSh(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.log = self.tmp / "install.log"
        self.env = {"HOME": str(self.tmp / "home"), "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
                    "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "t@t", "LOG": str(self.log)}
        (self.tmp / "home").mkdir()
        self.src = self.tmp / "src"
        self.git(self.tmp, "init", "-q", str(self.src))
        (self.src / "install.sh").write_text('#!/bin/bash\necho "install.sh $*" >> "$LOG"\necho "$0" >> "$LOG.run-as"\n'
                                             '[ "${1:-}" = update ] && [ -n "${FAIL_UPDATE:-}" ] && exit "$FAIL_UPDATE"; exit 0\n')
        (self.src / "install.sh").chmod(0o755)
        self.dest = self.tmp / "frame-tweaks"

    def git(self, where, *args):
        return subprocess.run(["git", "-C", str(where), *args], env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def release(self, *tags):
        for tag in tags:
            (self.src / "VERSION").write_text(tag + "\n")
            self.git(self.src, "add", "-A")
            self.git(self.src, "commit", "-qm", tag)
            self.git(self.src, "tag", "-a", tag, "-m", tag)

    def get(self, **extra):
        return subprocess.run(["bash", str(ROOT / "get.sh")], capture_output=True, text=True, timeout=60,
                              env={**self.env, "FRAME_TWEAKS_REPO": f"file://{self.src}",
                                   "FRAME_TWEAKS_DIR": str(self.dest), **extra})

    def ran(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def at(self):
        return (self.dest / "VERSION").read_text().strip()

    def test_installs_the_newest_stable_release(self):
        self.release("v0.9.0", "v0.10.0", "v0.11.0-rc.1")
        r = self.get()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.at(), "v0.10.0")
        self.assertEqual(self.ran(), ["install.sh menu", "install.sh "])     # (then the installer)

    def test_the_channel_given_is_kept_for_updates(self):
        """The testers' link (FRAME_TWEAKS_CHANNEL=beta) is remembered: updates take test releases too."""
        self.release("v0.10.0", "v0.11.0-rc.1")
        channel = self.tmp / "home/.config/frame-tweaks/channel"
        self.assertEqual(self.get().returncode, 0)
        self.assertFalse(channel.exists())                            # (none given: none written)
        shutil.rmtree(self.dest)
        self.assertEqual(self.get(FRAME_TWEAKS_CHANNEL="beta").returncode, 0)
        self.assertEqual(channel.read_text(), "beta\n")
        r = self.get(FRAME_TWEAKS_CHANNEL="stable")                    # (installed: an update)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(channel.read_text(), "stable\n")
        r = self.get(FRAME_TWEAKS_CHANNEL="nightly")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("stable or beta", r.stderr)

    def test_a_channel_kept_from_before_counts_for_a_new_install(self):
        """Installed again (its settings kept): ~/.config/frame-tweaks/channel says beta, as updates
        read it, unless FRAME_TWEAKS_CHANNEL says otherwise."""
        self.release("v0.10.0", "v0.11.0-rc.1")
        channel = self.tmp / "home/.config/frame-tweaks/channel"
        channel.parent.mkdir(parents=True)
        channel.write_text("beta\n")
        r = self.get()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.at(), "v0.11.0-rc.1")
        shutil.rmtree(self.dest)
        self.assertEqual(self.get(FRAME_TWEAKS_CHANNEL="stable").returncode, 0)
        self.assertEqual(self.at(), "v0.10.0")

    def test_a_relative_folder(self):
        """FRAME_TWEAKS_DIR=frame-tweaks, relative: install.sh is run by its full path (by a
        relative one with a folder in it, it couldn't find itself)."""
        self.release("v0.10.0")
        r = subprocess.run(["bash", str(ROOT / "get.sh")], cwd=self.tmp, capture_output=True, text=True, timeout=60,
                           env={**self.env, "FRAME_TWEAKS_REPO": f"file://{self.src}", "FRAME_TWEAKS_DIR": "frame-tweaks"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.at(), "v0.10.0")
        self.assertEqual(self.ran(), ["install.sh menu", "install.sh "])
        self.assertEqual(Path(f"{self.log}.run-as").read_text().split(), [str(self.dest / "install.sh")] * 2)

    def test_beta_takes_a_pre_release_but_not_over_its_release(self):
        self.release("v0.10.0", "v0.11.0-rc.1")
        self.assertEqual(self.get(FRAME_TWEAKS_CHANNEL="beta").returncode, 0)
        self.assertEqual(self.at(), "v0.11.0-rc.1")
        self.release("v0.11.0")
        shutil.rmtree(self.dest)                          # (a new install: an update is install.sh's)
        self.assertEqual(self.get(FRAME_TWEAKS_CHANNEL="beta").returncode, 0)
        self.assertEqual(self.at(), "v0.11.0")

    def test_an_existing_checkout_is_updated_by_install_sh(self):
        """With its checks: the signature against this copy's release key, the installers again."""
        self.release("v0.9.0")
        self.assertEqual(self.get().returncode, 0)
        self.log.unlink()
        self.release("v0.10.0")
        r = self.get()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Updating", r.stdout)
        self.assertEqual(self.ran(), ["install.sh update", "install.sh menu", "install.sh "])

    def test_no_release_says_so(self):
        self.release("v0.11.0-rc.1")                      # (a pre-release only: none for stable)
        r = self.get()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Couldn't find a release", r.stderr)
        self.assertFalse(self.dest.exists())

    def test_a_checkout_that_cant_update_doesnt_open_the_old_version(self):
        self.release("v0.9.0")
        self.assertEqual(self.get().returncode, 0)
        self.log.unlink()
        self.release("v0.10.0")
        r = self.get(FAIL_UPDATE="1")                      # (say, a release that isn't signed)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.at(), "v0.9.0")
        self.assertEqual(self.ran(), ["install.sh update"])


    def test_an_update_where_a_tweak_failed_still_opens_the_window(self):
        """update's exit 3: Frame Tweaks updated, but a tweak didn't install again. The window
        shows which, so it's opened, unlike an update that couldn't happen."""
        self.release("v0.9.0")
        self.assertEqual(self.get().returncode, 0)
        self.log.unlink()
        self.release("v0.10.0")
        r = self.get(FAIL_UPDATE="3")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Some tweaks didn't update", r.stdout)
        self.assertEqual(self.ran(), ["install.sh update", "install.sh menu", "install.sh "])


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(shutil.which("git"), "needs git")
class GetShLanguage(unittest.TestCase):
    """get.sh's own words come before Frame Tweaks' translations are on the machine, so they carry
    theirs (dev/i18n.py writes them in), in the language Frame Tweaks would pick: Steam's own
    interface language too (SteamOS keeps LANG at en_US.UTF-8 whatever the Frame was set up in)."""
    def setUp(self):
        import sys
        from unittest import mock
        sys.path.insert(0, str(ROOT / "tests"))
        from helpers import load_script
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        locale = self.tmp / "locale"
        locale.mkdir()
        for lang, text in (("fr", "Impossible de trouver une version de %s"),
                           ("nl_BE", "Geen versie van %s gevonden ('t is \\\\ raar)")):
            (locale / f"{lang}.po").write_text(f'msgid ""\nmsgstr ""\n\nmsgid "Couldn\'t find a release of %s"\n'
                                               f'msgstr "{text}"\n')
        tool = load_script(ROOT / "dev/i18n.py", "i18n_tool_get")
        with mock.patch.object(tool, "LOCALE", locale):
            self.script = self.tmp / "get.sh"
            self.script.write_text(tool.get_sh_text((ROOT / "get.sh").read_text()))
        (self.tmp / "home/.steam").mkdir(parents=True)

    def say(self, steam="english", **env):
        (self.tmp / "home/.steam/registry.vdf").write_text(
            '"Registry"\n{\n\t"HKCU"\n\t{\n\t\t"Software"\n\t\t{\n\t\t\t"Valve"\n\t\t\t{\n\t\t\t\t"Steam"\n'
            f'\t\t\t\t{{\n\t\t\t\t\t"language"\t\t"{steam}"\n\t\t\t\t}}\n\t\t\t}}\n\t\t}}\n\t}}\n}}\n')
        r = subprocess.run(["bash", str(self.script)], capture_output=True, text=True, timeout=60,
                           env={"HOME": str(self.tmp / "home"), "PATH": "/usr/bin:/bin", "LANG": "en_US.UTF-8",
                                "GIT_CONFIG_NOSYSTEM": "1", "FRAME_TWEAKS_REPO": str(self.tmp / "no-such-repo"),
                                "FRAME_TWEAKS_DIR": str(self.tmp / "ft"), **env})
        self.assertEqual(r.returncode, 1)
        return r.stderr.strip().splitlines()[-1]

    def test_in_steams_language(self):
        repo = self.tmp / "no-such-repo"
        self.assertEqual(self.say("french"), f"Impossible de trouver une version de {repo}")
        self.assertEqual(self.say("dutch"), f"Geen versie van {repo} gevonden ('t is \\ raar)")   # (nl: the Flemish)
        self.assertEqual(self.say("english"), f"Couldn't find a release of {repo}")

    def test_a_language_set_on_purpose_wins(self):
        repo = self.tmp / "no-such-repo"
        self.assertEqual(self.say("english", LANG="fr_CA.UTF-8"), f"Impossible de trouver une version de {repo}")
        self.assertEqual(self.say("dutch", FRAME_TWEAKS_LANGUAGE="fr"), f"Impossible de trouver une version de {repo}")
        (self.tmp / "home/.config/frame-tweaks").mkdir(parents=True)
        (self.tmp / "home/.config/frame-tweaks/language").write_text("en\n")          # (chosen in ⚙ Preferences)
        self.assertEqual(self.say("french"), f"Couldn't find a release of {repo}")
        self.assertEqual(self.say("french", FRAME_TWEAKS_KEYBOARD="0", FRAME_TWEAKS_PREFERENCE_FILE="/dev/null"),
                         f"Couldn't find a release of {repo}")                         # (no guessing)

    def test_the_real_get_sh_is_current(self):
        """dev/i18n.py update keeps its block as the translations have it (check fails otherwise)."""
        from helpers import load_script
        tool = load_script(ROOT / "dev/i18n.py", "i18n_tool_get2")
        self.assertEqual(tool.get_sh_text((ROOT / "get.sh").read_text()), (ROOT / "get.sh").read_text())
