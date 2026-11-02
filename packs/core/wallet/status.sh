#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/wallet-unlock" ] || status_missing "$(t 'wallet tools not installed')"
sysctl_user is-active --quiet wallet-lock-sync || status_warn "$(t '%s not running: closing the wallet would not lock it (re-run %s)' wallet-lock-sync "./install.sh install wallet")"
sysctl_user is-active --quiet app-timers || status_warn "$(t "%s not running: apps with a timer won't be closed (re-run %s)" app-timers "./install.sh install wallet")"
# (a failing --list must not stop this script, which then read as "not installed")
n=$({ "$BIN/wallet-launcher" --list 2>/dev/null || true; } | wc -l)
state=$("$BIN/wallet-unlock" --status 2>/dev/null || echo unknown)
grep -q oauth_token "$HOME/.config/gh/hosts.yml" 2>/dev/null && status_warn "$(t 'gh token stored in plain text (re-run %s)' "./install.sh install wallet")"
# (brew shellenv below the last PATH line naming ~/.local/bin puts Homebrew's gh ahead of the
# wallet's wrapper in terminals. ensure_path moves only the line it wrote: a line of yours is
# yours to move, and a reinstall couldn't clear this warning.)
last=$(grep -n 'HOME/\.local/bin' "$HOME/.bashrc" 2>/dev/null | grep -Ev '^[0-9]+:[[:space:]]*#' | tail -1 || true)
if [ "${last%%:*}" -lt "$(grep -n 'brew shellenv' "$HOME/.bashrc" 2>/dev/null | tail -1 | cut -d: -f1)" ] 2>/dev/null; then
    # shellcheck disable=SC2016   # (the line as written in ~/.bashrc)
    if grep -qxF 'export PATH="$HOME/.local/bin:$PATH"' "$HOME/.bashrc"; then
        status_warn "$(t "terminals run Homebrew's gh, not the wallet's wrapper: its token would be plain text (re-run %s)" "./install.sh install wallet")"
    fi
    status_warn "$(t "terminals run Homebrew's gh, not the wallet's wrapper: move this line of ~/.bashrc below its brew shellenv line: %s" "${last#*:}")"
fi
# (With Auto-lock off on the Wallet apps page, no timer is what was asked for.)
autolock=$(sed -n 's/^WALLET_AUTOLOCK=//p' "$HOME/.config/frame-tweaks/wallet.conf" 2>/dev/null | tail -1 || true)
if [ "$state" = unlocked ] && [ "$autolock" != 0 ] && ! sysctl_user is-active --quiet wallet-autolock.timer; then
    status_warn "$(t 'wallet unlocked with no auto-lock scheduled (run: %s)' "wallet-unlock --schedule-lock")"
fi
# (--info tries the wallet without a password while it's locked, once per wallet file: SteamOS's
# stock wallet has none, so until one is set nothing in it is protected.)
"$BIN/wallet-unlock" --info 2>/dev/null | grep -q '"password": false' && status_warn "$(t 'the wallet has no password: set one in KWalletManager (kdewallet → Change Password)')"
case $state in
    locked) status_ok "$(t 'wallet locked; %s app launcher(s) routed/gated' "$n")" ;;
    unlocked) status_ok "$(t 'wallet unlocked; %s app launcher(s) routed/gated' "$n")" ;;
    *) status_warn "$(t "wallet-unlock can't tell whether the wallet is locked: protected apps won't open (re-run %s)" "./install.sh install wallet")" ;;
esac
status_ok "$(t 'wallet %s; %s app launcher(s) routed/gated' "$state" "$n")"
