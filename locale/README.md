# Translating Frame Tweaks

Frame Tweaks uses GNU gettext's standard message catalogues, so the usual tools work: Poedit,
Lokalize, Weblate, or a text editor.

- `frame-tweaks.pot` is the template: every text the installer window shows, and the official
  tweaks' names, summaries, descriptions and settings. Don't edit it: `dev/i18n.py extract`
  makes it from the code and the tweaks' README front matter.
- `<language>.po` (for example `de.po`, `pt_BR.po`) is one language's translation.

## Adding a language

```sh
python3 dev/i18n.py new de        # starts locale/de.po from the template
```

Check the new file's `Plural-Forms` line for your language (the GNU gettext manual lists them),
then translate the `msgstr ""` lines in your editor of choice. Leave `%s`, `%d` and `{name}`
placeholders as they are; they're filled in by the program. A text you're unsure of can be
marked *fuzzy* (Poedit: "Needs work"): it then isn't used until you clear the mark.

## Trying it

```sh
FRAME_TWEAKS_LANGUAGE=de ./install.sh gui
```

Without `FRAME_TWEAKS_LANGUAGE`, the language comes from the session (`LANGUAGE`, `LC_ALL`,
`LC_MESSAGES`, then `LANG`), and anything not translated shows in English.

## Keeping up

When the code or a tweak's text changes, `dev/i18n.py extract` refreshes the template and
`dev/i18n.py update` brings every `.po` file in line with it: translations are kept, new text
appears untranslated, and text that's gone is kept at the end as `#~` comments.
`dev/i18n.py stats` shows how far each language is.

## Not translated yet

- The installer's messages in the terminal (`install.sh` and the tweaks' scripts) and the
  tweaks' own programs (Arrow Pad, Screen snip + Narrate, Android Mirror's dialogs).
- The README files.
- Some of the window's text that's built from parts (it needs its markers adding by hand).

These are the next steps; contributions that mark more text with `_()` are welcome
(CONTRIBUTING.md, "Translations").
