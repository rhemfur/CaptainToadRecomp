#!/bin/sh
# Makes build/game-macos/Captain Toad Treasure Tracker.app for Apple Silicon Macs, a portable app: its
# first start asks for your own base game and update, then prepares the game in build/game-macos/data
# (tools/setup_game_macos.sh); later starts launch it, Shift runs setup again.
# The app contains no game code; the setup builds it on this Mac from your files, so keep data/ local.
#
# Requirements: Xcode command line tools, Python 3.10 or later and
#   brew install cmake ninja vulkan-headers vulkan-loader molten-vk glslang zstd
# The app runs this repository's tools: keep the repository where it is.
set -eu
task_root=$(cd "$(dirname "$0")/.." && pwd)
task_out="$task_root/build/game-macos"
task_app="$task_out/Captain Toad Treasure Tracker.app"
python=$(command -v "${PYTHON:-python3}" || true)

if [ "$(uname -s)" != Darwin ] || [ "$(uname -m)" != arm64 ]; then
    echo 'build_game_macos.sh makes the Apple Silicon app; use build_game_windows.ps1 or build_game_android.ps1 elsewhere' >&2
    exit 1
fi
task_missing=''
for tool in clang cmake ninja brew bsdtar osacompile; do
    command -v "$tool" >/dev/null 2>&1 || task_missing="$task_missing $tool"
done
if [ -z "$python" ] || ! "$python" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
    task_missing="$task_missing python3.10+"
fi
if command -v brew >/dev/null 2>&1; then
    for formula in vulkan-headers vulkan-loader molten-vk glslang zstd; do
        brew list --versions "$formula" >/dev/null 2>&1 || task_missing="$task_missing $formula"
    done
fi
if [ -n "$task_missing" ]; then
    echo "Missing:$task_missing" >&2
    echo 'Install the Xcode command line tools (xcode-select --install) and' >&2
    echo '  brew install cmake ninja vulkan-headers vulkan-loader molten-vk glslang zstd' >&2
    exit 1
fi
PYTHON="$python" sh "$task_root/tools/setup_reference.sh"

# Finder starts apps with a minimal PATH: the setup gets this shell's tools and Python.
mkdir -p "$task_out"
task_script="$task_out/CaptainToad.applescript"
"$python" -I - "$task_root/tools/macos/CaptainToad.applescript" "$task_script" "$task_root" "$PATH" "$python" <<'EOF'
import sys
source, target, *values = sys.argv[1:]
text = open(source, encoding='utf-8').read()
for key, value in zip(('@REPO@', '@PATH@', '@PYTHON@'), values):
    text = text.replace(key, value.replace('\\', '\\\\').replace('"', '\\"'))
open(target, 'w', encoding='utf-8').write(text)
EOF
rm -rf "$task_app" "$task_out/Captain Toad.app"  # (the earlier name)
osacompile -o "$task_app" "$task_script"
rm -f "$task_script"
plist="$task_app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Set :CFBundleName Captain Toad: Treasure Tracker' "$plist"
/usr/libexec/PlistBuddy -c 'Add :CFBundleDisplayName string Captain Toad: Treasure Tracker' "$plist" 2>/dev/null ||
    /usr/libexec/PlistBuddy -c 'Set :CFBundleDisplayName Captain Toad: Treasure Tracker' "$plist"
# the game's icon, once a setup has made it from the player's game (tools/build_runtime_macos.sh)
icon="$task_out/data/bin/Captain Toad Treasure Tracker.app/Contents/Resources/AppIcon.icns"
if [ -f "$icon" ]; then
    cp "$icon" "$task_app/Contents/Resources/applet.icns"
    # osacompile's asset catalog (CFBundleIconName) would show the script icon instead
    rm -f "$task_app/Contents/Resources/Assets.car"
    /usr/libexec/PlistBuddy -c 'Delete :CFBundleIconName' "$plist" 2>/dev/null || true
fi
/usr/libexec/PlistBuddy -c 'Add :CFBundleIdentifier string org.ctrecomp.captaintoad' "$plist" 2>/dev/null ||
    /usr/libexec/PlistBuddy -c 'Set :CFBundleIdentifier org.ctrecomp.captaintoad' "$plist"
codesign --force -s - "$task_app" 2>/dev/null || true  # ad-hoc: reseals the bundle after the Info.plist edit
echo "Made $task_app. Start it and choose your base game and v16 update; data stays in $task_out/data."
