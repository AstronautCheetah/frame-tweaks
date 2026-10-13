#!/bin/bash
# Windows you already floated keep their current float-return. (vr-dashboard, shared, stays.)
source "$(dirname "$0")/../lib/common.sh"
remove_dashboard_patch float-return
