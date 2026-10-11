param(
    [string]$AndroidSdk = 'C:\Android\Sdk',
    [string]$NdkVersion = '30.0.16248370',
    [string]$CMakeVersion = '4.1.2',
    # 'generic' runs on any arm64 phone; 'oryon-1' tunes for the Snapdragon 8 Elite (Galaxy S25)
    [string]$Cpu = 'generic',
    # JDK for Gradle: JAVA_HOME, else Android Studio's bundled runtime
    [string]$JavaHome = '',
    [int]$Jobs = 6,
    [string]$Python = 'python'
)
# Builds the reference game runtime with the locally generated Captain Toad code as the Android app's
# native library (libmain.so, as the reference's android/build_native.sh does), then a private APK.
# The APK contains recompiled game code: keep it on your own devices and never distribute it.
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskUpstream = Join-Path $taskRoot 'upstream'
$taskCMake = Join-Path $AndroidSdk "cmake\$CMakeVersion\bin\cmake.exe"
$taskNinja = Join-Path $AndroidSdk "cmake\$CMakeVersion\bin\ninja.exe"
$taskNdk = Join-Path $AndroidSdk "ndk\$NdkVersion"
$taskToolchain = Join-Path $taskNdk 'build\cmake\android.toolchain.cmake'
$taskLlvm = Join-Path $taskNdk 'toolchains\llvm\prebuilt\windows-x86_64'
foreach ($taskRequired in @($taskCMake, $taskNinja, $taskToolchain)) {
    if (-not (Test-Path -LiteralPath $taskRequired)) { throw "Missing tool: $taskRequired" }
}
& $Python (Join-Path $PSScriptRoot 'patch_runtime.py') $taskUpstream --gen (Join-Path $taskRoot 'build\gen')
if ($LASTEXITCODE -ne 0) { throw 'Runtime preparation failed' }

$taskBuild = Join-Path $taskRoot 'build\game-android'
# Strict HLE stops at the first missing import; foreign-guest mode keeps Wind Waker HD addresses out.
$taskFlags = '-DCT_DIAGNOSTIC_STRICT_HLE=1 -DCT_FOREIGN_GUEST=1'
if ($Cpu -ne 'generic') { $taskFlags += " -mcpu=$Cpu" }
$taskExtra = @('fast_mutex.cpp', 'mcp.cpp', 'reference_hle.cpp' | ForEach-Object { (Join-Path $taskRoot "runtime\$_") -replace '\\', '/' }) -join ';'
& $taskCMake -S $taskUpstream -B $taskBuild -G Ninja "-DCMAKE_MAKE_PROGRAM=$taskNinja" `
    "-DCMAKE_TOOLCHAIN_FILE=$taskToolchain" -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-33 `
    -DANDROID_STL=c++_shared -DCMAKE_BUILD_TYPE=Release -DWWHD_BUNDLED_DEPS=ON `
    "-DCMAKE_C_FLAGS=$taskFlags" "-DCMAKE_CXX_FLAGS=$taskFlags" `
    "-DGEN_DIR=$((Join-Path $taskRoot 'build\gen') -replace '\\', '/')" "-DCT_EXTRA_SOURCES=$taskExtra"
if ($LASTEXITCODE -ne 0) { throw 'Android game runtime configuration failed' }
& $taskCMake --build $taskBuild --target wwhd --parallel $Jobs
if ($LASTEXITCODE -ne 0) { throw 'Android game runtime compilation failed' }

$taskLibs = Join-Path $taskUpstream 'android\app\libs\arm64-v8a'
New-Item -ItemType Directory -Force -Path $taskLibs | Out-Null
& (Join-Path $taskLlvm 'bin\llvm-strip.exe') --strip-unneeded (Join-Path $taskBuild 'libmain.so') -o (Join-Path $taskLibs 'libmain.so')
if ($LASTEXITCODE -ne 0) { throw 'Stripping libmain.so failed' }
$taskSdl = Get-ChildItem -LiteralPath (Join-Path $taskBuild '_deps') -Recurse -Filter 'libSDL3.so' | Select-Object -First 1
if (-not $taskSdl) { throw 'libSDL3.so was not built' }
Copy-Item -LiteralPath $taskSdl.FullName -Destination $taskLibs -Force
Copy-Item -LiteralPath (Join-Path $taskLlvm 'sysroot\usr\lib\aarch64-linux-android\libc++_shared.so') -Destination $taskLibs -Force
# libadrenotools loads these hooks by soname from the app's native library folder
foreach ($taskHook in @('main_hook', 'hook_impl', 'file_redirect_hook', 'gsl_alloc_hook')) {
    $taskHookFile = Get-ChildItem -LiteralPath (Join-Path $taskBuild '_deps') -Recurse -Filter "lib$taskHook.so" | Select-Object -First 1
    if (-not $taskHookFile) { throw "Missing AdrenoTools hook: $taskHook" }
    Copy-Item -LiteralPath $taskHookFile.FullName -Destination $taskLibs -Force
}

if (-not $JavaHome) { $JavaHome = $env:JAVA_HOME }
if (-not $JavaHome) { $JavaHome = 'C:\Program Files\Android\Android Studio\jbr' }
if (-not (Test-Path -LiteralPath (Join-Path $JavaHome 'bin\java.exe'))) { throw "No JDK at $JavaHome; pass -JavaHome" }
$env:JAVA_HOME = $JavaHome
$env:ANDROID_HOME = $AndroidSdk
Push-Location (Join-Path $taskUpstream 'android')
try {
    & .\gradlew.bat assembleRelease
    if ($LASTEXITCODE -ne 0) { throw 'Gradle build failed' }
} finally { Pop-Location }
$taskApk = Join-Path $taskRoot 'build\game-android\captain-toad.apk'
Copy-Item -LiteralPath (Join-Path $taskUpstream 'android\app\build\outputs\apk\release\app-release.apk') -Destination $taskApk -Force
Write-Output "Built $taskApk (package org.ctrecomp.captaintoad). It contains recompiled game code: keep it private."
