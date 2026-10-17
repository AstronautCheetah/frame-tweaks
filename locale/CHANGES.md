# English text changes to translate

`dev/i18n.py extract` adds to this each time it refreshes the template: each text that's new, or
whose English changed, with where it is (as of that change) and, for a changed one, what it was.
An entry goes by itself once every language has its text translated (`dev/i18n.py update`,
`import`): what's here is the translation work waiting for the next release (`dev/i18n.py todo`).
`dev/i18n.py export` hands translators what a changed text was, and its old translation, to
adjust. Texts are JSON strings (`\n` is a new line). Don't edit by hand.

## 2026-10-17
- New in `gui/report_page.py:106`
  - now: "📋 Copied"
- Changed in `gui/report_page.py:48`
  - was: "1. Read the report: it's plain text, and nothing in it is sent anywhere unless you attach it.<br>2. Open the bug form (on GitHub; you sign in there), say what happened and what you expected, and drag the report into its Diagnostics report box."
  - now: "1. Read the report below: it's plain text, and nothing in it is sent anywhere unless you add it to the form.<br>2. Open the bug form (on GitHub; you sign in there), say what happened and what you expected, then paste the report into its Diagnostics report box (📋 Copy the report), or attach the saved file."
- Changed in `gui/report_page.py:57`
  - was: "📄 Open the report"
  - now: "📋 Copy the report"
