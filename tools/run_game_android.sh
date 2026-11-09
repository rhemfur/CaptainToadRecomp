#!/bin/sh
# Installs the private Captain Toad APK (tools/build_game_android.sh) on one phone, optionally copies the
# prepared game tree into the app's folder (Android/data/org.ctrecomp.captaintoad/files/game), starts it
# and saves its log to local-reports/android-game.log. macOS and Linux.
#
#   tools/run_game_android.sh [--push-game] [--push-save] [--serial SERIAL] [--log-seconds N]
#
# --push-game  copy the game (once, or after preparing it again); checks Kinopio.rpx against the profiles
# --push-save  copy your save (user/GameData.bin), replacing the phone's
# SERIAL       from adb devices (default: local-reports/device-target.json, else the only device).
#              Device identifiers stay local.
# Environment: CT_DATA  folder holding game/ and save/ (default: the macOS app's build/game-macos/data)
set -eu
task_root=$(cd "$(dirname "$0")/.." && pwd)
task_package=org.ctrecomp.captaintoad
task_data=${CT_DATA:-$task_root/build/game-macos/data}
task_apk="$task_root/build/game-android/captain-toad.apk"
task_serial= task_push_game=0 task_push_save=0 task_seconds=60
while [ $# -gt 0 ]; do
    case "$1" in
    --push-game) task_push_game=1 ;;
    --push-save) task_push_save=1 ;;
    --serial) task_serial=$2; shift ;;
    --log-seconds) task_seconds=$2; shift ;;
    *) echo "unknown option $1"; exit 2 ;;
    esac
    shift
done
task_device_file="$task_root/local-reports/device-target.json"
if [ -z "$task_serial" ] && [ -f "$task_device_file" ]; then
    task_serial=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["adb_serial"])' "$task_device_file")
fi
if [ -z "$task_serial" ]; then
    task_serial=$(adb devices | awk 'NR > 1 && $2 == "device" { print $1 }')
    [ "$(printf '%s\n' "$task_serial" | grep -c .)" = 1 ] || { echo 'Several or no devices: pass --serial from adb devices'; exit 1; }
fi
[ -f "$task_apk" ] || { echo "Missing $task_apk (tools/build_game_android.sh)"; exit 1; }
ct_adb() { adb -s "$task_serial" "$@"; }

ct_adb get-state > /dev/null
ct_adb install -r "$task_apk"
task_files="/sdcard/Android/data/$task_package/files"
ct_adb shell mkdir -p "$task_files"
if [ "$task_push_game" = 1 ]; then
    task_sha=$(shasum -a 256 "$task_data/game/code/Kinopio.rpx" | cut -d' ' -f1)
    grep -l "\"$task_sha\"" "$task_root"/profiles/*.json > /dev/null ||
        { echo 'Kinopio.rpx matches no Captain Toad profile'; exit 1; }
    ct_adb shell rm -rf "$task_files/game"
    ct_adb shell mkdir -p "$task_files/game"
    for task_dir in code content meta; do
        ct_adb push "$task_data/game/$task_dir" "$task_files/game/"
    done
fi
if [ "$task_push_save" = 1 ]; then
    ct_adb shell mkdir -p "$task_files/save/user"
    ct_adb push "$task_data/save/user/GameData.bin" "$task_files/save/user/GameData.bin"
fi
# adb writes as the shell user into folders only that user and ext_data_rw may open: let the app read them
if [ "$task_push_game" = 1 ] || [ "$task_push_save" = 1 ]; then
    ct_adb shell chmod -R 777 "$task_files/game" "$task_files/save" 2> /dev/null || true
fi
ct_adb logcat -c
ct_adb shell monkey -p "$task_package" -c android.intent.category.LAUNCHER 1 > /dev/null
sleep "$task_seconds"
mkdir -p "$task_root/local-reports"
ct_adb logcat -d -s wwhd SDL AndroidRuntime DEBUG > "$task_root/local-reports/android-game.log" || true
echo "Log saved to local-reports/android-game.log. The runtime also writes $task_files/captures/wwhd.log."
