"""Your packs: one shared as a git repository added from its link, updated, or removed, and the
`mods` command (lib/sft.py mods, through ./install.sh mods) that lists, trusts, turns on or off
and checks packs.

Imported through lib/sft.py, which hands every name here on. The packs themselves come from
lib/registry.py, looked up as registry.NAME when they're used, so a test's patch there counts here.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import registry  # (lib/ is on the path: lib/sft.py put it there)
from i18n import _, ngettext

# ---- packs from a link (mods add | update | remove) --------------------------------------------
# A pack someone shares as a git repository (the pack at its top) is cloned into USER_PACKS. As any
# pack, nothing of it runs until it's trusted; an update fetches its newer version, which then
# waits to be trusted again; remove deletes it once its tweaks are uninstalled.
INSTALLED = Path.home() / ".local/state/frame-tweaks/installed"     # install records (./install.sh)
LINK = re.compile(r"^(https://|ssh://|git@[\w.-]+:|file://)[^\s]+$")
# (no ext:: transport, which runs a command; no submodules; never a password prompt; and none of
# the repository's own settings that run a command: hooks, an upload-pack or ssh command, an
# fsmonitor. A pack's .git/config is checked before git runs in it: pack_git_ok.)
GIT = ["git", "-c", "protocol.ext.allow=never", "-c", "submodule.recurse=false", "-c", "core.hooksPath=/dev/null",
       "-c", "core.fsmonitor=false", "-c", "core.sshCommand=ssh", "-c", "remote.origin.uploadpack=git-upload-pack",
       "-c", "remote.origin.receivepack=git-receive-pack"]
# What a clone made by `mods add` has in its .git/config. Anything else there (a filter, which git
# runs on pull, an include, a credential helper, a URL rewrite…) didn't come from Frame Tweaks, and
# trusting a pack covers its files, not its .git folder.
CLONE_CONFIG = re.compile(r"core\.(repositoryformatversion|filemode|bare|logallrefupdates|symlinks|ignorecase"
                          r"|precomposeunicode)|remote\.origin\.(url|fetch)|branch\.[^\s]+\.(remote|merge)"
                          r"|extensions\.(objectformat|refstorage)", re.IGNORECASE)


class PackError(Exception):
    """Why a pack couldn't be added, updated or removed (shown as it is)."""


def git(*args, cwd=None, check=True, timeout=120):
    """git's output; on failure PackError with git's last line (check), or None."""
    try:
        r = subprocess.run(GIT + list(args), cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "true", "SSH_ASKPASS": "true"})
    except FileNotFoundError:
        raise PackError(_("git isn't installed")) from None
    except subprocess.TimeoutExpired:
        raise PackError(_("git took too long (no connection?)")) from None
    if r.returncode != 0:
        if not check:
            return None
        raise PackError((r.stderr.strip().splitlines() or [_("git {command} failed").format(command=args[0])])[-1])
    return r.stdout


def plain(text):
    """Text from a pack's repository, without control characters (it's shown in a terminal too)."""
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text).strip()


def pack_folder_name(link):
    """Its folder in USER_PACKS: the repository's name (https://host/someone/my-pack.git → my-pack)."""
    name = re.sub(r"\.git$", "", link.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1])
    return re.sub(r"[^A-Za-z0-9._-]", "-", name).strip(".-") or "pack"


def pack_git_ok(d):
    """Whether a pack's .git/config holds only what a clone sets: read as a file (git config
    --file runs nothing in it)."""
    out = git("config", "--file", str(Path(d) / ".git/config"), "--name-only", "--list", check=False)
    return out is not None and all(CLONE_CONFIG.fullmatch(k.strip()) for k in out.splitlines() if k.strip())


def pack_origin(d):
    """The link a pack was added from (mods add), or None (also when its git settings aren't a
    clone's own: pack_git_ok)."""
    if not (Path(d) / ".git").is_dir() or not pack_git_ok(d):
        return None
    out = git("remote", "get-url", "origin", cwd=d, check=False)
    return plain(out) or None if out else None


def add_pack(link, ref=None):
    """Clone the pack at link (a branch or tag of it: ref) into USER_PACKS, not trusted; its folder."""
    link = link.strip()
    if not LINK.match(link):
        raise PackError(_("That isn't a link to a pack: give the address of its git repository, starting with https://"))
    if ref is not None and not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./-]*", ref):
        raise PackError(_("{ref} isn't a branch or tag name").format(ref=repr(ref)))
    dest = registry.USER_PACKS / pack_folder_name(link)
    if dest.exists():
        raise PackError(_("You have a pack in {folder} already: update it, or remove it first.").format(folder=dest))
    registry.USER_PACKS.mkdir(parents=True, exist_ok=True)
    tmp = registry.USER_PACKS / f".adding-{dest.name}"            # (a dot folder: not a pack while it comes in)
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        git("clone", "--quiet", *(["--branch", ref] if ref else []), "--", link, str(tmp))
        tops = [p for p in tmp.iterdir() if p.is_dir() and not p.name.startswith(".")]
        if not (tmp / "pack.md").is_file() and not any((p / "README.md").is_file() for p in tops):
            raise PackError(_("There's no pack at the top of {link}: no pack.md, and no tweak folders (docs/mods.md).").format(
                link=link))
        tmp.rename(dest)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    registry.load(refresh=True)
    return dest


def update_pack(d):
    """The newer version of a pack added from a link: {"files": changed files, "log": commit subjects}."""
    d = Path(d)
    if not (d / ".git").is_dir():
        raise PackError(_("{pack} wasn't added from a link: change its folder yourself.").format(pack=d.name))
    p = next((x for x in registry.load(refresh=True)["packs"] if x["dir"] == d.resolve()), None)
    if p is None or p["state"] != "trusted":
        # (git runs in its folder: only in a pack you've trusted, as for looking for updates)
        raise PackError(_("{pack} isn't trusted: trust it first ({command}), or remove it and add it again.").format(
            pack=d.name, command=f'./install.sh mods trust "{d}"'))
    if (d / ".git").is_dir() and not pack_git_ok(d):
        raise PackError(_("{pack}'s git settings (.git/config) aren't the ones adding it made, and git would act "
                          "on them: remove the pack and add it again.").format(pack=d.name))
    if not pack_origin(d):
        raise PackError(_("{pack} wasn't added from a link: change its folder yourself.").format(pack=d.name))
    if git("symbolic-ref", "-q", "HEAD", cwd=d, check=False) is None:
        raise PackError(_("{pack} was added at a fixed version: to follow another one, remove it and add it again.").format(
            pack=d.name))
    old = git("rev-parse", "HEAD", cwd=d).strip()
    git("pull", "--ff-only", "--quiet", cwd=d)
    new = git("rev-parse", "HEAD", cwd=d).strip()
    registry.load(refresh=True)
    if old == new:
        return {"files": [], "log": []}
    return {"files": [plain(x) for x in git("diff", "--name-only", old, new, cwd=d).splitlines()],
            "log": [plain(x) for x in git("log", "--format=%s", f"{old}..{new}", cwd=d).splitlines()[:20]]}


def pack_has_update(d):
    """Whether where a pack was added from has a newer version than this copy: True, False (the
    same, or one added at a fixed version), or None (couldn't look: offline, say). It only asks
    the repository for its branch's commit (git ls-remote); nothing is downloaded."""
    d = Path(d)
    if not pack_origin(d):
        return False
    branch = (git("symbolic-ref", "-q", "--short", "HEAD", cwd=d, check=False) or "").strip()
    if not branch:                                       # (a fixed version: it doesn't follow one)
        return False
    try:
        out = git("ls-remote", "--heads", "origin", f"refs/heads/{branch}", cwd=d, timeout=20)
    except PackError:
        return None
    theirs = out.split()[0] if out.split() else ""
    if not re.fullmatch(r"[0-9a-f]{40,64}", theirs):
        return None
    # (newer unless this copy already has that commit: equal, or behind work of its own)
    return git("merge-base", "--is-ancestor", theirs, "HEAD", cwd=d, check=False) is None


def packs_with_updates():
    """Your packs added from a link whose source has a newer version: their pack entries (load()).
    Only packs you trust: git reads a repository's own .git/config, which can run commands, so it
    isn't run in one you haven't trusted (nor in one changed since)."""
    return [p for p in registry.load(refresh=True)["packs"]
            if removable(p) and p["state"] == "trusted" and pack_has_update(p["dir"])]


def pack_installed(p):
    """A pack's tweaks that are installed (an install record), but not those another pack in use provides."""
    try:
        records = {f.name for f in INSTALLED.iterdir()}
    except OSError:
        records = set()
    used = {c["id"]: c for c in registry.components()}
    return [t for t in p["tweaks"] if t in records and (t not in used or used[t]["pack_dir"] == p["dir"])]


def removable(p):
    """Whether a pack can be removed here: one in your packs folder (not the official ones, nor others)."""
    return p["dir"].parent == registry.USER_PACKS.resolve()


def remove_pack(d):
    """Delete one of your packs, and its trust. Not while its tweaks are installed."""
    d = Path(d).resolve()
    p = next((x for x in registry.load(refresh=True)["packs"] if x["dir"] == d), None)
    if p is None or not removable(p):
        raise PackError(_("Only packs in {folder} can be removed here.").format(folder=registry.USER_PACKS))
    left = pack_installed(p)
    if left:
        ids = " ".join(left)
        raise PackError((_("Uninstall its tweaks first: {ids} ({command}).") if p["state"] == "trusted" else
                         _("Its tweaks {ids} are still installed: trust it again to uninstall them ({command}), "
                           "then remove it.")).format(ids=ids, command=f"./install.sh uninstall {ids}"))
    shutil.rmtree(d)
    registry.set_trusted(d, False)
    registry.load(refresh=True)


def check_folder(d):
    """(lines, bad): mods check of a pack, or of a single tweak folder."""
    single = (d / "README.md").is_file() and not (d / "pack.md").is_file() and not any(
        (p / "README.md").is_file() for p in d.iterdir() if p.is_dir() and not p.name.startswith("."))
    if single:                                     # (a pack's own README.md beside its tweaks: still a pack)
        folders, probs = [d], []
    else:                                          # (a pack: its pack.md is checked too)
        info, folders, probs = registry.read_pack(d)
        if not isinstance(info["api"], int) or info["api"] > registry.API:
            probs.append(f"{d.name}: needs a newer Frame Tweaks (pack api {info['api']}; this one knows {registry.API})")
    lines, bad = list(probs), len(probs)
    for f in folders:
        c, probs = registry.read_tweak(f)
        lines += probs
        bad += c is None
        lines.append(f"{'ok ' if c else 'BAD'} {f.name}")
    return lines, bad


def find_pack(name):
    """A pack by its folder, or by its name or folder name if only one pack goes by it (any pack
    can call itself anything: trusting the wrong one by its name mustn't be possible)."""
    packs = registry.load()["packs"]
    found = [p for p in packs if Path(name).expanduser().resolve() == p["dir"]] or [
        p for p in packs if name in (p["name"], p["label"], p["dir"].name, str(p["dir"]))]
    if len(found) > 1:
        sys.exit(_("more than one pack is called {name}: give its folder ({folders})").format(
            name=repr(name), folders=", ".join(str(p["dir"]) for p in found)))
    if found:
        return found[0]
    sys.exit(_("no pack {name}; see {command}").format(name=repr(name), command="./install.sh mods"))


def mods(args, usage):
    """The `mods` command; usage: what anything else it's given prints (lib/sft.py's, which
    ./install.sh mods shows)."""
    if args[:1] in (["on"], ["off"]) and len(args) == 2:
        p = find_pack(args[1])
        if p["state"] not in ("official", "off"):
            sys.exit(_("{pack} isn't one of Frame Tweaks' own packs: {command}").format(
                pack=p["name"], command="./install.sh mods trust|untrust NAME"))
        registry.set_official(p["dir"], args[0] == "on")
        print(f"{p['name']}: " + (_("in use; its tweaks are listed") if args[0] == "on" else
                                  _("turned off (installed tweaks of it stay until you uninstall them)")))
        return
    if args[:1] in (["trust"], ["untrust"]) and len(args) == 2:
        p = find_pack(args[1])
        if p["state"] in ("official", "off"):
            sys.exit(_("{pack} comes with Frame Tweaks, so it needs no trust: {command}").format(
                pack=p["name"], command="./install.sh mods on|off NAME"))
        registry.set_trusted(p["dir"], args[0] == "trust")
        print(f"{p['name']}: " + (_("trusted; its tweaks are listed now") if args[0] == "trust" else
                                  _("no longer used (installed tweaks of it stay until you uninstall them)")))
        return
    if args[:1] == ["check"] and len(args) == 2:
        lines, bad = check_folder(Path(args[1]).expanduser().resolve())
        print("\n".join(lines))
        sys.exit(1 if bad else 0)
    if args[:1] == ["add"] and len(args) in (2, 3):
        try:
            d = add_pack(args[1], args[2] if len(args) == 3 else None)
        except PackError as e:
            sys.exit(str(e))
        p = next(x for x in registry.load()["packs"] if x["dir"] == d.resolve())
        print(_("Added the pack {name} in {folder}.").format(name=plain(p["name"]), folder=d)
              + (" " + _("By {author}.").format(author=plain(p["author"])) if p["author"] else ""))
        print(_("Tweaks: %s") % (", ".join(p["tweaks"]) or _("none")))
        lines, bad = check_folder(d)
        if bad:
            print(_("Problems:") + "\n  " + "\n  ".join(plain(x) for x in lines if not x.startswith("ok ")))
        print(_("It isn't used until you trust it: its tweaks would run as you. Read what they do first (each "
                "one's README.md in that folder), then: {command}").format(command=f'./install.sh mods trust "{d}"'))
        return
    if args == ["updates"]:
        found = 0
        for p in registry.load()["packs"]:
            if not removable(p):
                continue
            if p["state"] != "trusted":         # (git runs in its folder: only in a pack you've trusted)
                if (p["dir"] / ".git").is_dir():
                    found += 1
                    print(f"{plain(p['name'])}: " + _("not checked: not trusted ({command})").format(
                        command=f'./install.sh mods trust "{p["dir"]}"'))
                continue
            if not pack_origin(p["dir"]):
                continue
            found += 1
            news = pack_has_update(p["dir"])
            print(f"{plain(p['name'])}: " + {True: _("a newer version is out: {command}").format(
                command=f'./install.sh mods update "{p["dir"]}"'), False: _("up to date"),
                None: _("couldn't check (no connection?)")}[news])
        if not found:
            print(_("No packs added from a link."))
        return
    if args[:1] in (["update"], ["remove"]) and len(args) == 2:
        p = find_pack(args[1])
        try:
            if args[0] == "remove":
                remove_pack(p["dir"])
                print(_("Removed the pack {name} ({folder}).").format(name=plain(p["name"]), folder=p["dir"]))
                return
            got = update_pack(p["dir"])
        except PackError as e:
            sys.exit(str(e))
        if not got["files"]:
            print(_("{name} is up to date.").format(name=plain(p["name"])))
            return
        print(ngettext("{name}: updated, {n} file changed.", "{name}: updated, {n} files changed.",
                       len(got["files"])).format(name=plain(p["name"]), n=len(got["files"])))
        for line in got["log"]:
            print(f"  {line}")
        print(_("It isn't used until you trust it again. Read what changed first, then: {command}").format(
            command=f'./install.sh mods trust "{p["dir"]}"'))
        return
    if args:
        sys.exit(usage)
    data = registry.load()
    used = {c["id"]: c for c in data["components"]}
    for p in data["packs"]:
        state = {"official": _("official: in use"),
                 "off": _("official: turned off ({command})").format(command="./install.sh mods on NAME"),
                 "trusted": _("trusted: in use"),
                 "untrusted": _("not trusted: not used ({command})").format(command="./install.sh mods trust NAME"),
                 "changed": _("changed since you trusted it: not used until you trust it again")}[p["state"]]
        # (a pack's own text, plain: an untrusted one's name could otherwise hold terminal escapes)
        name = plain(p["name"]) if p["label"] == p["name"] else f"{plain(p['label'])} [{plain(p['name'])}]"
        print(f"{name}  ({plain(str(p['dir']))})  {state}")
        if p["about"]:
            print(f"    {plain(p['about'])}")
        if p["state"] not in ("official", "off"):
            for t in p["tweaks"]:
                c = used.get(t)
                note = "" if not c or c["pack_dir"] != p["dir"] else (
                    "  " + _("(instead of {other}'s)").format(other=c["replaced"]) if c["replaced"] else "")
                print(f"    {plain(t)}{note}")
    for pr in data["problems"]:
        print(_("problem: %s") % plain(pr))
