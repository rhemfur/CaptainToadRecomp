#!/bin/sh
# Installs Captain Toad's graphic packs from Cemu's community repository (cemu-project/cemu_graphic_packs,
# CC0-1.0) into the Mods tab of build/game-macos (Settings > Mods > Installed). They arrive switched off.
#
#   Shadow Resolution (Enhancements/CaptainToad_Shadows, by Ryce-Fast): a texture rule for the 1024x1024
#     shadow map, presets 50% to 400%.
# Not installed: Resolution (Resolutions/CaptainToad_Resolution): the runtime has its own internal resolution,
# and the pack's ultrawide aspect changes are code patches, which this runtime does not apply yet.
#
# Environment: CT_DATA  portable data folder (default: <repo>/build/game-macos/data)
set -eu
task_root=$(cd "$(dirname "$0")/.." && pwd)
task_data=${CT_DATA:-$task_root/build/game-macos/data}
task_commit=975f3759d7837da5a374150347d3202360b13ca3
task_mods="$task_data/user/ModManager/Mods"

install_pack() {  # id, repository folder, name, credit
    target="$task_mods/$1"
    if [ -e "$target" ]; then
        echo "$3: already installed ($target)"
        return
    fi
    staging="$target.download"
    rm -rf "$staging"
    mkdir -p "$staging"
    curl -fsSL "https://raw.githubusercontent.com/cemu-project/cemu_graphic_packs/$task_commit/$2/rules.txt" -o "$staging/rules.txt"
    printf '{"format_version": 1, "id": "%s", "name": "%s", "version": "1.0.0", "game_id": "captain-toad", "kind": "cemu", "cemu_dir": "", "description": "%s, from Cemu graphic packs (%s, CC0-1.0)."}\n' \
        "$1" "$3" "$4" "$2" > "$staging/manifest.json"
    mv "$staging" "$target"
    echo "$3: installed, switched off (Settings > Mods > Installed)"
}

mkdir -p "$task_mods"
install_pack cemu.captaintoad-shadows Enhancements/CaptainToad_Shadows "Shadow Resolution" "Shadow map resolution by Ryce-Fast"
