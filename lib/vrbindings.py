#!/usr/bin/env python3
"""SteamVR controller bindings, changed for a tweak and put back on its uninstall (experimental).

SteamVR serves its binding editor's API on 127.0.0.1:27062 while it runs. Through it this reads
the binding an app uses for a controller (by default the dashboard's, for the Frame's
controllers), writes a copy with a tweak's small edits under ~/.local/share/frame-tweaks/bindings/,
selects that copy, and remembers what it replaced in ~/.local/state/frame-tweaks/vrbindings.json.
The API is undocumented: SteamVR updates may change it, and SteamVR may keep acting on the old
binding until it restarts. Steam's own files are never edited. Format and use: docs/mods.md,
"Changing a SteamVR controller binding".

Patches have names, so several tweaks can each have one. Patches of the same app and controller
stack: the copy holds every patch's edits, in the order they were made, on the binding they
replaced; restoring one rebuilds the copy from the others (or selects the original again when
it was the last). A patch is put back only while SteamVR still uses Frame Tweaks' copy as it was
written: if someone chose another binding since, that choice stays and the record is dropped.

  vrbindings.py show [--controller C] [--app KEY] [--json]   the binding in use, per action set
  vrbindings.py patch NAME EDIT-FILE                         apply a patch (EDIT-FILE: JSON)
  vrbindings.py restore NAME                                 undo it
  vrbindings.py status                                       Frame Tweaks' patches, and whether active

Exit 0: done (also: nothing to change, no such patch), 1: failed, nothing changed (SteamVR not
running, say), 2: wrong arguments or edit file.
"""
import contextlib
import fcntl
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from i18n import _  # noqa: E402
except ImportError:                       # (copied somewhere without i18n.py: English)
    def _(text):
        return text

APP = "openvr.component.vrcompositor"     # the dashboard and the system button's actions
CONTROLLER = "frame_controller"
# (FRAME_TWEAKS_VRINPUT_URL: another server, for the tests' stand-in)
BASE = os.environ.get("FRAME_TWEAKS_VRINPUT_URL") or "http://127.0.0.1:27062"
NAME_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
OPS = ("remove", "set")
EDIT_KEYS = {"remove": {"op", "action_set", "path", "input", "output"},
             "set": {"op", "action_set", "path", "input", "output", "mode"}}
FILE_KEYS = {"app", "controller", "edits", "description"}


class BindingsError(Exception):
    """A failure; nothing was changed."""


class NotRunning(BindingsError):
    pass


def data_dir():
    return Path.home() / ".local/share/frame-tweaks/bindings"


def state_file():
    return Path.home() / ".local/state/frame-tweaks/vrbindings.json"


def digest(config):
    """A binding's identity: its JSON, keys sorted (SteamVR's own output isn't key-stable)."""
    return hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def same_url(a, b):
    """SteamVR may hand back a file URL quoted differently than it was given."""
    return bool(a and b) and urllib.parse.unquote(a) == urllib.parse.unquote(b)


def _truthy(v):
    # (SteamVR answers "success": "True" (a string) on a load that worked, false (a bool) on one
    # that didn't: seen on a Frame, SteamVR 2.x, 2026-11)
    return v is True or (isinstance(v, str) and v.lower() == "true")


# ---- SteamVR's binding API -------------------------------------------------------------------
class SteamVR:
    """SteamVR's binding editor's API. Every request carries SteamVR's own page as its Origin:
    without one, or with another site's, SteamVR answers 401 (checked on a Frame), which is also
    what stops a web page in the browser from changing bindings."""

    def __init__(self, base=None, timeout=3):
        self.base = (base or BASE).rstrip("/")
        self.timeout = timeout

    def _call(self, path, params=None, body=None):
        url = self.base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers={"Origin": self.base})
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            e.close()
            raise BindingsError(_("SteamVR refused {what} (HTTP {code})").format(what=path, code=e.code)) from e
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            raise NotRunning(_("SteamVR isn't running (nothing answers on {url}); nothing was changed.")
                             .format(url=self.base)) from e
        except ValueError as e:
            raise BindingsError(_("SteamVR's answer to {what} isn't JSON").format(what=path)) from e

    def current_url(self, app, controller):
        got = self._call("/input/getactions.json", {"app_key": app})
        url = (got.get("current_binding_url") or {}).get(controller) if isinstance(got, dict) else None
        if not url:
            raise BindingsError(_("SteamVR has no binding of {app} for {controller}")
                                .format(app=app, controller=controller))
        return url

    def load(self, url, app, controller):
        got = self._call("/input/loadbindingfromurl.json",
                         {"binding_url": url, "controller_type": controller, "app_key": app})
        config = got.get("binding_config") if isinstance(got, dict) else None
        if not isinstance(config, dict) or not _truthy(got.get("success", True)):
            raise BindingsError(_("SteamVR couldn't load the binding {url}").format(url=url))
        return config

    def select(self, url, app, controller):
        got = self._call("/input/selectconfig.action",
                         body={"app_key": app, "controller_type": controller, "url": url})
        if not (isinstance(got, dict) and _truthy(got.get("success"))):
            raise BindingsError(_("SteamVR didn't select the binding {url}").format(url=url))


# ---- the edit file ---------------------------------------------------------------------------
def parse_edit(data):
    """The edit file's JSON (already parsed) as {app, controller, edits}; ValueError if it
    isn't one. Strict: an unknown key is more likely a typo than something to ignore."""
    if not isinstance(data, dict):
        raise ValueError(_("the edit file must be a JSON object"))
    unknown = set(data) - FILE_KEYS
    if unknown:
        raise ValueError(_("unknown key in the edit file: {keys}").format(keys=", ".join(sorted(map(str, unknown)))))
    app, controller = data.get("app", APP), data.get("controller", CONTROLLER)
    for k, v in (("app", app), ("controller", controller)):
        if not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", v):
            raise ValueError(_("\"{key}\" must be a name such as {example}")
                             .format(key=k, example=APP if k == "app" else CONTROLLER))
    edits = data.get("edits")
    if not isinstance(edits, list) or not edits:
        raise ValueError(_("\"edits\" must be a list of at least one edit"))
    out = []
    for i, e in enumerate(edits, 1):
        if not isinstance(e, dict) or e.get("op") not in OPS:
            raise ValueError(_("edit {n}: \"op\" must be one of: {ops}").format(n=i, ops=", ".join(OPS)))
        unknown = set(e) - EDIT_KEYS[e["op"]]
        if unknown:
            raise ValueError(_("edit {n}: unknown key: {keys}").format(n=i, keys=", ".join(sorted(map(str, unknown)))))
        for k in ("action_set", "path", "input") + (("output",) if e["op"] == "set" else ()):
            if not isinstance(e.get(k), str) or not e[k]:
                raise ValueError(_("edit {n}: \"{key}\" must be a text").format(n=i, key=k))
        for k in ("output", "mode"):
            if k in e and (not isinstance(e[k], str) or not e[k]):
                raise ValueError(_("edit {n}: \"{key}\" must be a text").format(n=i, key=k))
        if not e["action_set"].startswith("/actions/") or not e["path"].startswith("/user/"):
            raise ValueError(_("edit {n}: \"action_set\" starts /actions/, \"path\" /user/").format(n=i))
        out.append(dict(e))
    return {"app": app, "controller": controller, "edits": out}


def read_edit(path):
    try:
        data = json.loads(Path(path).read_text())
    except OSError as e:
        raise ValueError(_("can't read {file}: {why}").format(file=path, why=e.strerror)) from e
    except ValueError as e:
        raise ValueError(_("{file} isn't JSON: {why}").format(file=path, why=e)) from e
    return parse_edit(data)


def apply_edits(config, edits):
    """A copy of the binding config with the edits made; config itself is left as it is.
    remove: drop that input (click, long, held...) of the sources with that path in that action
    set (only where it outputs "output", if given); a source left with no inputs goes too.
    set: make that input output "output" on the first source with that path (and "mode", if
    given), adding a source (which then needs "mode") when there's none."""
    result = json.loads(json.dumps(config))
    bindings = result.setdefault("bindings", {})
    for e in edits:
        aset = bindings.setdefault(e["action_set"], {}) if e["op"] == "set" else bindings.get(e["action_set"])
        if not isinstance(aset, dict):
            continue
        sources = aset.get("sources")
        if not isinstance(sources, list):
            if e["op"] == "remove":
                continue
            sources = aset["sources"] = []
        if e["op"] == "remove":
            kept = []
            for s in sources:
                inputs = s.get("inputs") if isinstance(s, dict) else None
                if (isinstance(inputs, dict) and s.get("path") == e["path"] and e["input"] in inputs
                        and ("output" not in e or (inputs[e["input"]] or {}).get("output") == e["output"])):
                    inputs = {k: v for k, v in inputs.items() if k != e["input"]}
                    if not inputs:
                        continue
                    s = dict(s, inputs=inputs)
                kept.append(s)
            aset["sources"] = kept
        else:
            match = next((s for s in sources if isinstance(s, dict) and s.get("path") == e["path"]
                          and ("mode" not in e or s.get("mode") == e["mode"])), None)
            if match is None:
                if "mode" not in e:
                    raise ValueError(_("{path} has no source in {set}: say its \"mode\" (button, joystick...) to add one")
                                     .format(path=e["path"], set=e["action_set"]))
                match = {"path": e["path"], "mode": e["mode"], "inputs": {}}
                sources.append(match)
            if not isinstance(match.get("inputs"), dict):
                match["inputs"] = {}
            match["inputs"][e["input"]] = {"output": e["output"]}
    return result


def summary(config):
    """The binding in a few lines: per action set, each input source's inputs and what they do."""
    lines = []
    for name, aset in sorted((config.get("bindings") or {}).items()):
        if not isinstance(aset, dict):
            continue
        rows = []
        for s in aset.get("sources") or []:
            inputs = s.get("inputs") if isinstance(s, dict) else None
            if not isinstance(inputs, dict) or not inputs:
                continue
            what = ", ".join(f"{k} → {str((v or {}).get('output', '')).rsplit('/', 1)[-1]}"
                             for k, v in inputs.items() if isinstance(v, dict))
            rows.append(f"    {s.get('path')} ({s.get('mode')}): {what}")
        for c in aset.get("chords") or []:
            if isinstance(c, dict):
                keys = " + ".join(f"{p} {how}" for p, how in (c.get("inputs") or []) if isinstance(p, str))
                rows.append(f"    chord {keys} → {str(c.get('output', '')).rsplit('/', 1)[-1]}")
        if rows:
            lines.append(f"  {name}")
            lines.extend(rows)
    return lines


# ---- Frame Tweaks' record --------------------------------------------------------------------
def read_state():
    try:
        data = json.loads(state_file().read_text())
    except (OSError, ValueError):
        return {"slots": {}}
    return data if isinstance(data, dict) and isinstance(data.get("slots"), dict) else {"slots": {}}


def write_state(state):
    f = state_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".new")
    tmp.write_text(json.dumps(state, indent=1) + "\n")
    os.replace(tmp, f)


@contextlib.contextmanager
def locked():
    """One patch or restore at a time (two tweaks installing at once would each rebuild the copy
    from a record the other is changing)."""
    f = state_file().with_suffix(".lock")
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "w") as fd:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield


def slot_key(app, controller):
    return f"{app}|{controller}"


def find(state, name):
    for key, slot in state["slots"].items():
        if name in slot.get("patches", {}):
            return key, slot
    return None, None


def is_ours(active, slot):
    """Is SteamVR still on Frame Tweaks' copy, unchanged since it was written?"""
    f = Path(slot.get("file", ""))
    if not same_url(active, f.as_uri() if f.is_absolute() else ""):
        return False
    try:
        return digest(json.loads(f.read_text())) == slot.get("written_hash")
    except (OSError, ValueError):
        return False


def _write_copy(app, controller, config):
    """The patched copy, in a file of its own per content: the one SteamVR has selected is never
    written over (if selecting the new one fails, SteamVR keeps a file that's still whole)."""
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    h = digest(config)
    f = d / f"{re.sub(r'[^A-Za-z0-9._-]', '_', app)}__{controller}-{h[:12]}.json"
    tmp = f.with_name(f.name + ".new")
    tmp.write_text(json.dumps(config, indent=2) + "\n")
    os.replace(tmp, f)
    return f, h


def _remove(path):
    with contextlib.suppress(OSError):
        Path(path).unlink()


def _named(config, names):
    """The copy says it's Frame Tweaks' in SteamVR's binding list, and for which patches."""
    base = str(config.get("name") or "")
    config["name"] = (base + " " if base else "") + "(Frame Tweaks: " + ", ".join(names) + ")"
    return config


def _original(api, slot):
    """The binding the patches replaced, loaded again each time: a SteamVR update's changes to it
    come through into the rebuilt copy."""
    return api.load(slot["original_url"], slot["app"], slot["controller"])


def _with(config, patches):
    """config with every patch's edits made, in the order they were made."""
    for edits in patches.values():
        config = apply_edits(config, edits)
    return config


# ---- the commands ----------------------------------------------------------------------------
def show(app=APP, controller=CONTROLLER, api=None):
    """(the URL SteamVR uses, its binding config)."""
    api = api or SteamVR()
    url = api.current_url(app, controller)
    return url, api.load(url, app, controller)


def patch(name, edit, api=None):
    """Applies edit (parse_edit's result) as patch name. Returns a message; BindingsError if it
    couldn't (then nothing changed)."""
    if not NAME_RE.fullmatch(name or ""):
        raise ValueError(_("a patch's name is lowercase letters, digits, '.', '_' and '-' (e.g. the tweak's id)"))
    api = api or SteamVR()
    app, controller = edit["app"], edit["controller"]
    with locked():
        state = read_state()
        key = slot_key(app, controller)
        other_key, _other = find(state, name)
        if other_key and other_key != key:
            raise BindingsError(_("A patch named {name} already changes another binding ({key}); restore it first.")
                                .format(name=name, key=other_key))
        active = api.current_url(app, controller)
        slot = state["slots"].get(key)
        if slot and not is_ours(active, slot):
            raise BindingsError(_("The binding changed since Frame Tweaks patched it (for: {names}). "
                                  "Restore those patches first: that keeps the binding chosen since.")
                                .format(names=", ".join(slot["patches"])))
        if not slot:
            if urllib.parse.unquote(active).startswith(urllib.parse.unquote(data_dir().as_uri()) + "/"):
                raise BindingsError(_("SteamVR uses a copy Frame Tweaks has no record of ({url}): choose "
                                      "another binding in SteamVR's controller settings first.").format(url=active))
            slot = {"app": app, "controller": controller, "original_url": active, "patches": {}}
        patches = dict(slot["patches"])
        if patches.get(name) == edit["edits"]:
            return _("{name}: already active").format(name=name)
        original = _original(api, slot)
        before = _with(original, {k: v for k, v in patches.items() if k != name})
        patches[name] = edit["edits"]
        config = _with(original, patches)
        if config == before:
            return _("{name}: the binding already reads that way; nothing to change").format(name=name)
        old_file = slot.get("file")
        f, h = _write_copy(app, controller, _named(config, list(patches)))
        try:
            api.select(f.as_uri(), app, controller)
        except BindingsError:
            if str(f) != old_file:
                _remove(f)
            raise
        if old_file and old_file != str(f):
            _remove(old_file)
        slot.update(file=str(f), written_hash=h, patches=patches)
        slot.setdefault("original_hash", digest(original))
        state["slots"][key] = slot
        write_state(state)
    return _("{name}: patched (SteamVR may need a restart before it acts on it)").format(name=name)


def restore(name, api=None):
    """Undoes patch name. Returns a message; BindingsError if SteamVR couldn't be asked (the
    record is kept, so running it again later works)."""
    api = api or SteamVR()
    with locked():
        state = read_state()
        key, slot = find(state, name)
        if not slot:
            return _("{name}: no such patch; nothing to restore").format(name=name)
        app, controller = slot["app"], slot["controller"]
        active = api.current_url(app, controller)
        patches = {k: v for k, v in slot["patches"].items() if k != name}
        if not is_ours(active, slot):
            msg = _("{name}: the binding was changed since Frame Tweaks patched it; left as it is").format(name=name)
            if patches:
                slot["patches"] = patches
            else:
                del state["slots"][key]
                if not same_url(active, Path(slot["file"]).as_uri()):
                    _remove(slot["file"])         # (SteamVR doesn't use it: safe to delete)
            write_state(state)
            return msg
        if not patches:
            api.select(slot["original_url"], app, controller)
            _remove(slot["file"])
            del state["slots"][key]
        else:
            config = _with(_original(api, slot), patches)
            f, h = _write_copy(app, controller, _named(config, list(patches)))
            try:
                api.select(f.as_uri(), app, controller)
            except BindingsError:
                if str(f) != slot["file"]:
                    _remove(f)
                raise
            if str(f) != slot["file"]:
                _remove(slot["file"])
            slot.update(file=str(f), written_hash=h, patches=patches)
        write_state(state)
    return _("{name}: restored (SteamVR may need a restart before it acts on it)").format(name=name)


def status(api=None):
    """[(name, app, controller, active)] for each patch; active is None when SteamVR isn't
    running (it can't be asked which binding it uses)."""
    api = api or SteamVR()
    out = []
    for slot in read_state()["slots"].values():
        try:
            active = is_ours(api.current_url(slot["app"], slot["controller"]), slot)
        except NotRunning:
            active = None
        except BindingsError:
            active = False
        out.extend((n, slot["app"], slot["controller"], active) for n in slot.get("patches", {}))
    return out


# ---- the command line ------------------------------------------------------------------------
def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__, file=sys.stdout if argv else sys.stderr)
        return 0 if argv else 2
    cmd, args = argv[0], argv[1:]
    try:
        if cmd == "show":
            opts = {"--app": APP, "--controller": CONTROLLER}
            as_json = "--json" in args
            args = [a for a in args if a != "--json"]
            while args:
                if len(args) < 2 or args[0] not in opts:
                    raise ValueError(_("show [--controller C] [--app KEY] [--json]"))
                opts[args[0]], args = args[1], args[2:]
            url, config = show(opts["--app"], opts["--controller"])
            if as_json:
                print(json.dumps(config, indent=2))
            else:
                print(url)
                print("\n".join(summary(config)))
        elif cmd == "patch":
            if len(args) != 2:
                raise ValueError(_("patch NAME EDIT-FILE"))
            print(patch(args[0], read_edit(args[1])))
        elif cmd == "restore":
            if len(args) != 1:
                raise ValueError(_("restore NAME"))
            print(restore(args[0]))
        elif cmd == "status":
            rows = status()
            if not rows:
                print(_("No SteamVR binding patches."))
            for name, app, controller, active in rows:
                state = {True: _("active"), False: _("not active (the binding was changed since)"),
                         None: _("SteamVR not running")}[active]
                print(f"{name}: {app} / {controller}: {state}")
        else:
            raise ValueError(_("unknown command: {cmd}").format(cmd=cmd))
    except ValueError as e:
        print(f"vrbindings: {e}", file=sys.stderr)
        return 2
    except BindingsError as e:
        print(f"vrbindings: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
