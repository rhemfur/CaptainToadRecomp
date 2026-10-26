#!/bin/sh
# macOS/Linux counterpart of tools/setup_reference.ps1: downloads the pinned runtime/recompiler
# reference into upstream/ and applies the hook-list and strict diagnostic extensions.
set -eu
task_root=$(cd "$(dirname "$0")/.." && pwd)
task_reference="$task_root/upstream"
task_commit=59aa6ddeadd08b557a17743834a2d89a1d2dfc11
python=${PYTHON:-python3}
if [ ! -e "$task_reference" ]; then
    git init "$task_reference"
    git -C "$task_reference" remote add origin https://github.com/ZeldaWWHDRecomp/ZeldaWWHDRecomp.git
    git -C "$task_reference" fetch --depth 1 origin "$task_commit"
    git -C "$task_reference" checkout --detach FETCH_HEAD
fi
task_actual_commit=$(git -C "$task_reference" rev-parse HEAD)
if [ "$task_actual_commit" != "$task_commit" ]; then
    echo 'Existing reference has a different commit; review it before updating. No reset performed.' >&2
    exit 1
fi
"$python" "$task_root/tools/patch_reference.py" "$task_reference"
"$python" "$task_root/tools/patch_diagnostic.py" "$task_reference"
echo 'Pinned runtime/recompiler reference is ready. Supply your own Captain Toad base game and v16 update (USA or EUR).'
