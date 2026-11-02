#!/usr/bin/env bash
# dev/container-check.sh [CHECK...]: dev/check.sh (every check, or those named) in a container
# built from dev/Containerfile, CI's environment, against this checkout as it is (changes not
# committed included). For a machine without Linux, or without the checks' tools: needs Podman or
# Docker (CONTAINER=docker picks one). The image is built the first time, and again when
# dev/Containerfile or lib/python-constraints.txt changes.
#   dev/container-check.sh               every check
#   dev/container-check.sh lint tests    those only (shell python lint i18n commits manifests
#                                        tests metadata docs tweaks)
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
engine=${CONTAINER:-$(command -v podman || command -v docker || true)}
[ -n "$engine" ] || { echo "dev/container-check.sh: needs podman or docker" >&2; exit 1; }
tag=frame-tweaks-checks:$(cat "$repo/dev/Containerfile" "$repo/lib/python-constraints.txt" | git hash-object --stdin | cut -c1-12)
if ! "$engine" image inspect "$tag" >/dev/null 2>&1; then
    echo "building $tag (a few minutes, once)" >&2
    "$engine" build -q -t "$tag" -f "$repo/dev/Containerfile" "$repo" >/dev/null
fi
# The files stay yours: rootless Podman maps your user in (keep-id); Docker runs as your uid. The
# runtime folder is where a desktop has it, /run/user/UID, private to you: tests look there.
uid=$(id -u) gid=$(id -g)
case $(basename "$engine") in
    podman) user=(--userns=keep-id --tmpfs "/run/user/$uid:rw,mode=0700,U") ;;
    *) user=(--user "$uid:$gid" --tmpfs "/run/user/$uid:rw,mode=0700,uid=$uid,gid=$gid") ;;
esac
# (a writable home, as on a desktop; CI= so a missing tool skips, as it does outside CI)
exec "$engine" run --rm "${user[@]}" -e HOME=/tmp/home -e CI= -e "XDG_RUNTIME_DIR=/run/user/$uid" \
    -v "$repo:/src:z" "$tag" bash -c 'mkdir -p "$HOME" && exec dev/check.sh "$@"' _ "$@"
