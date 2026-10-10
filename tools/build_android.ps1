param(
    [string]$AndroidSdk = 'C:\Android\Sdk',
    [string]$NdkVersion = '30.0.16248370',
    [string]$CMakeVersion = '4.1.2',
    [int]$Jobs = 6
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskCMake = Join-Path $AndroidSdk "cmake\$CMakeVersion\bin\cmake.exe"
$taskNinja = Join-Path $AndroidSdk "cmake\$CMakeVersion\bin\ninja.exe"
$taskToolchain = Join-Path $AndroidSdk "ndk\$NdkVersion\build\cmake\android.toolchain.cmake"
foreach ($taskRequired in @($taskCMake, $taskNinja, $taskToolchain)) {
    if (-not (Test-Path -LiteralPath $taskRequired)) { throw "Missing tool: $taskRequired" }
}
$taskBuild = Join-Path $taskRoot 'build\android-gamecode'
& $taskCMake -S $taskRoot -B $taskBuild -G Ninja "-DCMAKE_MAKE_PROGRAM=$taskNinja" `
    "-DCMAKE_TOOLCHAIN_FILE=$taskToolchain" -DANDROID_ABI=arm64-v8a `
    -DANDROID_PLATFORM=android-33 -DANDROID_STL=c++_shared -DCMAKE_BUILD_TYPE=Release
if ($LASTEXITCODE -ne 0) { throw 'Android CMake configuration failed' }
& $taskCMake --build $taskBuild --parallel $Jobs
if ($LASTEXITCODE -ne 0) { throw 'Android game-code compilation failed' }
Write-Output 'ARM64 library and boot diagnostic compiled. The diagnostic is headless; no game renderer or APK yet.'
