#!/bin/bash
# KDE wallet pieces wallet-unlock and the broker talk to.
miss=()
for b in kwalletd6 ksecretd kdialog; do command -v "$b" >/dev/null || miss+=("$b"); done
[ -S "/run/user/$(id -u)/bus" ] || miss+=("Steam session D-Bus")
[ ${#miss[@]} -eq 0 ] || { echo "missing: ${miss[*]}"; exit 1; }
echo "kwalletd6, ksecretd, kdialog and the Steam session's D-Bus present"
