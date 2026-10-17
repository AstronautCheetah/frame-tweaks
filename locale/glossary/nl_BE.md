# Glossary and style: Dutch (Flanders), nl_BE

For `locale/nl_BE.po`, which is also the Dutch for the Netherlands (there is no `nl.po`). Keep to
it so the translation reads as one voice; change an entry here first, then
`dev/i18n.py export nl_BE DIR --all` and fix the texts that use it.

**Official wording first.** When a text names something in other software (a SteamVR button, a
KDE app, an Android setting, a Steam label), use that software's own Dutch:
[nl_BE.terms.tsv](nl_BE.terms.tsv) lists the ones our texts use, made by `dev/i18n-terms.py nl_BE`
from SteamVR's, Steam's, Android's, Qt's and KDE's own translations; `--lookup WORD` looks up
any other, and `--check` lists our translations that differ. Where sources disagree, the software
the text talks about decides (KDE's "portefeuille" for the KDE wallet, not Steam's "portemonnee").

## Who reads it
Someone with a Steam Frame (Valve's VR headset running SteamOS) in Flanders or the Netherlands,
using an app that installs fixes and apps ("tweaks"). Standard Dutch as written in Flanders: a
Belgian word where it's the normal one there and a Dutch reader reads past it ("bv.", "4 u"), but
no tussentaal or dialect ("ge/gij", "klavier", "gsm", "plezant") and no Netherlands-only slang
("gaaf", "hartstikke"). Plain, friendly, precise, short sentences like the English; no
marketing, no extra politeness (no "gelieve", no "alstublieft").

Address the reader as **je** (unstressed; "jij"/"jouw" only for contrast), never "u", never
mixed. Steam, SteamVR and Android, whose Dutch surrounds our texts on the Frame, say "je" (about
2,500 of their sentences with "you"; "u" once). KDE and Qt say "u", but we only take labels from
them, which have no pronoun. In Flanders "u" is for letters, banks and government; an app on a
game headset says "je", as Steam does.
- Buttons, menu items, tooltips that name an action: **infinitive**, verb last, as Steam, KDE
  and Android do: "Installeren", "Wijzigingen toepassen", "Kopiëren (Ctrl+C)"; dialog questions
  too ("SteamVR herstarten?"). Progress: "Controleren…"; done: "Gekopieerd".
- Instructions in a sentence: **imperative** (the verb stem): "Klik op", "Tik", "Druk op",
  "Houd … ingedrukt", "Zet Draadloze foutopsporing aan".
- Sentence case everywhere; Dutch has no Title Case ("Wachtwoord wijzigen").

## Keep exactly
- Placeholders and their count/order meaning: `%s`, `%d`, `%(name)s`, `{name}`, `{0}`, `%%`.
  A `{name}` placeholder may move within the sentence; never translate its name.
- HTML tags and attributes (`<b>`, `<a href='...'>`, `<span style=...>`, `<br>`), Markdown
  (`**bold**`, `` `code` ``, links), emoji, arrows and symbols (← ⚙ ✔ ⟳ ⬇ ↻ 🧩 📖 🧪), leading/
  trailing spaces, newlines (`\n`), trailing colons/ellipses ("…"), the quote marks used.
- Commands, paths, file names, option names, environment variables, URLs, key names (Esc, Tab,
  Ctrl, Alt, Super, PgUp, F1). A button or menu item of OTHER software: its official Dutch
  (above); English only when no source has it (then in the same quotes), such as the English
  GitHub bug form's "Diagnostics report" box.
- Product and program names: Frame Tweaks, Steam, Steam Frame, SteamVR, SteamOS, Valve, KDE,
  Plasma, KWin, Dolphin, Kate, Konsole, Android, NordVPN, Signal, Firefox, Tor Browser, VSCodium,
  Claude, Claude Code, Homebrew, Flatpak, Flathub, ydotool, scrcpy, adb, Piper, eSpeak NG,
  whisper.cpp, WireGuard, GitHub, Bluetooth, OCR, README, VPN, D-Bus, Wayland; Wi-Fi is "wifi"
  (as Android and Steam write it).
- **Frame Tweaks' own tools and tweaks are translated** (table below), everywhere they're
  named: Arrow Pad, Full Keyboard, Recline, Android Mirror, Claude Desktop and every tweak title.

## Glossary (use consistently)
| English | Dutch |
|---|---|
| tweak | aanpassing (mv. aanpassingen); the verb "adjust" near it: wijzigen, instellen |
| Arrow Pad / Arrow Pad (VR) | Pijltjesblok / Pijltjesblok (VR) |
| Full Keyboard | Volledig toetsenbord |
| Recline (upstream: Recline-VR, kept) | Achterover |
| Android Mirror | Android-spiegel (its window: de spiegel; to mirror: spiegelen) |
| Claude Desktop | Claude voor desktop |
| Float in World (SteamVR) | In wereld zweven |
| Toggle Curvature (SteamVR) | Kromming in-/uitschakelen |
| Recenter (SteamVR) | Opnieuw centreren |
| Room View (SteamVR); passthrough | Kamerweergave |
| System Settings (KDE) | Systeeminstellingen |
| Change Password (KWalletManager) | Wachtwoord wijzigen |
| Application Launcher (KDE) | Programmastarter |
| Developer options (Android) | Ontwikkelaarsopties |
| Wireless debugging (Android) | Draadloze foutopsporing |
| Pair device with pairing code (Android) | Apparaat koppelen met koppelingscode |
| pack (of tweaks) | pakket (het); package manager: pakketbeheerder |
| Core (pack name, formerly Original) | Basis |
| Integrations / 3rd Party (pack names) | Integraties / Van derden |
| install / uninstall, remove (a tweak) / reinstall | installeren / verwijderen / opnieuw installeren |
| delete (files, settings, a pack) | wissen ("Ja, wissen") |
| remove a pack (Packs page's Remove…: its folder is deleted) | wissen: "Wissen…", "Ja, wissen", "{name} gewist.", "wis het eerst", "kunnen hier gewist worden"; uninstalling its tweaks stays "verwijderen" |
| Linked / linked (🔗, a tweak installed with its project's own installer) | Gekoppeld / gekoppeld (SteamVR's word; "%s is niet gekoppeld"); never "gelinkt". Pairing a phone is also "koppelen" (Android), but the two never meet in one text |
| installer window / the Frame Tweaks window / Tweak installer (menu) | installatievenster / het Frame Tweaks-venster / Installatieprogramma voor aanpassingen |
| Apply changes / Apply | Wijzigingen toepassen / Toepassen |
| settings | Instellingen (SteamVR, Steam, Android, KDE); a setting: een instelling |
| Configure / ⚙ Settings / ⚙ Preferences | Instellen / ⚙ Instellingen / ⚙ Voorkeuren |
| Refresh | Vernieuwen |
| update (noun / verb); up to date | update (de, mv. updates) / bijwerken; bijgewerkt |
| Check for updates | Naar updates zoeken (Steam) |
| release (a version) | versie; pre-release: testversie |
| Restart (a program) / reboot (the Frame) | Herstarten (SteamVR) / opnieuw opstarten (Steam, Android) |
| diagnostics report | diagnoserapport |
| Show hidden | Verborgen tonen |
| hide / unhide | verbergen / weer tonen |
| category | categorie (mv. categorieën) |
| helper (a tweak installed for others) | hulpprogramma |
| experimental | experimenteel |
| Run / Open | Starten / Openen |
| Back / Close / Cancel | Terug / Sluiten / Annuleren |
| Copy / Paste / Cut | Kopiëren / Plakken / Knippen |
| Undo / Redo / Select all / Find / Save | Ongedaan maken / Opnieuw / Alles selecteren / Zoeken / Opslaan |
| clipboard | klembord (het) |
| headset | headset (de); opzetten / afzetten |
| controller | controller (de); linkercontroller, rechtercontroller |
| laser (pointer) | laser (de); laser pointer: laserpen (SteamVR) |
| grip (button) / squeeze | greep (SteamVR) / de greep indrukken |
| trigger | trekker (SteamVR, Steam) |
| thumbstick / D-pad | analoge stick (SteamVR) / vierpuntsdruktoets (Steam); our "joystick": joystick |
| VR | VR: "in VR", "VR-sessie", "VR-venster" |
| desktop mode | bureaubladmodus (Steam) |
| the desktop / desktop apps | het bureaublad / bureaubladapps |
| dashboard (SteamVR's) | dashboard (het), SteamVR-dashboard: SteamVR's own word |
| floating window / float | zwevend venster / laten zweven |
| window | venster (het) |
| overlay | overlay (de; SteamVR) |
| curved / curvature | gebogen / kromming (SteamVR) |
| haptics / haptic tick | haptische feedback (SteamVR) / tik |
| scroll / scroll strips | scrollen (SteamVR, Steam, Android) / scrolstroken (een strook) |
| Screen snip + Narrate | Schermknipsel + Voorlezen |
| snip (noun / verb) | knipsel / een knipsel maken (not "knippen": that's Cut) |
| narrate / narration; read aloud | voorlezen (the feature: Voorlezen) |
| dictation | dicteren (the tweak: Dicteren) |
| speech engine / voice | spraakengine / stem |
| wallet (KDE wallet) | portefeuille (de; KDE-portefeuille), KDE's word |
| lock / unlock / auto-lock | vergrendelen / ontgrendelen / automatisch vergrendelen |
| password | wachtwoord |
| phone | telefoon (not "gsm") |
| pair / pairing code / forget | koppelen / koppelingscode / vergeten (Android) |
| download / fetch | downloaden / ophalen |
| build (from source) | compileren |
| pinned version / pin (Arrow Pad) | vastgezette versie / vastzetten |
| checksum | controlesom (KDE) |
| folder / file / home folder | map / bestand / persoonlijke map (KDE) |
| log | logboek |
| bug report / Report a problem | bugrapport / Een probleem melden |
| status: ok / missing / installed / not installed / running | in orde / ontbreekt / geïnstalleerd / niet geïnstalleerd / actief |
| tick (a checkbox) / untick | aanvinken / uitvinken |
| row | rij; a button on it: "in de rij van Bureaubladherstel", "(↻ in hun rij)" (not "op") |
| shortcut | sneltoets (keys; KDE); a link that starts something: snelkoppeling |
| mirror (download mirror) | spiegelserver |
| tray (system tray) / taskbar | systeemvak (KDE, SteamVR) / taakbalk |
| menu entry / gear (⚙) | menu-item (KDE) / tandwiel |
| tap / right-click / middle-click | tikken (Android) / rechtsklik / middelklik |
| app / computer | app (mv. apps) / computer |

## Key legends and mouse buttons
Arrow Pad's keys (context "key legend") show what Belgian and Dutch keyboards print, short enough
for a key (about 6 letters). Belgian AZERTY keyboards and the US-International ones used in the
Netherlands print English names or symbols, and Qt's Dutch keeps the English names (Esc, Tab,
Backspace, Ins, Del, Home, End, PgUp, PgDown, Print, Shift, Ctrl, Alt, Menu), so the legends
stay English: write them in the msgstr anyway (an empty one counts as untranslated). Where no
short name exists, the ISO/IEC 9995-7 symbol: ⌫ for Backspace (not ←, an arrow key on the pad).

| key | legend | | key | legend |
|---|---|---|---|---|
| Esc | Esc | | Home | Home |
| Tab | Tab | | End | End |
| Bksp | ⌫ | | PgUp | PgUp |
| Del | Del | | PgDn | PgDn |
| Enter | Enter | | PrtSc | PrtSc |
| Ins | Ins | | Menu | Menu |
| Shift | Shift | | Ctrl, Alt, Super | Ctrl, Alt, Super |

Words on keys (same context) are short Dutch words: Tools → Extra (Dutch Windows programs' name
for their Tools menu; the tooltip calls the layer "Extra" too), Unstick → Los (tooltip:
"Toetsen losmaken"), Launcher → Starter (KDE's "Programmastarter"), Snip → Knipsel.

The mouse keys (context "mouse button") show the initial of the word: Right → Rechts (R),
Middle → Midden (M), as in "rechtsklik", "middelklik" (KDE: rechter/middelste muisknop).

A sentence that names a key, layer or button puts the noun first and the legend after it,
exactly as the key shows it: "de toets Extra", "de laag Extra" (its tooltip: "Laag Extra: …"),
"Laag F1–F12", "Tik op Los (onder Extra)", "de knop Knipsel", "de knop 🎤", "met de toets Extra
van Pijltjesblok en dan Knipsel". Screen snip's own Snip action in the Frame Tweaks window (a
verb label) is "Knipsel maken".

## Frame Tweaks' own names (decided in the 2026-10 review)
Use these wherever the English names them, in every text (summaries, READMEs, terminal
messages, status lines), so a title can be found in the list.

| Tweak title (README) | Dutch |
|---|---|
| Android Mirror / Arrow Pad / Full Keyboard (VR) / Recline | Android-spiegel / Pijltjesblok / Volledig toetsenbord (VR) / Achterover |
| Battery charge limit | Laadlimiet voor de batterij |
| Curved world windows | Gebogen zwevende vensters ("world windows": zwevende vensters) |
| Pick up when floating | Oppakken bij zweven |
| Back to the previous window | Terug naar het vorige venster |
| Scroll strips | Scrolstroken (een strook) |
| Dictation; Dictate (toggle) (menu) | Dicteren; Dicteren (aan/uit) |
| Screen snip + Narrate; Screen snip; Narrate | Schermknipsel + Voorlezen; Schermknipsel; Voorlezen |
| Speech engine (helper) | Spraakengine (hulpprogramma); in sentences "de Spraakengine", capital as in the English |
| VR dashboard patching (helper) | Patches voor het VR-dashboard (hulpprogramma) |
| ydotool (helper) / Homebrew / NordVPN (WireGuard) | ydotool (hulpprogramma) / Homebrew / NordVPN (WireGuard) |
| Desktop Recovery; its Restart taskbar | Bureaubladherstel; Taakbalk herstarten |
| Firefox privacy | Privacy in Firefox |
| Shared KDE wallet (also "the Wallet tweak") | Gedeelde KDE-portefeuille ("de aanpassing Gedeelde KDE-portefeuille") |
| Signal: key in the wallet | Signal: sleutel in de portefeuille |
| Shared clipboard / Claude Desktop | Gedeeld klembord / Claude voor desktop |
| Mouse cursor fix / Menu icons | Herstel van de muisaanwijzer / Menupictogrammen |
| a VR environment tweak (the category) | een aanpassing voor de VR-omgeving |
| NordVPN Tray (menu) / App timers (notifications) | NordVPN-systeemvak / Apptimers |

| Wallet apps page (🔑) | Dutch |
|---|---|
| 🔑 Wallet apps | 🔑 Portefeuille-apps |
| Close after / Headset off / Password first | Sluiten na / Headset af / Eerst wachtwoord |
| Auto-lock | Automatisch vergrendelen ("automatisch vergrendelen staat uit"; the noun: de automatische vergrendeling) |
| ⏱ Extend timer / 🔒 Lock now / 🔓 Unlock… | ⏱ Timer verlengen / 🔒 Nu vergrendelen / 🔓 Ontgrendelen… |
| Lock Wallet / Unlock wallet (menu, dialog) | Portefeuille vergrendelen / Portefeuille ontgrendelen |
| Protect / Protected ({n}); protected, gated (apps) | Beveiligen / Beveiligd ({n}); beveiligd ("omgeleid/beveiligd"; the gate: achter het wachtwoord) |
| Remove (an app from the list) | Verwijderen |

| Packs page (🧩) | Dutch |
|---|---|
| Remove… / Yes, delete it / Removed {name}. | Wissen… / Ja, wissen / {name} gewist. |
| Trust… / Use / Stop using / Update | Vertrouwen… / Gebruiken / Niet meer gebruiken / Bijwerken |
| Open packs folder / the Packs page | Pakkettenmap openen / de pagina Pakketten |

**Naming a label in a sentence:** its exact Dutch, with the label's capital, unquoted (quotes
only where the English has them, as for "In wereld zweven"): `<b>Sluiten na</b> sluit de app
af…`, "Stel eerst een tijd in bij Sluiten na", "(Portefeuille-apps: Eerst wachtwoord)", "geen
timer (Sluiten na)", "kies dan Wijzigingen toepassen", "eerst aanvinken en Wijzigingen
toepassen", "kies Opnieuw installeren", "Druk op Taakbalk herstarten", "⬇ Update afronden doet
dat alsnog". Lowercase status lines keep lowercase ("eerst wachtwoord").

**Hours and minutes:** short "%s u", "{h} u", "{h} u {m} min", "{m} min", "4 u", "10 s",
"{seconds} s"; written out where the English writes them out ("4 uur", "15 minuten",
"voor {hours} uur").

**CLI "group"** (`hide-group`): groep, to match the command; the window's category: categorie.

## Notes
- Spelling: the Groene Boekje (woordenlijst.org), the same in Belgium and the Netherlands.
  Compounds are one word ("bureaubladmodus", "koppelingscode"); a hyphen after a name,
  abbreviation, letter or digit, and where vowels clash ("SteamVR-dashboard", "VR-venster",
  "Ctrl-toets", "portefeuille-apps", "menu-item"; "Steam Frame-headset"). Loanwords as it has
  them: app, wifi, e-mail, downloaden (gedownload), scrollen (gescrold; "scrol-" in compounds).
- Numbers: decimal comma ("2,5 s"), "80%", hours "4 u" (short) or "4 uur"; "bv." for "e.g.".
  The Frame is "de Frame", "de Steam Frame" (as in Steam's Dutch).
- Tweak titles: translate descriptive ones ("Shared clipboard" → "Gedeeld klembord", "Mouse
  cursor fix" → "Herstel van de muisaanwijzer", "Desktop Recovery" → "Bureaubladherstel"); keep
  the product names above; every current title is in "Frame Tweaks' own names" above, and a new
  one goes there. Categories: Toegankelijkheid, Gemak, VR-omgeving, Systeem, Hardware,
  Privacy en beveiliging, Voor ontwikkelaars.
- On / off: "aanzetten / uitzetten" in sentences (Android), "inschakelen / uitschakelen" in
  labels. Save is "opslaan", never "bewaren". Status lines and terminal messages stay short,
  with the same punctuation style.
- If an entry is a single word whose role you can't tell, check "where".
- Never leave English untranslated unless it's a command, a placeholder, a key legend or a name
  in the "Keep exactly" list; a text that is only such a name comes back unchanged. Frame
  Tweaks' own tools and tweaks are translated (the table).
- The official terms are for what our text **names** in that software. A generic phrase that only
  happens to match one of theirs (Claude's "Remove them", "removed") is a suggestion; Frame Tweaks'
  own wording in this glossary ("verwijderen" for uninstalling, "wissen" for deleting) wins.
