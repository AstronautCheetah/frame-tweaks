#!/usr/bin/env python3
"""For maintainers: (re)build packs/core/speech/voices.tsv, the languages the Speech engine
settings offer: for each, a Piper voice from rhasspy/piper-voices at the revision voice.pin pins
(with the SHA256 of its two files, so the installer can check them) and the matching eSpeak NG
voice. Edit LANGUAGES below, run this, review the diff, commit.

  dev/speech-voices.py"""
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEECH = ROOT / "packs/core/speech"
# (code, label, Piper voice, eSpeak NG voice): popular languages, one natural Piper voice each.
LANGUAGES = [
    ("en_US", "English (US)", "en_US-ljspeech-medium", "en-us"),
    ("en_GB", "English (UK)", "en_GB-alba-medium", "en-gb"),
    ("de_DE", "Deutsch", "de_DE-thorsten-medium", "de"),
    ("fr_FR", "Français", "fr_FR-siwis-medium", "fr-fr"),
    ("es_ES", "Español (España)", "es_ES-davefx-medium", "es"),
    ("es_MX", "Español (México)", "es_MX-ald-medium", "es-419"),
    ("it_IT", "Italiano", "it_IT-paola-medium", "it"),
    ("pt_BR", "Português (Brasil)", "pt_BR-faber-medium", "pt-br"),
    ("nl_NL", "Nederlands", "nl_NL-pim-medium", "nl"),
    ("pl_PL", "Polski", "pl_PL-darkman-medium", "pl"),
    ("cs_CZ", "Čeština", "cs_CZ-jirka-medium", "cs"),
    ("sv_SE", "Svenska", "sv_SE-nst-medium", "sv"),
    ("tr_TR", "Türkçe", "tr_TR-fahrettin-medium", "tr"),
    ("ru_RU", "Русский", "ru_RU-irina-medium", "ru"),
    ("uk_UA", "Українська", "uk_UA-ukrainian_tts-medium", "uk"),
    ("ar_JO", "العربية", "ar_JO-kareem-medium", "ar"),
    ("hi_IN", "हिन्दी", "hi_IN-pratham-medium", "hi"),
    ("zh_CN", "中文 (普通话)", "zh_CN-huayan-medium", "cmn"),
]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "frame-tweaks"}), timeout=120) as r:
        return r.read()


def main():
    rev = next(l.split("=", 1)[1].strip() for l in (SPEECH / "voice.pin").read_text().splitlines() if l.startswith("version="))
    base = f"https://huggingface.co/rhasspy/piper-voices/resolve/{rev}/"
    voices = json.loads(get(base + "voices.json"))
    rows = ["# code\tlabel\tPiper voice file (in rhasspy/piper-voices at voice.pin's revision)\tits SHA256"
            "\tits .json's SHA256\teSpeak NG voice   (made by dev/speech-voices.py)"]
    for code, label, key, espeak in LANGUAGES:
        onnx = next(p for p in voices[key]["files"] if p.endswith(".onnx"))
        folder = onnx.rsplit("/", 1)[0]
        tree = json.loads(get(f"https://huggingface.co/api/models/rhasspy/piper-voices/tree/{rev}/{urllib.parse.quote(folder)}"))
        lfs = next(f["lfs"]["oid"] for f in tree if f["path"] == onnx)       # the large file's SHA256
        js = hashlib.sha256(get(base + urllib.parse.quote(onnx + ".json"))).hexdigest()
        rows.append("\t".join((code, label, onnx, lfs, js, espeak)))
        print(code, onnx, file=sys.stderr)
    (SPEECH / "voices.tsv").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    main()
