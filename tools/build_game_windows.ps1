param(
    # llvm-mingw toolchain whose target matches the PC (aarch64 for Snapdragon X, x86_64 otherwise)
    [string]$LlvmMingw = 'C:\dev\rel-dl\llvm-mingw-20260922-ucrt-aarch64',
    [string]$Target = 'aarch64',
    [string]$CMakeRoot = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake',
    # Vulkan headers and a MinGW import library; the runtime loads vulkan-1.dll itself at startup
    [string]$VulkanInclude = 'C:\VulkanSDK\Include',
    [string]$VulkanLibrary = 'C:\dev\rel-dl\vulkan\libvulkan-1.a',
    # optional folder holding glslang-src, sdl3-src, zlib-src and lz4-src from an earlier build;
    # empty downloads the reference's pinned dependency sources
    [string]$DependencySources = '',
    [int]$Jobs = 10,
    [string]$Python = 'python'
)
# Builds the reference game runtime (Vulkan renderer, SDL3 host, audio, input) with the locally
# generated Captain Toad code. The executable contains recompiled game code: keep it local.
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskBuild = Join-Path $taskRoot 'build\game-windows'
& $Python (Join-Path $PSScriptRoot 'patch_runtime.py') (Join-Path $taskRoot 'upstream') --gen (Join-Path $taskRoot 'build\gen')
if ($LASTEXITCODE -ne 0) { throw 'Runtime preparation failed' }
$taskBin = Join-Path $LlvmMingw 'bin'
$env:PATH = $taskBin + ';' + $env:PATH
# Strict HLE stops at the first missing import; foreign-guest mode keeps Wind Waker HD addresses out.
$taskFlags = '-DCT_DIAGNOSTIC_STRICT_HLE=1 -DCT_FOREIGN_GUEST=1'
$taskExtra = @('fast_mutex.cpp', 'mcp.cpp', 'reference_hle.cpp' | ForEach-Object { (Join-Path $taskRoot "runtime\$_") -replace '\\', '/' }) -join ';'
$taskArgs = @('-S', (Join-Path $taskRoot 'upstream'), '-B', $taskBuild, '-G', 'Ninja',
    "-DCMAKE_MAKE_PROGRAM=$(Join-Path $CMakeRoot 'Ninja\ninja.exe')",
    "-DCMAKE_C_COMPILER=$(Join-Path $taskBin "$Target-w64-mingw32-clang.exe")",
    "-DCMAKE_CXX_COMPILER=$(Join-Path $taskBin "$Target-w64-mingw32-clang++.exe")",
    '-DCMAKE_BUILD_TYPE=Release', '-DWWHD_BUNDLED_DEPS=ON',
    "-DCMAKE_C_FLAGS=$taskFlags", "-DCMAKE_CXX_FLAGS=$taskFlags",
    "-DGEN_DIR=$((Join-Path $taskRoot 'build\gen') -replace '\\', '/')",
    "-DCT_EXTRA_SOURCES=$taskExtra",
    "-DVulkan_INCLUDE_DIR=$VulkanInclude", "-DVulkan_LIBRARY=$VulkanLibrary")
if ($DependencySources) {
    foreach ($taskDep in @('GLSLANG:glslang-src', 'SDL3:sdl3-src', 'ZLIB:zlib-src', 'LZ4:lz4-src')) {
        $taskName, $taskDir = $taskDep -split ':'
        $taskArgs += "-DFETCHCONTENT_SOURCE_DIR_$taskName=$(Join-Path $DependencySources $taskDir)"
    }
}
& (Join-Path $CMakeRoot 'CMake\bin\cmake.exe') @taskArgs
if ($LASTEXITCODE -ne 0) { throw 'Game runtime configuration failed' }
& (Join-Path $CMakeRoot 'CMake\bin\cmake.exe') --build $taskBuild --target wwhd --parallel $Jobs
if ($LASTEXITCODE -ne 0) { throw 'Game runtime compilation failed' }
foreach ($taskDll in @('libc++.dll', 'libunwind.dll')) {
    Copy-Item -LiteralPath (Join-Path $LlvmMingw "$Target-w64-mingw32\bin\$taskDll") -Destination $taskBuild -Force
}
Write-Output "Built $(Join-Path $taskBuild 'wwhd.exe'). Run it with --game <prepared game folder>."
