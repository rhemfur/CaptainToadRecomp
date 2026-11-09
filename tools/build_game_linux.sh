#!/bin/sh
# Builds the reference game runtime (Vulkan renderer, SDL3 host, audio, input, controller gyro) with the
# locally generated Captain Toad code for Linux (x86_64 or arm64), as build/game-linux/wwhd. Run it with
# --game <prepared game folder>. It contains recompiled game code: keep it local.
#
# Needs clang, CMake, Ninja, Python 3, the Vulkan, libcurl and zlib headers, and what SDL3 builds its
# video, audio and controller support with when the system has no SDL3 (Debian/Ubuntu package names):
#   libvulkan-dev libcurl4-openssl-dev zlib1g-dev libx11-dev libxext-dev libxcursor-dev libxi-dev
#   libxrandr-dev libxss-dev libxtst-dev libxkbcommon-dev libwayland-dev libdecor-0-dev libpulse-dev
#   libasound2-dev libudev-dev libdbus-1-dev
# Controller gyro reads DualSense, DualShock 4 and Switch controllers through hidraw: the user needs read
# access to their /dev/hidraw* devices (Steam's udev rules give it).
#
# Environment:
#   CT_GEN       generated game code (default: build/gen, from tools/recompile.py)
#   CT_DEPS      optional folder holding glslang-src, sdl3-src, zlib-src and lz4-src (git checkouts of the
#                versions upstream/cmake pins); empty downloads the pinned sources
#   JOBS, PYTHON
set -eu
task_root=$(cd "$(dirname "$0")/.." && pwd)
task_gen=${CT_GEN:-$task_root/build/gen}
task_build="$task_root/build/game-linux"
python=${PYTHON:-python3}
jobs=${JOBS:-$(getconf _NPROCESSORS_ONLN)}
[ -f "$task_gen/table.c" ] || { echo "No generated game code at $task_gen (tools/recompile.py, or set CT_GEN)"; exit 1; }
for task_tool in clang clang++ cmake ninja "$python"; do
    command -v "$task_tool" > /dev/null || { echo "Missing $task_tool"; exit 1; }
done

"$python" "$task_root/tools/patch_runtime.py" "$task_root/upstream" --gen "$task_gen"

# Strict HLE stops at the first missing import; foreign-guest mode keeps Wind Waker HD addresses out.
task_flags='-DCT_DIAGNOSTIC_STRICT_HLE=1 -DCT_FOREIGN_GUEST=1'
task_extra=
for task_source in fast_mutex.cpp mcp.cpp reference_hle.cpp ct_frame.cpp ct_prompts.cpp; do
    task_extra="$task_extra${task_extra:+;}$task_root/runtime/$task_source"
done
set -- -S "$task_root/upstream" -B "$task_build" -G Ninja \
    -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Release -DWWHD_BUNDLED_DEPS=ON \
    "-DCMAKE_C_FLAGS=$task_flags" "-DCMAKE_CXX_FLAGS=$task_flags" \
    "-DGEN_DIR=$task_gen" "-DCT_EXTRA_SOURCES=$task_extra"
if [ -n "${CT_DEPS:-}" ]; then
    set -- "$@" "-DFETCHCONTENT_SOURCE_DIR_GLSLANG=$CT_DEPS/glslang-src" "-DFETCHCONTENT_SOURCE_DIR_SDL3=$CT_DEPS/sdl3-src" \
        "-DFETCHCONTENT_SOURCE_DIR_ZLIB=$CT_DEPS/zlib-src" "-DFETCHCONTENT_SOURCE_DIR_LZ4=$CT_DEPS/lz4-src"
fi
cmake "$@"
cmake --build "$task_build" --target wwhd --parallel "$jobs"
echo "Built $task_build/wwhd. Run it with --game <prepared game folder>."
