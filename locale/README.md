# Translating Frame Tweaks

Frame Tweaks uses GNU gettext's standard message catalogues, so the usual tools work: Poedit,
Lokalize, Weblate, or a text editor.

- `frame-tweaks.pot` is the template: every text the installer window, the installer's terminal
  messages and the tweaks' own programs show, and the official tweaks' names, summaries,
  descriptions and settings. Don't edit it: `dev/i18n.py extract`
  makes it from the code and the tweaks' README front matter.
- `<language>.po` (for example `de.po`, `pt_BR.po`, `es_419.po` for Latin American Spanish) is
  one language's translation. A language without its own file uses another of the same
  language: Spanish from Spain or Mexico (`es`, `es_MX`) uses `es_419.po` until there's an `es.po`,
  and Dutch from the Netherlands (`nl`) uses `nl_BE.po` (Flemish).
- Today: `es_419.po` (Latin American Spanish), `fr.po` (French) and `nl_BE.po` (Flemish Dutch),
  each with its glossary in [glossary/](glossary/). The French and Flemish came from a translation
  helper, checked against their glossaries and the official SteamVR, Steam, KDE and Android
  wording, and are marked `# needs review` until a native speaker reads them.

## Adding a language

```sh
python3 dev/i18n.py new de        # starts locale/de.po from the template
```

Check the new file's `Plural-Forms` line for your language (the GNU gettext manual lists them),
then translate the `msgstr ""` lines in your editor of choice. Leave `%s`, `%d` and `{name}`
placeholders as they are; they're filled in by the program. A text you're unsure of can be
marked *fuzzy* (Poedit: "Needs work"): it then isn't used until you clear the mark.

**Needs review** is the other mark: a translator comment line `# needs review` above the entry
(every gettext tool keeps those). The translation *is* used, but `dev/i18n.py stats` and the
Translations needed issue count it as unreviewed. It's for a translation that's probably right
but no person has checked yet: a machine's, or one made without the full context.
`dev/i18n.py import LANG DIR --needs-review` marks what it puts in; `dev/i18n.py export LANG DIR
--review` lists the marked ones, with their translations, for a reviewer; an import with
`--reviewed` takes the mark off (or delete the line by hand).

Translating a lot at once (a new language, or catching up)? [BATCH.md](BATCH.md): export the
untranslated texts as JSON, translate them, and import them with checks. Each language keeps its
terms and tone in [glossary/](glossary/) (Spanish: [glossary/es_419.md](glossary/es_419.md)).
What the text names in other software (SteamVR's "Float in World", KDE's System Settings, an
Android setting) takes that software's own wording: `dev/i18n-terms.py LANG` collects it from
their translations into `glossary/LANG.terms.tsv`, and `--check` lists ours that differ.

## Trying it

```sh
FRAME_TWEAKS_LANGUAGE=de ./install.sh gui
```

Or choose it in the installer window's **⚙ Preferences** (every Frame Tweaks program follows that
choice; kept in `~/.config/frame-tweaks/language`). Left on "Follow the keyboard", or without
`FRAME_TWEAKS_LANGUAGE`, the language follows **the keyboard you're typing with**:
Steam's VR keyboard in VR (its layout chosen in Steam's keyboard settings), KDE's keyboard layout
in desktop mode. An English, QWERTY or other layout that doesn't say which language (Dvorak,
Colemak) leaves the choice to the session (`LANGUAGE`, `LC_ALL`, `LC_MESSAGES`, then `LANG`).
The installer window looks at the keyboard at most every 5 seconds and switches when you're on
its list. It then announces the change (`/run/user/<uid>/frame-tweaks/language`): Arrow Pad and
Screen snip, already open, switch with it (`i18n.follow_announcements`; they don't look at the
keyboard themselves). Scripts and other programs use the language they found when they started.
`FRAME_TWEAKS_KEYBOARD=0` turns the keyboard check off. Anything not translated shows in English.

## Keeping up

Changes are made in English only; the translations catch up in one pass just before a release
(CONTRIBUTING.md, Releasing). When the code or a tweak's text changes, `dev/i18n.py extract`
refreshes the template and notes each new or changed text in [CHANGES.md](CHANGES.md): where it
is and, for a changed one, what it was. `dev/i18n.py update` brings every `.po` file in line with
the template: translations are kept, new text appears untranslated, and text that's gone is kept
at the end as `#~` comments (an export still offers it to adjust). An entry leaves CHANGES.md
once every language has its text. `dev/i18n.py todo` shows what each language has left (new and
changed texts), `dev/i18n.py stats` how far each language is.

## Marking text in the code

The full rules: [MARKING.md](MARKING.md).

- **Python:** `_("Text")`, `ngettext("1 tweak", "%d tweaks", n)`, `pgettext("context", "Text")`;
  `N_("Text")` for a constant made when the program starts, then `_()` where it's shown. Values
  go in afterwards (`_("Saved {path}").format(path=p)`), so the text stays one literal.
- **Shell:** `t 'Text with %s' "$value"` (lib/i18n.sh, sourced by lib/common.sh), printf-style:
  `say "$(t 'Fetching %s' "$name")"`. The text is in single quotes, or double quotes without `$`.
- **SteamVR dashboard patches (JS):** `T('Text')` where it's shown, `N('Text')` in a constant
  (each patch defines both; see scroll-strips' patch.js). Put the language in the patch's
  redraw cache key (`window.__sftI18n?.lang`).
- **Menu entries:** `Name=`, `GenericName=` and `Comment=` in a tweak's `.desktop` file are
  collected as they are; install it with `install_desktop` (lib/common.sh), which adds the
  translations.
- Programs a tweak installs can't see this folder: `install_i18n` (lib/common.sh) copies the
  translations to `~/.local/share/frame-tweaks/i18n`, and the program imports or sources them
  from there (see Arrow Pad or Android Mirror's `phone`).

Two places choose their language differently:

- **Menu entries** (the desktop menu and Steam's "+" menu) open in the language chosen before
  the menu opened, and don't change while it's open. Each carries every translation (the usual
  `Name[es_419]=…` lines, for a system set to that language) and its English
  (`X-Frame-Tweaks-Name=…`); its plain `Name=` is put in the keyboard's language at install and
  again whenever Steam saves a new keyboard layout (a systemd path unit,
  `frame-tweaks-menus.path`, runs `i18n.py menus`; nothing polls). The entries are shared by VR
  and desktop mode, so Steam's VR keyboard decides for both. Reinstall a tweak after its
  translation changes.
- **The ⚙ panels in SteamVR's dashboard** (scroll strips, Android Mirror) follow the keyboard
  like the window: vr-dashboard's `sft-dashboard` sends their text in the current language
  every 5 seconds, and they redraw with it.

## Not translated yet

- The README files.

Contributions that mark more text are welcome (CONTRIBUTING.md, "Translations").
