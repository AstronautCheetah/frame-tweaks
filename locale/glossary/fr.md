# Glossary and style: French (France), fr

For `locale/fr.po`. Keep to it so the translation reads as one voice; change an entry here
first, then `dev/i18n.py export fr DIR --all` and fix the texts that use it.

**Official wording first.** When a text names something in other software (a SteamVR button, a
KDE app, an Android setting, a Steam or Claude label), use that software's own French:
[fr.terms.tsv](fr.terms.tsv) lists the ones our texts use, made by `dev/i18n-terms.py fr` from
SteamVR's, Steam's, Android's, Claude Desktop's, Qt's and KDE's own translations;
`dev/i18n-terms.py fr --lookup WORD` looks up any other, and `--check` lists our translations
that differ. Where sources disagree, the software the text talks about decides: KDE's
*Configuration du système* for KDE's System Settings (the .tsv has Steam's *Paramètres du
système* first, so `--check` listing it is expected). The table below follows them too.

## Who reads it
Someone with a Steam Frame (Valve's VR headset running SteamOS) whose keyboard or system is in
French, using an app that installs fixes and apps ("tweaks"). Plain, friendly, precise France
French, also read in Belgium, Switzerland and Canada (their locales use this file): no slang, no
regional words. Short sentences, like the English. Keep the English tone (no marketing, no extra
politeness: no *veuillez*, no *s'il vous plaît*, no *nous* for the app).
- **Vous, not tu**: Steam, SteamVR, KDE, Android and Claude Desktop all say *vous* (Steam's French:
  over 2,000 *vous*, next to no *tu*). *Tu* would be the one voice on the Frame that speaks
  differently; in software *vous* reads neutral, not stiff.
- **Buttons, menu items, checkboxes, options, action tooltips: the infinitive**, as KDE, Steam and
  SteamVR do: *Installer*, *Appliquer les modifications*, *Recevoir aussi les versions de test*.
- **Sentences telling the reader what to do: the vous imperative**: *Appuyez sur Entrée pour
  fermer.* Status lines: a noun or participle, no subject (*Installé*, *Enregistré.*); "Couldn't
  …" is *Impossible de …*.

## Typography
- **U+00A0 (no-break space) before : ; ! ?** and inside « »: *Mot de passe :*, *« Faire flotter
  les vues »*. Always that character: KDE's, SteamVR's and Android's French use it, every font and
  terminal shows it (the narrow U+202F not everywhere), and it keeps the colon on its line. Type
  the character itself, also in HTML (not `&nbsp;`). None before . , … ) and none added inside
  commands, paths, URLs, times (10:30), shortcuts (Ctrl+C) or `<ip>:<port>`.
- **Quotes « »** around names of buttons, menu entries, settings and apps in a sentence, even
  where the English has none: *appuyez sur « Faire flotter les vues »*. Commands and code keep
  the English's quote marks or backticks (`'nordvpn-wg setup'`): someone may type them.
- Straight apostrophe ' (as KDE, Steam and our English), not ’. Ellipsis: one character "…".
- Sentence case, as in KDE (*Rechercher des mises à jour*); capitals keep their accents (*État*,
  *Échap*). Language names in lower case (*en anglais*); the language menu's (Čeština) stay.
- Decimal comma in prose (*1,5*), never in commands. MB → Mo, GB → Go. U+00A0 between a number
  and its unit and before %: *60 Mo*, *80 %*; in a text with `%s`, `%d` or `%%` every percent
  sign is `%%` (*80 %%*), or `dev/i18n.py import` refuses it.

## Keep exactly
- Placeholders and their count/order meaning: `%s`, `%d`, `%(name)s`, `{name}`, `{0}`, `%%`.
  A `{name}` placeholder may move within the sentence; never translate its name.
- HTML tags and attributes (`<b>`, `<a href='...'>`, `<span style=...>`, `<br>`), Markdown
  (`**bold**`, `` `code` ``, links), emoji, arrows and symbols (← ⚙ ✔ ⟳ ⬇ ↻ 🧩 📖 🧪), leading/
  trailing spaces, newlines (`\n`), trailing colons/ellipses ("…", and " :" as above).
- Commands, paths, file names, option names, environment variables, URLs, key names in
  commands. A button or menu item of OTHER software: its official French (above); English only
  when no source has it (then in « »).
- **Key names in sentences and shortcuts** as French keyboards and KDE write them, like Arrow
  Pad's legends (below): Échap, Entrée, Maj, Suppr, Inser, Début, Fin, Retour arrière, Verr. Maj
  (Caps Lock), Ctrl droite (Right Ctrl), Méta (Meta): *Ctrl+Maj+Z*. Ctrl, Alt, Tab, Super, F1 stay.
- Product and program names: Frame Tweaks, Steam, Steam Frame, SteamVR, SteamOS, Valve, KDE,
  Plasma, KWin, Dolphin, Kate, Konsole, Android, NordVPN, Signal, Firefox, Tor Browser, VSCodium,
  Claude, Claude Code, Homebrew, Flatpak, Flathub, ydotool, scrcpy, adb, Piper, eSpeak NG,
  whisper.cpp, WireGuard, GitHub, Wi-Fi, Bluetooth, OCR, README, VPN, D-Bus, Wayland.
  *Le Steam Frame*, *le Frame* (masculine, as in Steam's French).
- **Frame Tweaks' own tools and tweaks are translated** (table below), everywhere they're
  named: Arrow Pad, Full Keyboard, Recline, Android Mirror, Claude Desktop and every tweak title.
  In sentences they take an article (*le Pavé fléché*, *du Miroir Android*); in titles, menu
  entries and « » they don't (*Lancez « Pavé fléché » depuis le menu des applications*).

## Glossary (use consistently)
| English | French |
|---|---|
| tweak | ajustement (m.) |
| Arrow Pad | Pavé fléché |
| Full Keyboard | Clavier complet |
| Recline | Mode allongé (the upstream project, `Recline-VR`, keeps its name) |
| Android Mirror | Miroir Android |
| Claude Desktop | Claude pour ordinateur (Anthropic's own French; no article) |
| Float in World (SteamVR) | Faire flotter les vues |
| Toggle Curvature (SteamVR) | Activer/désactiver la courbure |
| Recenter (SteamVR) | Recentrer (recentering: le recentrage) |
| Room View (SteamVR), passthrough | Vue de la pièce |
| System Settings (KDE) | Configuration du système |
| Change Password (KWalletManager) | Modifier le mot de passe |
| Developer options (Android) | Options pour les développeurs |
| Wireless debugging (Android) | Débogage sans fil |
| Pair device with pairing code (Android) | Associer l'appareil avec un code d'association |
| pack (of tweaks) | pack (m.); software packages: paquets |
| Core (pack name; was Original) | Base |
| Integrations (pack name) | Intégrations |
| 3rd Party (pack name) | Tiers |
| install / uninstall / reinstall | installer / désinstaller / réinstaller |
| remove (a tweak, a pack) / delete (files, settings) | retirer / supprimer |
| Apply changes | Appliquer les modifications |
| settings | Paramètres (SteamVR, Steam, Android, Claude); a setting: un paramètre |
| Configure / ⚙ Settings / Preferences | Configurer / ⚙ Paramètres / Préférences |
| Refresh | Actualiser |
| update (noun/verb) | mise à jour / mettre à jour |
| Check for updates | Rechercher des mises à jour |
| release / test releases / channel | version / versions de test / canal |
| Restart | Redémarrer |
| Diagnostics | Diagnostic (rapport de diagnostic) |
| Show hidden | Afficher les masqués |
| hide / unhide | masquer / réafficher |
| category | catégorie |
| helper (a tweak installed for others) | auxiliaire |
| experimental | expérimental |
| trust / trusted (a pack) | approuver / approuvé (KDE) |
| 🔗 Linked (uses its project's own installer) | 🔗 Lié |
| Run / Open / launch | Exécuter / Ouvrir / lancer |
| Back | Retour (to go back: revenir) |
| Close | Fermer |
| Cancel | Annuler |
| Copy / Paste / Cut | Copier / Coller / Couper |
| clipboard | presse-papiers (m., invariable) |
| press, tap / click / hold / double-tap | appuyer sur / cliquer / maintenir / appuyer deux fois |
| headset | casque |
| controller | contrôleur (SteamVR; Steam for the Frame's) |
| laser (pointer) | laser (pointeur laser) |
| grip (button) / squeeze | poignée (SteamVR) / serrer la poignée |
| trigger | gâchette |
| thumbstick, joystick / D-pad | stick (SteamVR: stick analogique) / croix directionnelle |
| VR | VR (f.): *en VR*, *la session VR*, *le clavier VR*, as Steam and SteamVR (not RV) |
| desktop mode | mode bureau (Steam) |
| the desktop | le bureau |
| taskbar (desktop mode's) | barre des tâches |
| dashboard (SteamVR's) | tableau de bord (de SteamVR; docked: ancré); never KDE's panel |
| floating window / float / pick up (a window) | fenêtre flottante / faire flotter / saisir |
| window | fenêtre |
| the installer window, the Frame Tweaks window | la fenêtre de Frame Tweaks |
| overlay | overlay (m.), SteamVR's and Steam's own French (*l'overlay Steam*) |
| haptics / haptic tick | retour haptique / pulsation haptique (SteamVR) |
| scroll strips | bandes de défilement |
| Screen snip + Narrate | Capture d'écran + Lecture |
| snip (noun / verb) | capture / capturer (the tool: Capture d'écran; in a sentence *l'outil Capture d'écran*) |
| narrate / narration | lire à voix haute / lecture à voix haute (Narrate button: Lire à voix haute) |
| read aloud | lire à voix haute (Claude) |
| dictation | dictée |
| speech engine / voice | moteur vocal / voix |
| wallet (KDE wallet) | portefeuille (le portefeuille KDE) |
| lock / unlock / auto-lock | verrouiller / déverrouiller / verrouillage automatique |
| password / sudo (admin) password | mot de passe / mot de passe sudo (administrateur) |
| phone | téléphone |
| pair / pairing code / forget | associer / code d'association / oublier |
| download / fetch | télécharger |
| build (from source) | compiler |
| fix / patch (SteamVR's dashboard) | correctif / modification |
| pinned version | version fixée |
| checksum | somme de contrôle |
| folder / file / home folder | dossier / fichier / dossier personnel |
| log | journal |
| bug report | rapport de bug (the bug form: le formulaire de signalement) |
| status: ok / missing / installed / not installed / running | OK / manquant / installé / non installé / en cours d'exécution |
| reboot | redémarrer le Frame (noun: le redémarrage) |
| tick (a checkbox) / untick | cocher / décocher |
| row | ligne |
| shortcut | raccourci |
| mirror (download mirror) / mirror a phone | miroir / afficher en miroir |
| tray (system tray) | zone de notification |
| app | application (the app menu: le menu des applications) |
| computer | ordinateur |

## Key legends and mouse buttons
Arrow Pad's keys (context "key legend") show what French AZERTY keyboards print, short enough for
a key (about 6 letters; longer words shrink); where they print only a symbol, or the word would
mislead, the ISO/IEC 9995-7 symbol. These are Arrow Pad's untranslated French legends
(`SEED_LEGENDS`) but one: Backspace is ⌫, as keyboards print a bare ←, which on the pad reads as
the Left arrow (and *Retour* is Qt's Return). Pg↑ Pg↓ shorten Steam's own French keyboard
(*Page ↑*); keyboards print *Pg préc* or ⇞. Qt's and KDE's names (`dev/i18n-terms.py fr --lookup
Backspace`) are the long form, for tooltips: *Retour arrière*, *Page précédente*, *Page suivante*.

| key | legend | | key | legend |
|---|---|---|---|---|
| Esc | Échap | | Home | Début |
| Tab | Tab | | End | Fin |
| Bksp | ⌫ | | PgUp | Pg↑ |
| Del | Suppr | | PgDn | Pg↓ |
| Enter | Entrée | | PrtSc | Impr |
| Ins | Inser | | Menu | Menu |
| Shift | Maj | | Ctrl, Alt, Super | Ctrl, Alt, Super |

Words on keys (same context): Tools → Outils, Unstick → Libérer (it lets go of a stuck modifier
and gives desktop mode's input back), Launcher → Lanceur (KDE's *lanceur d'applications*), Snip →
Capture. Launcher and Snip normally show an icon; the word is the fallback.

The mouse keys (context "mouse button") show the initial of the word: Right → Droit (D),
Middle → Central (C), as in KDE's *bouton droit*, *bouton central* (*clic droit*, *clic
central*). "Right" without that context is a position: *Droite*, *à droite*.

## Names and labels (decided in the first full review, 2026-10-17)
The first translation was done in three parts at once; these are the choices its review made so
the parts read as one voice. A sentence that names a label, button or title quotes it exactly as
it's translated here, in « » (no article inside the quotes).

### Tweak titles, tools, categories and packs
| English | French title | in a sentence |
|---|---|---|
| Arrow Pad | Pavé fléché | le Pavé fléché |
| Full Keyboard (VR) | Clavier complet (VR) | le Clavier complet |
| Recline | Mode allongé | le Mode allongé |
| Android Mirror | Miroir Android | le Miroir Android |
| Claude Desktop | Claude pour ordinateur | Claude pour ordinateur (no article) |
| Dictation | Dictée | la Dictée |
| Screen snip + Narrate (the tweak) | Capture d'écran + Lecture | « Capture d'écran + Lecture » |
| Screen snip (the tool) | Capture d'écran | **l'outil Capture d'écran**, never *la Capture d'écran* (reads as "the screenshot") |
| Speech engine (helper) | Moteur vocal (auxiliaire) | le Moteur vocal |
| Scroll strips | Bandes de défilement | les Bandes de défilement |
| Curved world windows | Fenêtres flottantes courbes | |
| Pick up when floating | Saisir en faisant flotter | |
| Back to the previous window | Retour à la fenêtre précédente | |
| VR dashboard patching (helper) | Modification du tableau de bord VR (auxiliaire) | |
| Battery charge limit | Limite de charge de la batterie | la Limite de charge de la batterie |
| Desktop Recovery | Récupération du bureau | sur la ligne « Récupération du bureau » |
| Shared KDE wallet ("the Wallet tweak") | Portefeuille KDE partagé | l'ajustement « Portefeuille KDE partagé » |
| Signal: key in the wallet | Signal : clé dans le portefeuille | |
| Shared clipboard | Presse-papiers partagé | |
| Firefox privacy | Confidentialité de Firefox | |
| Mouse cursor fix | Correctif du curseur de la souris | |
| Menu icons | Icônes des menus | |
| Homebrew, ydotool (helper), NordVPN (WireGuard) | unchanged (helper: auxiliaire) | |
| NordVPN Tray (menu entry) | NordVPN (zone de notification) | |
| Lock Wallet (menu entry, README button) | Verrouiller le portefeuille | |
| Restart taskbar (button) | Redémarrer la barre des tâches | |
| Categories: Accessibility, Convenience, VR environment, System, Hardware, Privacy & security, Developer | Accessibilité, Confort, Environnement VR, Système, Matériel, Confidentialité et sécurité, Développement | |
| a VR environment tweak / the VR environment tweaks | | un ajustement de la catégorie Environnement VR / les ajustements de la catégorie Environnement VR |
| Packs: Core, Integrations, 3rd Party | Base, Intégrations, Tiers | |

### The Wallet apps page
| English | French |
|---|---|
| 🔑 Wallet apps (button, page) | 🔑 Applications du portefeuille |
| Password first / Close after / Headset off | Mot de passe d'abord / Fermer après / Casque retiré |
| Protect / Protected ({n}) / Remove | Protéger / Protégées ({n}) / Retirer |
| Auto-lock | Verrouillage automatique |
| timer (an app's Close after time) | **délai** (de fermeture), never *minuteur*: *aucun délai de fermeture*, *un délai « Fermer après »*, *après ce délai* |
| App timers (the notifications' sender) | Délais de fermeture des applications |
| ⏱ Extend timer (the auto-lock countdown) | ⏱ Prolonger le délai (tooltip: le compte à rebours) |
| 🔒 Lock now / 🔓 Unlock… | 🔒 Verrouiller / 🔓 Déverrouiller… |
| a label named in a sentence | *(« Applications du portefeuille » : « Mot de passe d'abord »)*; a status line may use it lower case without « » (*mot de passe d'abord*) |

### Screen snip and Narrate
| English | French |
|---|---|
| Narrate, the button (also "Narrate won't work") | « Lire à voix haute » |
| Narrate, the feature in a sentence ("for Screen snip's Narrate") | la lecture à voix haute (de l'outil Capture d'écran) |
| Snip (key legend) / Snip (the README's button) | Capture / Capturer |
| Copy text / Narrate with / Narrate's voice | Copier le texte / Lire avec / Voix de lecture |
| Piper: natural / eSpeak NG: fast | Piper : naturel / eSpeak NG : rapide (masculine: *le moteur*) |
| Speech (ready, downloading) | synthèse vocale |

### The Packs page
| English | French |
|---|---|
| trust / trusted / not trusted / trust it again | approuver / approuvé / non approuvé / l'approuver de nouveau |
| in use / not used / turned off | utilisé / non utilisé / désactivé |
| comes with Frame Tweaks / official | fourni avec Frame Tweaks / officiel |
| where it came from (a pack's link) | sa source |
| Trust… / Open packs folder / Stop using / Use / Update | Approuver… / Ouvrir le dossier des packs / Ne plus utiliser / Utiliser / Mettre à jour |
| the Packs page | la page « Packs » |

### Other wording
| English | French |
|---|---|
| credit labels before a link: from / approach from / fix from / idea from / styled after / uses | de / d'après / correctif de / idée de / inspiré de / utilise |
| Details rows: From / Made by / Source / Needs / Status | Provenance / Créé par / Source / Nécessite / État |
| By: %s (terminal) | Auteur : %s |
| Shown / Hidden in the installer window: %s | Affiché / Masqué dans la fenêtre de Frame Tweaks : %s |
| installer (a program's or project's own) / uninstaller | installateur / programme de désinstallation |
| Tweak installer (the app's generic name) | Installateur d'ajustements |
| (Restart fixes it) / (Reinstall fixes it) / (Reinstall starts it) | (« Redémarrer » corrige le problème) / (« Réinstaller » corrige le problème) / (« Réinstaller » le lance): the button in « », the same words each time |
| ↻ Restart, ⟳ Restart SteamVR named in a sentence | appuyez sur « ↻ Redémarrer », « ⟳ Redémarrer SteamVR » |
| not running (a program, a service) | non lancé (a running/not running column: en cours d'exécution / pas en cours d'exécution) |
| Keep it on (Android Mirror's question) | Rester connecté; its text: *sauf si vous restez connecté* |
| Choose phone… / Restart stream | Choisir le téléphone… / Redémarrer le flux |
| VR extras (Android Mirror) | fonctions VR |
| gear (a VR panel's settings button) | roue dentée |
| F-keys | touches de fonction |
| build (noun) | version (compilée): *ancienne version*, *la version compilée par Frame Tweaks* |
| the taskbar watch | la surveillance de la barre des tâches |
| what happened: %s | détails : %s |
| Steam Frame, Steam Deck | Steam Frame, Steam Deck, with U+00A0 as in Steam's French (fr.terms.tsv) |
| durations | U+00A0 inside: *{h} h {m} min*, *{minutes} minutes*, *10 s* |
| Arrow Pad's keys named in a sentence | in « »: *la touche « Outils », puis « Capture »*; its layers without: *la couche Outils* |
| a .desktop Comment or tooltip that is an action | the infinitive, as a button (*Sélectionner un rectangle…*) |

## Notes
- Tweak titles: translate descriptive ones; keep the product names above. Every title, category
  and pack name, and the wording of the Wallet apps page, Screen snip and the Packs page: see
  "Names and labels" above.
- Status lines are short: keep them short. French runs about a fifth longer than English; on
  buttons, legends and status lines take the shorter wording.
- Terminal messages: keep them concise, same punctuation style (U+00A0 included).
- If an entry is a single word whose role you can't tell, check "where".
- Values you can't see: write *de %s*, not *d'%s*, and *Installé : %s* rather than a participle
  agreeing with an unknown name. Plurals: 0 and 1 take the singular (*0 ajustement*).
- Never leave English untranslated unless it's a command, a placeholder, or a name in the "Keep
  exactly" list; a text that is only such a name comes back unchanged. Frame Tweaks' own tools
  and tweaks are translated (the table).
- The official terms are for what our text **names** in that software. A generic phrase that only
  happens to match one of theirs (Claude's "Remove them", *Les supprimer*) is a suggestion; Frame
  Tweaks' own wording in this glossary (*retirer* a tweak) wins.
