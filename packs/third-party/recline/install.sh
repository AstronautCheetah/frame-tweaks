#!/bin/bash
# Recline: new-waifu/Recline-VR, built from the pinned commit with SteamOS's own CMake and
# compiler, then installed by its own installer into ~/.local/share/recline-vr.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
DEST="$HOME/.local/share/recline-vr"
VRPATHREG=/opt/steamvr/bin/linuxarm64/vrpathreg
CONF="$HOME/.config/frame-tweaks/recline.conf"

bash "$TWEAK_DIR/check-system.sh" >/dev/null || die "$(t "can't build Recline: %s" "$(bash "$TWEAK_DIR/check-system.sh")")"

BUILD="$HOME/.cache/frame-tweaks/recline-build"
SRC="$BUILD/src"
rm -rf "$BUILD" && mkdir -p "$BUILD"
trap 'rm -rf "$BUILD"' EXIT
version=$(sed -n 's/^version=//p' "$TWEAK_DIR/pin")
rev=$(sed -n 's/^rev=//p' "$TWEAK_DIR/pin")
say "$(t 'Fetching Recline-VR %s from %s' "$version" https://github.com/new-waifu/Recline-VR)"
if git clone -q "$(sed -n 's/^url=//p' "$TWEAK_DIR/pin")" "$SRC" &&
   git -C "$SRC" -c advice.detachedHead=false checkout -q "$rev"; then
    [ "$(git -C "$SRC" rev-parse HEAD)" = "$rev" ] || die "$(t '%s: not the pinned commit' Recline-VR)"
else      # gone upstream: Frame Tweaks' copy of that commit's source (dev/mirror-pins.sh)
    warn "$(t "%s's pinned commit isn't available upstream; using Frame Tweaks' copy" Recline-VR)"
    rm -rf "$SRC" && mkdir -p "$SRC"
    fetch_mirror "$(sed -n 's/^mirror=//p' "$TWEAK_DIR/pin")" \
        "$(sed -n 's/^mirror_sha256=//p' "$TWEAK_DIR/pin")" "$BUILD/src.tar.gz"
    tar -xzf "$BUILD/src.tar.gz" -C "$SRC" --strip-components=1
fi

say "$(t 'Building it (under a minute) and running its tests')"
cmake -S "$SRC" -B "$BUILD/out" -DCMAKE_BUILD_TYPE=RelWithDebInfo -DRECLINE_VERSION="v$version" >/dev/null ||
    die "$(t 'Recline-VR: cmake failed')"
cmake --build "$BUILD/out" -j "$(nproc)" >/dev/null || die "$(t 'Recline-VR: the build failed')"
ctest --test-dir "$BUILD/out" --output-on-failure >/dev/null || die "$(t 'Recline-VR: its tests failed; nothing was installed')"
grep -q '^Vulkan_INCLUDE_DIR:PATH=/' "$BUILD/out/CMakeCache.txt" ||
    die "$(t "Recline-VR built without Vulkan; not installing (its fallback has crashed SteamVR's compositor)")"

# The room-view fix is the library loaded into the Frame's camera service; without the file,
# Recline-VR skips that part.
PASSTHROUGH=on
[ -f "$CONF" ] && PASSTHROUGH=$(sed -n 's/^RECLINE_PASSTHROUGH_FIX=//p' "$CONF" | tr -d '"' | tail -1)
shim=recline/bin/linuxarm64/librecline_xrshim.so
if [ "${PASSTHROUGH:-on}" = off ]; then
    rm -f "$BUILD/out/stage/$shim" "$DEST/$shim"
    say "$(t 'Room-view fix left out (setting); the room view will look tilted while reclined')"
fi

# vrpathreg tells SteamVR's monitor about a new driver with xdg-open vrmonitor://driverinstalled;
# nothing on the Frame opens that, so desktop mode would show "Could not read file". Skip it.
mkdir -p "$BUILD/quiet" && printf '#!/bin/sh\nexit 0\n' > "$BUILD/quiet/xdg-open" && chmod +x "$BUILD/quiet/xdg-open"
PATH="$BUILD/quiet:$PATH" DEST="$DEST" VRPATHREG="$VRPATHREG" "$BUILD/out/stage/install.sh"
echo "$version" > "$DEST/.frame-tweaks-version"
say "$(t 'Recline %s installed. Restart SteamVR to load it (reboot, or: %s).' "$version" "steamvr restart")"
