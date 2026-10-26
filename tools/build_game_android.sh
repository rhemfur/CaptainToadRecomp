#!/bin/sh
# Builds the reference game runtime with the locally generated Captain Toad code as the Android app's
# native library (libmain.so, as the reference's android/build_native.sh does), then a private APK
# (package org.ctrecomp.captaintoad) at build/game-android/captain-toad.apk. macOS and Linux.
# The APK contains recompiled game code: keep it on your own devices and never distribute it.
#
# Environment:
#   CT_GEN       generated game code (default: the macOS app's data/gen, else build/gen)
#   CT_GAME      prepared game tree, for the launcher icon (default: next to CT_GEN)
#   ANDROID_SDK  SDK with ndk/$NDK_VERSION (default: ANDROID_HOME, ~/Library/Android/sdk or Homebrew's)
#   NDK_VERSION  default 30.0.16248370
#   CPU          generic (default, any arm64 phone) or an -mcpu value such as oryon-1
#   JAVA_HOME    JDK 17 to 21 for Gradle 8.12 (default: Homebrew's openjdk@21 or openjdk@17)
#   JOBS         default: the number of CPUs
set -eu
task_root=$(cd "$(dirname "$0")/.." && pwd)
task_upstream="$task_root/upstream"
task_build="$task_root/build/game-android"
case "$(uname -s)" in
Darwin) task_host=darwin-x86_64 ;;
Linux) task_host=linux-x86_64 ;;
*) echo "unsupported host $(uname -s)"; exit 2 ;;
esac

task_gen=${CT_GEN:-}
if [ -z "$task_gen" ]; then
    task_gen="$task_root/build/game-macos/data/gen"
    [ -d "$task_gen" ] || task_gen="$task_root/build/gen"
fi
[ -d "$task_gen" ] || { echo "No generated game code at $task_gen (set CT_GEN)"; exit 1; }
task_gen=$(cd "$task_gen" && pwd)
task_game=${CT_GAME:-$(dirname "$task_gen")/game}

task_sdk=${ANDROID_SDK:-${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}}
if [ -z "$task_sdk" ]; then
    for task_try in "$HOME/Library/Android/sdk" "$HOME/Android/Sdk" /opt/homebrew/share/android-commandlinetools; do
        if [ -d "$task_try" ]; then task_sdk=$task_try; break; fi
    done
fi
task_ndk="$task_sdk/ndk/${NDK_VERSION:-30.0.16248370}"
[ -f "$task_ndk/build/cmake/android.toolchain.cmake" ] || {
    echo "No NDK at $task_ndk (sdkmanager \"ndk;${NDK_VERSION:-30.0.16248370}\" \"platforms;android-36\" \"build-tools;35.0.0\")"
    exit 1
}
task_llvm="$task_ndk/toolchains/llvm/prebuilt/$task_host"
for task_tool in cmake ninja python3; do
    command -v "$task_tool" > /dev/null || { echo "Missing $task_tool"; exit 1; }
done
if [ -z "${JAVA_HOME:-}" ]; then
    for task_try in /opt/homebrew/opt/openjdk@21 /opt/homebrew/opt/openjdk@17; do
        if [ -x "$task_try/bin/java" ]; then JAVA_HOME=$task_try; break; fi
    done
fi
[ -n "${JAVA_HOME:-}" ] && [ -x "$JAVA_HOME/bin/java" ] || { echo "No JDK 17-21 (set JAVA_HOME)"; exit 1; }
export JAVA_HOME ANDROID_HOME="$task_sdk"
task_jobs=${JOBS:-$(getconf _NPROCESSORS_ONLN)}

python3 "$task_root/tools/patch_runtime.py" "$task_upstream" --gen "$task_gen"

# Strict HLE stops at the first missing import; foreign-guest mode keeps Wind Waker HD addresses out.
task_flags='-DCT_DIAGNOSTIC_STRICT_HLE=1 -DCT_FOREIGN_GUEST=1'
if [ "${CPU:-generic}" != generic ]; then task_flags="$task_flags -mcpu=$CPU"; fi
task_extra=
for task_source in fast_mutex.cpp mcp.cpp reference_hle.cpp ct_frame.cpp ct_prompts.cpp; do
    task_extra="$task_extra${task_extra:+;}$task_root/runtime/$task_source"
done
mkdir -p "$task_build"
echo "== libmain.so (NDK $(basename "$task_ndk"), CPU ${CPU:-generic}); log: $task_build/native.log"
cmake -S "$task_upstream" -B "$task_build/native" -G Ninja \
    "-DCMAKE_TOOLCHAIN_FILE=$task_ndk/build/cmake/android.toolchain.cmake" -DANDROID_ABI=arm64-v8a \
    -DANDROID_PLATFORM=android-33 -DANDROID_STL=c++_shared -DCMAKE_BUILD_TYPE=Release -DWWHD_BUNDLED_DEPS=ON \
    "-DCMAKE_C_FLAGS=$task_flags" "-DCMAKE_CXX_FLAGS=$task_flags" \
    "-DGEN_DIR=$task_gen" "-DCT_EXTRA_SOURCES=$task_extra" > "$task_build/native.log" 2>&1 ||
    { tail -40 "$task_build/native.log"; exit 1; }
cmake --build "$task_build/native" --parallel "$task_jobs" --target wwhd wwhd_yaz0 >> "$task_build/native.log" 2>&1 ||
    { tail -40 "$task_build/native.log"; exit 1; }

task_libs="$task_upstream/android/app/libs/arm64-v8a"
rm -rf "$task_libs"
mkdir -p "$task_libs"
"$task_llvm/bin/llvm-strip" --strip-unneeded "$task_build/native/libmain.so" -o "$task_libs/libmain.so"
"$task_llvm/bin/llvm-strip" --strip-unneeded "$task_build/native/libyaz0.so" -o "$task_libs/libyaz0.so"
cp "$(find "$task_build/native/_deps" -name libSDL3.so -print -quit)" "$task_libs/"
cp "$task_llvm/sysroot/usr/lib/aarch64-linux-android/libc++_shared.so" "$task_libs/"
# libadrenotools loads these hooks by soname from the app's native library folder
for task_hook in main_hook hook_impl file_redirect_hook gsl_alloc_hook; do
    task_file=$(find "$task_build/native/_deps" -name "lib$task_hook.so" -print -quit)
    [ -n "$task_file" ] || { echo "Missing AdrenoTools hook: $task_hook"; exit 1; }
    cp "$task_file" "$task_libs/"
done

# Launcher icon from your own game (android/app/local-res, git-ignored): the title screen's middle,
# sharper than the 128x128 iconTex.tga. Never committed: the picture is the game's.
if [ -f "$task_game/meta/bootTvTex.tga" ] && python3 -c 'import PIL' 2> /dev/null; then
    mkdir -p "$task_build/icon/meta"
    python3 -c 'import sys; from PIL import Image
Image.open(sys.argv[1]).convert("RGBA").crop((320, 50, 960, 690)).save(sys.argv[2])' \
        "$task_game/meta/bootTvTex.tga" "$task_build/icon/meta/iconTex.tga"
    python3 "$task_upstream/android/make_icon.py" "$task_build/icon" > /dev/null
fi

echo "== APK (Gradle)"
(cd "$task_upstream/android" && ./gradlew --quiet assembleRelease)
cp "$task_upstream/android/app/build/outputs/apk/release/app-release.apk" "$task_build/captain-toad.apk"
echo "Built $task_build/captain-toad.apk (package org.ctrecomp.captaintoad). It contains recompiled game code: keep it private."
