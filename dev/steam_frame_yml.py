#!/usr/bin/env python3
"""steam-frame.yml: check it as frame-commons' catalog will (its spec, version 0:
https://github.com/frame-commons/catalog/blob/main/spec/steam-frame-yml.md), so a mistake shows up
here instead of in the catalog's PROBLEMS.md a week later; and read its test records, for
dev/gen-docs.py's "Tested on" table in README.md. dev/check.sh runs it (docs).

  dev/steam_frame_yml.py [FILE]      check it (default: steam-frame.yml); exit 1 with the problems

The check is the catalog's own (dev/fccatalog_manifest.py, copied unchanged), which needs PyYAML;
without it (SteamOS's Python, a Mac's) only Frame Tweaks' own reader checks the file. That reader
(lib/manifest.py, no dependencies) refuses what YAML readers disagree on, so the dates are quoted
("2026-11-02"), which the catalog takes as well as a YAML date."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "dev"))
import manifest  # noqa: E402


def records(path=ROOT / "steam-frame.yml"):
    """The test records, oldest first (lib/manifest.py; ValueError if it can't read the file)."""
    data, _ = manifest.front_matter("---\n" + Path(path).read_text() + "---\n")
    return list(data.get("tested") or [])


def problems(path=ROOT / "steam-frame.yml"):
    """What's wrong with it ([]: nothing), and whether the catalog's checker ran (needs PyYAML)."""
    text = Path(path).read_text()
    try:
        manifest.front_matter("---\n" + text + "---\n")
    except ValueError as e:
        return [f"lib/manifest.py can't read it: {e}"], False
    try:
        import fccatalog_manifest as catalog
    except ImportError:                 # (no PyYAML here)
        return [], False
    try:
        catalog.parse(text)
    except catalog.ManifestError as e:
        return list(e.problems), True
    return [], True


def main(argv):
    path = Path(argv[0]) if argv else ROOT / "steam-frame.yml"
    found, ran = problems(path)
    for line in found:
        print(f"{path.name}: {line}", file=sys.stderr)
    if not found:
        how = "the catalog's checker" if ran else "lib/manifest.py only (no PyYAML for the catalog's checker)"
        print(f"{path.name}: fine, by {how}; {len(records(path))} test records")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
