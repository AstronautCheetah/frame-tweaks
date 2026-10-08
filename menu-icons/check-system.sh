#!/bin/bash
# The icons are copied from the system's Breeze theme.
for n in utilities-terminal preferences-system; do
    compgen -G "/usr/share/icons/breeze/apps/*/$n.svg" >/dev/null || { echo "Breeze no longer has $n"; exit 1; }
done
echo "Breeze icons present"
