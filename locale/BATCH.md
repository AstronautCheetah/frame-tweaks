# Translating in batches

For a first pass at a language, or catching up after many changes: the texts go out as JSON
files, come back translated, and are checked before they go into the `.po` file. Any translator,
tool or translation helper can do the middle step; `dev/i18n.py` does the rest.

```sh
python3 dev/i18n.py new es_419                 # once: locale/es_419.po (check its Plural-Forms)
python3 dev/i18n.py export es_419 /tmp/es      # what's untranslated: /tmp/es/part-01.json, …
#   … translate each part-NN.json into part-NN.es_419.json (below) …
python3 dev/i18n.py import es_419 /tmp/es      # checked, then put into locale/es_419.po
python3 dev/i18n.py stats
```

`import` leaves out an answer that loses a placeholder (`%s`, `{name}`), an HTML tag, a newline,
or the spaces at either end, and lists it: fix the answer file and import again. Then read the
result in the window (`FRAME_TWEAKS_LANGUAGE=es_419 ./install.sh gui`) and in a terminal
(`FRAME_TWEAKS_LANGUAGE=es_419 ./install.sh status`).

## The files

`part-NN.json`: `[{"id": 1, "ctx": null, "msgid": "...", "plural": null, "where": ["file:line"]}]`.
`part-NN.LANG.json`: `{"1": "translation", "2": ["singular form", "plural form"]}` (a list for an
entry with `plural`, one string per plural form of the language).

## Instructions for whoever translates a part

Give these with the language's glossary (`locale/glossary/LANG.md`; write one first for a new
language, from `es_419.md`'s list of terms):

> Translate every entry of part-NN.json into LANG and write part-NN.LANG.json as above. Follow
> locale/glossary/LANG.md for the reader, tone, the terms and the names that stay as they are.
> Read the files in "where" (the repo) to see what each text is: a button, a tooltip, a terminal
> message, a status line. Keep placeholders (`%s`, `%d`, `{name}`, `%%`), HTML tags, Markdown,
> emoji and symbols, `\n`, and spaces at either end exactly; a `{name}` may move. Keep commands,
> paths, key names (Esc, Ctrl) and product names. Short texts stay short. A text that is only a
> name comes back unchanged. List any entry you weren't sure about.
