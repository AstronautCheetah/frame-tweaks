# Marking text for translation

Text reaches translators only once it's marked in the code; `dev/i18n.py extract` then collects
it into `frame-tweaks.pot`. These are the rules the code follows (lib/i18n.py, lib/i18n.sh).

## How
- **Python**: `_("text")`, `ngettext("1 file", "%d files", n)`, `pgettext("context", "text")`.
  The argument must be a plain string literal (no f-string, no concatenation inside the call): turn
  f"Saved {path}" into `_("Saved {path}").format(path=path)` (named braces, so translators can
  reorder) or `_("Saved %s") % path`. Keep the rest of the code identical in behaviour.
  - gui/*.py and lib/*.py already `from i18n import _` (lib/ is on sys.path).
  - **Installed Python programs** (tweak programs copied to ~/.local/...: arrowpad.py, frame-snip,
    wallet-unlock, ...) can't see the repo. Add near the top, after the stdlib imports:
    ```python
    sys.path.insert(0, str(Path.home() / ".local/share/frame-tweaks/i18n"))   # (lib/common.sh install_i18n)
    try:
        from i18n import _, N_, ngettext
    except ImportError:                       # (not installed by Frame Tweaks: English)
        def _(text):
            return text

        def ngettext(singular, plural, n):
            return singular if n == 1 else plural
        N_ = _
    ```
    and in that tweak's install.sh call `install_i18n` (a lib/common.sh function) once, before
    the program is installed. If a module named something else imports these, keep it simple.
  - **Never shadow `_`** where you call `_()`: rename `for _ in`, `_, x = ...`, `lambda _:`,
    `def f(*_)` in any function that also calls `_()` (e.g. `_unused`, `_a`). A lambda parameter
    named `_` only shadows inside that lambda; that's fine if the lambda doesn't call `_()`.
  - **Never call `_()` at module level / import time** (constants, class attributes, default
    arguments): the installer window switches language while running. Mark the literal with
    `N_("...")` (from i18n; a no-op that dev/i18n.py collects) and call `_()` where it's shown:
    `STATE = {"official": (N_("Comes with Frame Tweaks: in use"), "#5cc77a")}` … `QLabel(_(text))`.
    In installed programs' fallback, also define `def N_(text): return text`, and import N_ too.
- **Shell** (bash): `t 'Text with %s' "$value"` prints the translated text (printf-style, no
  newline); use it inside the existing helpers: `say "$(t 'Fetching %s' "$name")"`,
  `die "$(t "Can't build %s: %s" "$what" "$why")"`, `status_ok "$(t 'Running')"`.
  - The text must be one literal: single quotes, or double quotes with NO `$` and no backtick
    inside (dev/i18n.py check fails on `t "...$x..."`). Every value goes in as an argument with
    %s (%d for integers you know are integers). A literal `%` in a text that has arguments is `%%`.
  - Scripts that source lib/common.sh already have `t` (common.sh sources lib/i18n.sh).
  - **Installed bash programs** (copied to ~/.local/bin etc., e.g. adb-scrcpy's `phone`): add
    near the top
    ```bash
    # Translations (lib/i18n.sh; the copy install_i18n puts here), else English
    # shellcheck source=/dev/null
    source "$HOME/.local/share/frame-tweaks/i18n/i18n.sh" 2>/dev/null ||
        t() { local f=$1; shift; if [ $# -eq 0 ]; then printf '%s' "$f"; else printf -- "$f" "$@"; fi; }
    ```
    (add `# shellcheck disable=SC2059` on the printf line if shellcheck asks) and call
    `install_i18n` in that tweak's install.sh.
  - kdialog/notify-send/zenity texts: `kdialog --msgbox "$(t 'Text %s' "$x")"`.

## What to mark
Everything a user reads: window text, buttons, tooltips, dialogs, notifications, terminal
messages from say/warn/die/echo/printf meant for people, status lines (status_ok/missing/warn
texts), errors shown to the user, kdialog texts.

## What NOT to mark (keep English, unchanged)
- Text that is parsed, compared, matched, stored or sent: config keys and values, file
  contents, D-Bus names, command names/arguments, output other code greps (e.g. lines tests or
  the GUI parse; check callers and tests/ before changing an echo), log-only/debug lines, ids,
  category names used as keys (sft translates manifest text itself), JSON keys.
- Product/program names on their own, paths, commands, URLs, version strings.
- dev/ scripts, tests, CI, docs.
- Text that is only whitespace, punctuation, symbols or emoji.
Keep messages whole: don't split a sentence into pieces; put values in with %s / {name}.
Keep every existing English wording exactly (translators get the English as it is now).

## Check

- `python3 -m py_compile` / `bash -n` and `shellcheck -x -S warning` on what you changed.
- `python3 dev/i18n.py extract && python3 dev/i18n.py check` (check also refuses `t "...$x..."`).
- The tests: `python3 -m unittest discover -s tests` (they run in English: tests/test_00_english.py).
