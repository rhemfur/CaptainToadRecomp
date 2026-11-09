#!/bin/sh
# Prepares Captain Toad from your own base game and update on a Mac, as Captain Toad.app's first start
# does: extract archives, merge base and update, translate the game code and build the runtime.
#
# usage: setup_game_macos.sh DATA BASE UPDATE
#   DATA    portable data folder (build/game-macos/data)
#   BASE    extracted base game folder (code/, content/, meta/) or a .rar/.zip/.7z of one
#   UPDATE  extracted v16 update folder or archive, the same way
# Progress goes to DATA/setup-status ("step/total description"), the exit status to DATA/setup-exit.
set -eu
task_root=$(cd "$(dirname "$0")/.." && pwd)
task_data=$1
task_base=$2
task_update=$3
python=${PYTHON:-python3}
mkdir -p "$task_data"
# One setup at a time: two would replace each other's game.new and gen.new. A lock whose process
# has ended is taken over.
task_lock="$task_data/setup.lock"
if ! mkdir "$task_lock" 2>/dev/null; then
    task_other=$(cat "$task_lock/pid" 2>/dev/null || true)
    if [ -n "$task_other" ] && kill -0 "$task_other" 2>/dev/null; then
        echo "Another Captain Toad setup is running (process $task_other); wait for it to finish." >&2
        exit 1
    fi
    rm -rf "$task_lock"
    mkdir "$task_lock"
fi
echo $$ > "$task_lock/pid"
rm -f "$task_data/setup-exit"
trap 'task_code=$?; rm -rf "$task_lock"; echo $task_code > "$task_data/setup-exit"' EXIT
step() { echo "$1/5 $2" > "$task_data/setup-status"; echo "== $1/5 $2"; }

# A Wii U title root holds code/app.xml; archives usually wrap it in one folder.
find_root() {
    found=$(find "$1" -maxdepth 4 -path '*/code/app.xml' -type f | sed 's#/code/app.xml$##')
    if [ -z "$found" ] || [ "$(printf '%s\n' "$found" | wc -l)" -ne 1 ]; then
        echo "Expected one game folder with code/app.xml in $1" >&2
        exit 1
    fi
    printf '%s\n' "$found"
}
source_root() {  # label, folder or archive
    if [ -d "$2" ]; then
        find_root "$2"
        return
    fi
    dir="$task_data/extract/$1"
    rm -rf "$dir"
    mkdir -p "$dir"
    bsdtar -xf "$2" -C "$dir" >&2
    find_root "$dir"
}

step 1 'Checking the runtime reference'
sh "$task_root/tools/setup_reference.sh"

step 2 'Extracting the game files'
base_root=$(source_root base "$task_base")
update_root=$(source_root update "$task_update")
echo "base: $base_root"
echo "update: $update_root"

step 3 'Merging the base game and the update'
rm -rf "$task_data/game.new"
"$python" "$task_root/tools/prepare_game.py" --base "$base_root" --update "$update_root" \
    --output "$task_data/game.new" --manifest "$task_data/game-manifest.json"
rm -rf "$task_data/game" "$task_data/extract"
mv "$task_data/game.new" "$task_data/game"

step 4 'Translating the game code'
rm -rf "$task_data/gen.new"
"$python" "$task_root/tools/recompile.py" --game "$task_data/game" --output "$task_data/gen.new"
rm -rf "$task_data/gen"
mv "$task_data/gen.new" "$task_data/gen"

step 5 'Compiling the game (several minutes)'
CT_DATA="$task_data" PYTHON="$python" sh "$task_root/tools/build_runtime_macos.sh"
echo 'Setup finished.'
