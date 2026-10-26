#!/bin/sh
# Builds the reference game runtime (Metal and Vulkan renderers, AppKit host, audio, input) with the
# locally generated Captain Toad code for Apple Silicon Macs, as data/bin/Captain Toad Treasure
# Tracker.app. The launcher (Captain Toad Treasure Tracker.app) runs this during its setup
# (tools/setup_game_macos.sh); it also runs on its own. It contains recompiled game code: keep it local.
#
# Environment overrides:
#   CT_DATA      portable data folder (default: <repo>/build/game-macos/data); the runtime goes to bin/
#   CT_GEN_DIR   generated Captain Toad code (default: $CT_DATA/gen)
#   CT_RENDERER  BOTH (default: Metal and Vulkan through MoltenVK), METAL or VULKAN (SDL3 host;
#                also needs brew install sdl3 lz4)
#   JOBS, PYTHON
set -eu
task_root=$(cd "$(dirname "$0")/.." && pwd)
task_data=${CT_DATA:-$task_root/build/game-macos/data}
task_build="$task_data/cmake"
task_gen=${CT_GEN_DIR:-$task_data/gen}
task_renderer=${CT_RENDERER:-BOTH}
python=${PYTHON:-python3}
jobs=${JOBS:-$(sysctl -n hw.ncpu)}

"$python" "$task_root/tools/patch_runtime.py" "$task_root/upstream" --gen "$task_gen"

brew_prefix=$(brew --prefix 2>/dev/null || echo /opt/homebrew)
# Strict HLE stops at the first missing import; foreign-guest mode keeps the reference game's addresses out.
# The Objective-C++ host and Metal renderer include guest_addr.h too, so they get the same flags.
task_flags='-DCT_DIAGNOSTIC_STRICT_HLE=1 -DCT_FOREIGN_GUEST=1'
task_extra="$task_root/runtime/fast_mutex.cpp;$task_root/runtime/mcp.cpp;$task_root/runtime/reference_hle.cpp;$task_root/runtime/ct_frame.cpp;$task_root/runtime/ct_prompts.cpp"
cmake -S "$task_root/upstream" -B "$task_build" -G Ninja \
    -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_OBJCXX_COMPILER=clang++ \
    -DCMAKE_BUILD_TYPE=Release \
    "-DCMAKE_PREFIX_PATH=$brew_prefix" \
    "-DWWHD_RENDERER=$task_renderer" \
    "-DCMAKE_C_FLAGS=$task_flags" "-DCMAKE_CXX_FLAGS=$task_flags" "-DCMAKE_OBJCXX_FLAGS=$task_flags" \
    "-DGEN_DIR=$task_gen" \
    "-DCT_EXTRA_SOURCES=$task_extra"
cmake --build "$task_build" --target wwhd --parallel "$jobs"

# The runtime runs as an app of its own, so the Dock and Cmd-Tab show its name and the game's icon
# (meta/iconTex.tga of the player's game, converted here). The launcher starts it with
# WWHD_USER_DIR=data/user: portable mode, so settings, controls, save states, shader caches and logs stay
# in data/ and nothing goes to the per-user Library folders or user defaults.
task_name='Captain Toad Treasure Tracker'
task_bundle="$task_data/bin/$task_name.app"
mkdir -p "$task_data/bin" "$task_data/save" "$task_data/user"
rm -f "$task_data/bin/wwhd" "$task_data/bin/captain-toad" "$task_data/bin/portable.txt"
rm -rf "$task_bundle.new"
mkdir -p "$task_bundle.new/Contents/MacOS" "$task_bundle.new/Contents/Resources"
cp "$task_build/wwhd" "$task_bundle.new/Contents/MacOS/$task_name"
{
    echo '<?xml version="1.0" encoding="UTF-8"?>'
    echo '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">'
    echo '<plist version="1.0"><dict>'
    echo '  <key>CFBundleName</key><string>Captain Toad: Treasure Tracker</string>'
    echo '  <key>CFBundleDisplayName</key><string>Captain Toad: Treasure Tracker</string>'
    echo '  <key>CFBundleIdentifier</key><string>org.ctrecomp.captaintoad.game</string>'
    echo "  <key>CFBundleExecutable</key><string>$task_name</string>"
    echo '  <key>CFBundleIconFile</key><string>AppIcon</string>'
    echo '  <key>CFBundlePackageType</key><string>APPL</string>'
    echo '  <key>CFBundleShortVersionString</key><string>0.0.0</string>'
    echo '  <key>CFBundleVersion</key><string>0.0.0</string>'
    echo '  <key>LSMinimumSystemVersion</key><string>14.0</string>'
    echo '  <key>NSHighResolutionCapable</key><true/>'
    echo '</dict></plist>'
} > "$task_bundle.new/Contents/Info.plist"
# The icon comes from the player's game and stays in build/ (never in the repository): a 640x640 square
# of the title art (meta/bootTvTex.tga, 1280x720), sharper than the game's 128x128 meta/iconTex.tga,
# which is the fallback.
task_iconset="$task_build/AppIcon.iconset"
rm -rf "$task_iconset"
mkdir -p "$task_iconset"
task_icon_ok=''
if sips -s format png "$task_data/game/meta/bootTvTex.tga" --out "$task_iconset/source.png" >/dev/null 2>&1 &&
   [ "$(sips -g pixelWidth "$task_iconset/source.png" | awk '/pixelWidth/{print $2}')" = 1280 ] &&
   sips -c 640 640 --cropOffset 50 320 "$task_iconset/source.png" >/dev/null 2>&1; then
    task_icon_ok=1
elif sips -s format png "$task_data/game/meta/iconTex.tga" --out "$task_iconset/source.png" >/dev/null 2>&1; then
    task_icon_ok=1
fi
if [ -n "$task_icon_ok" ]; then
    for size in 16 32 128 256 512; do
        sips -z $size $size "$task_iconset/source.png" --out "$task_iconset/icon_${size}x${size}.png" >/dev/null
        sips -z $((size * 2)) $((size * 2)) "$task_iconset/source.png" --out "$task_iconset/icon_${size}x${size}@2x.png" >/dev/null
    done
    rm "$task_iconset/source.png"
    iconutil -c icns "$task_iconset" -o "$task_bundle.new/Contents/Resources/AppIcon.icns" || true
fi
codesign --force -s - "$task_bundle.new" >/dev/null 2>&1 || true
# A new bundle, never an overwrite: macOS kills launches of a signed executable whose file changed in
# place (its cached code signature no longer matches), and a running game would read the new pages.
rm -rf "$task_bundle.old"
if [ -d "$task_bundle" ]; then mv "$task_bundle" "$task_bundle.old"; fi
mv "$task_bundle.new" "$task_bundle"
rm -rf "$task_bundle.old"
# the launcher next to data/ shows the same icon
task_launcher="$task_data/../$task_name.app"
if [ -f "$task_bundle/Contents/Resources/AppIcon.icns" ] && [ -d "$task_launcher/Contents/Resources" ]; then
    cp "$task_bundle/Contents/Resources/AppIcon.icns" "$task_launcher/Contents/Resources/applet.icns"
    # osacompile's asset catalog (CFBundleIconName) would show the script icon instead
    rm -f "$task_launcher/Contents/Resources/Assets.car"
    /usr/libexec/PlistBuddy -c 'Delete :CFBundleIconName' "$task_launcher/Contents/Info.plist" 2>/dev/null || true
    codesign --force -s - "$task_launcher" >/dev/null 2>&1 || true
    touch "$task_launcher"
fi
echo "Built $task_bundle."
