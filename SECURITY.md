# Security notes

Several tweaks handle secrets. This page says what they touch and what they do and don't
protect against.

| Tweak | Touches | Notes |
|---|---|---|
| wallet | KDE wallet (`kwalletd6`/`ksecretd`) | `wallet-unlock` derives the wallet key (PBKDF2-SHA512, as kwallet-pam does) and hands it to `ksecretd` over D-Bus; the password and key never appear on a command line or on disk. |
| wallet (`gh`) | GitHub CLI token | Moved from `~/.config/gh/hosts.yml` (plain text) into the wallet. |
| signal | Signal's database key | Stored in the wallet (Electron safeStorage, `v11`). Signal's data is only as safe as the wallet password. |
| nordvpn | NordVPN access token, WireGuard private key | The token is used once and never stored. The private key lives in root-only NetworkManager files and `~/.config/nordvpn-wg/private_key` (mode 600). |
| firefox | Firefox prefs only | No access to saved logins. Set Firefox's **Primary Password** to encrypt them. |

**Threat model.** These tweaks protect against *casual* access: someone else picking up the
headset (e.g. children on a shared, password-less SteamOS login) can't open Signal, Firefox
or Phone Mirror, or read Signal's database, while the wallet is locked. They don't protect
against someone who can use desktop mode while the wallet is unlocked (4 hours after you
unlock it, or until `wallet-unlock --lock`), or against malware running as your user.

**Set a wallet password.** SteamOS seeds every Frame with the same stock wallet, and it has no
password. Until you set one (KWalletManager → *Change Password*), nothing above is really
protected. Avoid changing it while a second wallet service is running (see
[wallet/README.md](wallet/README.md#kde-6-gotcha-ksecretd-holds-the-wallet)).

**Downloads** are verified where the publisher provides checksums: Claude Desktop (SHA256
from Anthropic's apt index) and Full Keyboard (release `SHA256SUMS`). Arch Linux ARM packages
come over HTTP from the official mirror, as pacman would fetch them, but without pacman's
signature check. Homebrew and Flathub packages are verified by those tools.

Found a problem? Please open a private security advisory on GitHub rather than a public issue.
