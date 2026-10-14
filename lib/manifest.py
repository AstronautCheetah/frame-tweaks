#!/usr/bin/env python3
"""Tweak and pack manifests: the YAML front matter of each tweak's README.md and each pack's
pack.md, read without any dependency (SteamOS's Python may lack PyYAML, Homebrew's does).

The YAML is a strict subset, so a file means the same to this reader, to PyYAML and to a
person reading it (tests/test_manifest.py checks every manifest against PyYAML):

  key: value              keys are letters, digits, _ and -
  key:                    a nested mapping or list, indented by spaces below it
    - item                list items: values or mappings ("- key: value" with more keys below)
  key: [a, b]             flow lists and mappings, nesting allowed: {label: Right, value: right}
  key: >-                 folded text (lines joined with spaces; a blank line is a line break)
  key: |                  literal text (line breaks kept); "-" after either drops the last one
  "text", 'text'          quoted strings ("..." knows \\" \\\\ \\n \\t; '...' doubles '')
  42, -3, 2.5             numbers;  true, false;  null or ~
  # comment               on its own line, or after a value (space before #)

Refused, with the line number, instead of being guessed at: tabs, anchors and aliases (& *),
tags (!), duplicate keys, a value continuing on the next line without > or |, and plain
values YAML 1.1 readers turn into something else (yes/no/on/off, dates, 010, 1_000, .5):
quote those. Plain text can't start with one of  [ ] { } , & * ! | > ' " % @ `  or "- ".
"""
import re

INDICATORS = set("[]{},&*!|>'\"%@`")
AMBIGUOUS = re.compile(r"(?i)^(y|n|yes|no|on|off|true|false|null|~|\.inf|-\.inf|\.nan)$")
INT = re.compile(r"^-?(0|[1-9][0-9]*)$")
FLOAT = re.compile(r"^-?(0|[1-9][0-9]*)\.[0-9]+$")
KEY = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_-]*):(?: (.*))?$")


class ManifestError(ValueError):
    def __init__(self, msg, line=None):
        super().__init__(f"line {line}: {msg}" if line else msg)
        self.line = line


def scalar(text, line):
    """A plain (unquoted) value."""
    t = text.strip()
    if t in ("null", "~"):
        return None
    if t in ("true", "false"):
        return t == "true"
    if INT.match(t):
        return int(t)
    if FLOAT.match(t):
        return float(t)
    if AMBIGUOUS.match(t):
        raise ManifestError(f"{t!r} means different things to different YAML readers: quote it", line)
    if t[:1] in INDICATORS or t.startswith("- ") or t == "-":
        raise ManifestError(f"a plain value can't start with {t[:1]!r}: quote it", line)
    if re.match(r"[-+]?\.?[0-9]", t):
        raise ManifestError(f"{t!r} looks like a number or date but isn't a simple one: quote it", line)
    if ": " in t or t.endswith(":") or " #" in t:
        raise ManifestError(f"{t!r} contains ': ' or ' #': quote it", line)
    return t


def strip_comment(text):
    """The value part of a line, without a trailing comment (quotes respected)."""
    quote, i = None, 0
    while i < len(text):
        ch = text[i]
        if quote == '"' and ch == "\\":
            i += 2                                     # an escaped character
            continue
        if quote:
            if ch == quote:
                if quote == "'" and text[i + 1:i + 2] == "'":
                    i += 2                             # '' inside '...'
                    continue
                quote = None
        elif ch in "\"'" and (i == 0 or text[i - 1] in " [{,:"):
            quote = ch
        elif ch == "#" and (i == 0 or text[i - 1] == " "):
            return text[:i].rstrip()
        i += 1
    return text.rstrip()


class Flow:
    """[...] and {...}, and quoted strings, on one line."""

    def __init__(self, text, line):
        self.s, self.i, self.line = text, 0, line

    def err(self, msg):
        raise ManifestError(msg, self.line)

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] == " ":
            self.i += 1

    def value(self, inside=False):
        self.ws()
        c = self.s[self.i:self.i + 1]
        if c == "[":
            self.i += 1
            out = []
            self.ws()
            if self.s[self.i:self.i + 1] == "]":
                self.i += 1
                return out
            while True:
                out.append(self.value(True))
                self.ws()
                c = self.s[self.i:self.i + 1]
                self.i += 1
                if c == "]":
                    return out
                if c != ",":
                    self.err("expected , or ] in a [...] list")
        if c == "{":
            self.i += 1
            out = {}
            self.ws()
            if self.s[self.i:self.i + 1] == "}":
                self.i += 1
                return out
            while True:
                self.ws()
                m = re.compile(r"([A-Za-z0-9_][A-Za-z0-9_-]*): ").match(self.s, self.i)
                if not m:
                    self.err("expected key: value in a {...} mapping")
                if m[1] in out:
                    self.err(f"duplicate key {m[1]!r}")
                self.i = m.end()
                out[m[1]] = self.value(True)
                self.ws()
                c = self.s[self.i:self.i + 1]
                self.i += 1
                if c == "}":
                    return out
                if c != ",":
                    self.err("expected , or } in a {...} mapping")
        if c == '"':
            j, out = self.i + 1, []
            while j < len(self.s):
                ch = self.s[j]
                if ch == "\\":
                    nxt = self.s[j + 1:j + 2]
                    if nxt not in ('"', "\\", "n", "t", "/"):
                        self.err(f"unsupported escape \\{nxt}")
                    out.append({"n": "\n", "t": "\t"}.get(nxt, nxt))
                    j += 2
                    continue
                if ch == '"':
                    self.i = j + 1
                    return "".join(out)
                out.append(ch)
                j += 1
            self.err("unterminated \"...\"")
        if c == "'":
            j, out = self.i + 1, []
            while j < len(self.s):
                if self.s[j] == "'":
                    if self.s[j + 1:j + 2] == "'":
                        out.append("'")
                        j += 2
                        continue
                    self.i = j + 1
                    return "".join(out)
                out.append(self.s[j])
                j += 1
            self.err("unterminated '...'")
        # plain: up to the next , ] } inside a flow collection, else to the end
        j = self.i
        while j < len(self.s) and not (inside and self.s[j] in ",]}"):
            j += 1
        raw = self.s[self.i:j]
        self.i = j
        if inside and (raw.strip()[:1] in INDICATORS):
            self.err(f"{raw.strip()!r}: quote it")
        return scalar(raw, self.line)

    def whole(self):
        v = self.value()
        self.ws()
        if self.i != len(self.s):
            self.err(f"unexpected {self.s[self.i:]!r} after the value")
        return v


def parse_yaml(text):
    lines = text.split("\n")
    for n, raw in enumerate(lines, 1):
        if "\t" in raw[:len(raw) - len(raw.lstrip(" \t"))]:
            raise ManifestError("tab in the indentation: use spaces", n)
    p = _Parser(lines)
    p.skip()
    if p.i >= len(lines):
        return {}
    v = p.block(p.indent())
    p.skip()
    if p.i < len(lines):
        raise ManifestError("unexpected text (wrong indentation?)", p.i + 1)
    return v


class _Parser:
    def __init__(self, lines):
        self.lines, self.i = lines, 0

    def skip(self):
        while self.i < len(self.lines) and (not self.lines[self.i].strip() or self.lines[self.i].lstrip().startswith("#")):
            self.i += 1

    def indent(self):
        line = self.lines[self.i]
        return len(line) - len(line.lstrip(" "))

    def block(self, ind):
        """A mapping or list whose lines start at indentation ind."""
        self.skip()
        if self.lines[self.i].strip().startswith("- ") or self.lines[self.i].strip() == "-":
            return self.seq(ind)
        return self.mapping(ind)

    def mapping(self, ind, first=None):
        out = {}
        while True:
            self.skip()
            if self.i >= len(self.lines) and first is None:
                return out
            if first is not None:
                text, n = first
                first = None
            else:
                if self.indent() != ind:
                    if self.indent() > ind:
                        raise ManifestError("unexpected indentation", self.i + 1)
                    return out
                n = self.i + 1
                text = self.lines[self.i].strip()
                if text.startswith("- "):
                    return out
                self.i += 1
            m = KEY.match(strip_comment(text) if not text.rstrip().endswith((">", ">-", "|", "|-")) else text.rstrip())
            if not m:
                raise ManifestError(f"expected key: value, got {text!r}", n)
            key, rest = m[1], m[2]
            if key in out:
                raise ManifestError(f"duplicate key {key!r}", n)
            out[key] = self.value(rest, ind, n)

    def seq(self, ind):
        out = []
        while True:
            self.skip()
            if self.i >= len(self.lines) or self.indent() != ind or not (
                    self.lines[self.i].strip().startswith("- ") or self.lines[self.i].strip() == "-"):
                if self.i < len(self.lines) and self.indent() > ind:
                    raise ManifestError("unexpected indentation", self.i + 1)
                return out
            n = self.i + 1
            item = self.lines[self.i].strip()[2:]
            self.i += 1
            if not item.strip():
                self.skip()
                out.append(self.block(self.indent()) if self.i < len(self.lines) and self.indent() > ind else None)
            elif item.startswith("- ") or item == "-":       # "- - x": a list in a list
                self.i -= 1
                self.lines[self.i] = " " * (ind + 2) + item
                out.append(self.seq(ind + 2))
            elif KEY.match(strip_comment(item)) and not item.startswith(("'", '"', "{", "[")):
                out.append(self.mapping(ind + 2, first=(item, n)))   # "- key: v" and keys below it
            else:
                out.append(self.value(item, ind, n))

    def value(self, rest, ind, n):
        rest = (rest or "").strip()
        if rest.startswith(("&", "*", "!")):
            raise ManifestError("anchors, aliases and tags aren't supported", n)
        if rest in (">", ">-", "|", "|-"):
            return self.text(rest, ind, n)
        rest = strip_comment(rest)
        if not rest:                                   # nested block below, or null
            self.skip()
            if self.i < len(self.lines) and self.indent() > ind:
                return self.block(self.indent())
            if self.i < len(self.lines) and self.indent() == ind and self.lines[self.i].strip().startswith("- "):
                return self.seq(ind)                   # (a list may sit at its key's indentation)
            return None
        v = Flow(rest, n).whole()
        self.skip()
        if self.i < len(self.lines) and self.indent() > ind:
            raise ManifestError("a value can't continue on the next line: use >- (or quotes on one line)", self.i + 1)
        return v

    def text(self, style, ind, n):
        body = []
        start = None
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if line.strip():
                cur = len(line) - len(line.lstrip(" "))
                if start is None:
                    if cur <= ind:
                        break
                    start = cur
                elif cur < start:
                    break
                body.append(line[start:])
            else:
                body.append("")
            self.i += 1
        while body and body[-1] == "":
            body.pop()
        if not body:
            raise ManifestError("empty text block", n)
        if style[0] == "|":
            out = "\n".join(body)
        else:
            if any(b.startswith(" ") for b in body):
                raise ManifestError("folded text (>) with more-indented lines: use | instead", n)
            out, para = [], []
            for b in body:
                if b:
                    para.append(b)
                else:
                    out.append(" ".join(para))
                    para = []
            out.append(" ".join(para))
            out = "\n".join(out)
        return out if style.endswith("-") else out + "\n"


def front_matter(text):
    """(data, body) of a Markdown file starting with a --- front matter block."""
    if not text.startswith("---\n"):
        raise ManifestError("no front matter: the file must start with a line ---")
    end = text.find("\n---\n", 3)
    if end < 0:
        raise ManifestError("front matter isn't closed by a line ---")
    data = parse_yaml(text[4:end + 1])
    if not isinstance(data, dict):
        raise ManifestError("front matter must be key: value lines")
    return data, text[end + 5:]


# ---- writing (for tools that create or update manifests) -----------------------------------
def dump_value(v, ind=0, width=96):
    """YAML for v as this reader (and PyYAML) read it back; long text is folded (>-)."""
    pad = " " * ind
    if isinstance(v, dict) and v and all(not isinstance(x, (dict, list)) for x in v.values()):
        flow = _inline(v)                              # a small mapping stays on one line
        if len(flow) <= 64 and "\n" not in flow:
            return flow
    if isinstance(v, dict):
        if not v:
            return "{}"
        out = []
        for k, x in v.items():
            s = dump_value(x, ind + 2, width)
            if isinstance(x, (dict, list)) and x and not s.startswith(("[", "{")):
                out.append(f"{pad}{k}:\n{s}")
            elif s.startswith((">-\n", "|\n", "|-\n")):
                out.append(f"{pad}{k}: {s}")
            else:
                out.append(f"{pad}{k}: {s}")
        return "\n".join(out)
    if isinstance(v, list):
        if not v:
            return "[]"
        if all(not isinstance(x, (dict, list)) for x in v):
            flow = "[" + ", ".join(_inline(x) for x in v) + "]"
            if len(flow) + ind < width and "\n" not in flow:
                return flow
        out = []
        for x in v:
            if isinstance(x, dict) and x and dump_value(x, ind + 2, width).startswith("{"):
                out.append(f"{pad}- {dump_value(x, ind + 2, width)}")
            elif isinstance(x, dict) and x:
                inner = dump_value(x, ind + 2, width).split("\n", 1)
                out.append(f"{pad}- {inner[0].lstrip()}" + (f"\n{inner[1]}" if len(inner) > 1 else ""))
            else:
                out.append(f"{pad}- {dump_value(x, ind + 2, width)}")
        return "\n".join(out)
    if isinstance(v, str) and (len(v) + ind > width - 20 or "\n" in v):
        if "\n" in v or v != v.strip() or "  " in v:
            body = v.rstrip("\n")
            return ("|\n" if v.endswith("\n") else "|-\n") + "\n".join((pad + l) if l else "" for l in body.split("\n"))
        return ">-\n" + "\n".join(pad + l for l in _wrap(v, width - ind))
    return _inline(v)


def _wrap(text, width):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    lines.append(cur)
    return lines


def _inline(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {_inline(x)}" for k, x in v.items()) + "}"
    if isinstance(v, list):
        return "[" + ", ".join(_inline(x) for x in v) + "]"
    try:
        if scalar(v, None) == v and v.strip() == v and v and not any(c in v for c in ",[]{}#"):
            return v
    except ManifestError:
        pass
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t") + '"'


def dump(data):
    return dump_value(data) + "\n"
