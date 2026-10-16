"""lib/menuedits.py: your edits to a menu entry, told from Frame Tweaks' own changes and kept when
it writes the entry again (wallet-launcher's wrappers)."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import kde_saves  # noqa: E402  (and lib/ importable)
import menuedits  # noqa: E402

BASE = """[Desktop Entry]
X-FrameTweaks-Wallet=true
Name=Notes
Exec=/home/u/.local/bin/wallet-gate /usr/bin/flatpak run --branch=stable org.notes @@u %U @@
Icon=org.notes
Comment=Write things down
Keywords=notes;text;
DBusActivatable=false

[Desktop Action new]
Name=New note
Exec=/usr/bin/flatpak run org.notes --new
"""


class Yours(unittest.TestCase):
    def test_only_what_you_changed(self):
        mine = kde_saves(BASE, Name="My notes", Icon="accessories-text-editor")
        self.assertEqual(menuedits.yours(BASE, mine), {
            ("Desktop Entry", "Icon"): "accessories-text-editor", ("Desktop Entry", "Name"): "My notes",
            ("Desktop Entry", "Path"): "", ("Desktop Entry", "Terminal"): "false",
            ("Desktop Entry", "X-KDE-SubstituteUID"): "false"})      # (the command: only quoted another way)
        self.assertEqual(menuedits.yours(BASE, BASE), {})

    def test_a_line_removed_and_a_command_changed(self):
        mine = BASE.replace("Keywords=notes;text;\n", "").replace("@@u %U @@", "--dark @@u %U @@")
        self.assertEqual(menuedits.yours(BASE, mine), {
            ("Desktop Entry", "Exec"): "/home/u/.local/bin/wallet-gate /usr/bin/flatpak run --branch=stable org.notes "
                                       "--dark @@u %U @@",
            ("Desktop Entry", "Keywords"): None})

    def test_a_label_in_another_language_isnt_yours(self):
        """lib/i18n.py relabel puts a Frame Tweaks entry's name in the keyboard's language."""
        base = "[Desktop Entry]\nName=Lock Wallet\nX-Frame-Tweaks-Name=Lock Wallet\nName[es]=Bloquear cartera\n"
        self.assertEqual(menuedits.yours(base, base.replace("\nName=Lock Wallet\n", "\nName=Bloquear cartera\n")), {})
        self.assertEqual(menuedits.yours(base, base.replace("\nName=Lock Wallet\n", "\nName=Lock up\n")),
                         {("Desktop Entry", "Name"): "Lock up"})
        self.assertEqual(menuedits.yours("[Desktop Entry]\nName=Lock Wallet\n", "[Desktop Entry]\nName=Notes\n"),
                         {("Desktop Entry", "Name"): "Notes"})          # (no X-Frame-Tweaks-Name: not one of ours)


class WithYours(unittest.TestCase):
    def test_into_a_new_version(self):
        """The app's new version changed its comment and keywords: those come through; your name,
        icon, removed line and added ones stay; owned keys stay the new version's."""
        mine = kde_saves(BASE, Name="My notes", Icon="my-icon", DBusActivatable="true")
        mine = mine.replace("Keywords=notes;text;\n", "")
        mine += "\n[Desktop Action mine]\nName=Mine\nExec=/opt/mine\n"
        new = BASE.replace("Write things down", "Notes, everywhere").replace("Exec=/usr/bin/flatpak run org.notes --new",
                                                                              "Exec=/usr/bin/flatpak run org.notes --new-note")
        out = menuedits.with_yours(new, menuedits.yours(BASE, mine), owned=("DBusActivatable",))
        self.assertEqual(out.splitlines(), [
            "[Desktop Entry]", "X-FrameTweaks-Wallet=true", "Name=My notes",
            "Exec=/home/u/.local/bin/wallet-gate /usr/bin/flatpak run --branch=stable org.notes @@u %U @@",
            "Icon=my-icon", "Comment=Notes, everywhere", "DBusActivatable=false",
            "Path=", "Terminal=false", "X-KDE-SubstituteUID=false",      # (yours: at the end of the group)
            "",
            "[Desktop Action new]", "Name=New note", "Exec=/usr/bin/flatpak run org.notes --new-note",
            "",
            "[Desktop Action mine]", "Name=Mine", "Exec=/opt/mine"])

    def test_your_command_goes_through_command(self):
        mine = BASE.replace("@@u %U @@", "--dark @@u %U @@")
        seen = []

        def command(group, yours):
            seen.append((group, yours))
            return "wrapped " + yours.split()[-4]
        out = menuedits.with_yours(BASE, menuedits.yours(BASE, mine), command=command)
        self.assertIn("Exec=wrapped --dark", out.splitlines())
        self.assertEqual([g for g, _c in seen], ["Desktop Entry"])
        out = menuedits.with_yours(BASE, menuedits.yours(BASE, mine), command=lambda g, c: None)
        self.assertEqual(out, BASE)                                    # (None: the new version's command)

    def test_an_entry_keeps_its_command(self):
        mine = BASE.replace("Exec=/home/u/.local/bin/wallet-gate /usr/bin/flatpak run --branch=stable org.notes @@u %U @@\n", "")
        self.assertEqual(menuedits.with_yours(BASE, menuedits.yours(BASE, mine)), BASE)

    def test_nothing_of_yours_changes_nothing(self):
        self.assertEqual(menuedits.with_yours(BASE, {}), BASE)
        self.assertEqual(menuedits.with_yours(BASE, {("Gone", "Name"): None}), BASE)



class Merge(unittest.TestCase):
    def test_a_command_both_changed_is_the_new_versions(self):
        """Yours may not run any more (the program moved): the new version's command wins; your
        name stays."""
        mine = BASE.replace("Name=Notes", "Name=Mine").replace("@@u %U @@", "--dark @@u %U @@")
        new = BASE.replace("/usr/bin/flatpak run --branch=stable", "/usr/bin/flatpak run --branch=beta")
        out = menuedits.merge(BASE, new, mine).splitlines()
        self.assertIn("Name=Mine", out)
        self.assertIn("Exec=/home/u/.local/bin/wallet-gate /usr/bin/flatpak run --branch=beta org.notes @@u %U @@", out)
        out = menuedits.merge(BASE, BASE.replace("Write things down", "New comment"), mine).splitlines()
        self.assertIn("Exec=/home/u/.local/bin/wallet-gate /usr/bin/flatpak run --branch=stable org.notes --dark "
                      "@@u %U @@", out)                                # (only yours changed: yours)
        self.assertIn("Comment=New comment", out)

    def test_keep_from_the_command_line(self):
        """lib/common.sh install_desktop: the new entry on stdin, out with your edits; as it is when
        there's nothing to tell them by."""
        d = Path(tempfile.mkdtemp())
        self.addCleanup(subprocess.run, ["rm", "-rf", str(d)])
        (d / "base").write_text(BASE)
        (d / "current").write_text(kde_saves(BASE, Icon="mine"))

        def keep(current, base):
            return subprocess.run([sys.executable, str(Path(menuedits.__file__)), "keep", str(current), str(base)],
                                  input=BASE, capture_output=True, text=True, check=True).stdout
        self.assertIn("Icon=mine", keep(d / "current", d / "base").splitlines())
        self.assertEqual(keep(d / "current", d / "none"), BASE)
        self.assertEqual(keep(d / "none", d / "base"), BASE)

if __name__ == "__main__":
    unittest.main()
