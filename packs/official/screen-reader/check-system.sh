#!/bin/bash
for b in orca kaccess; do command -v "$b" >/dev/null || { echo "$b not found: the screen reader can't start"; exit 1; }; done
echo "Orca and kaccess present"
