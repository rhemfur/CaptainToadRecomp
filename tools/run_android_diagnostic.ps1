param(
    [string]$Serial,
    [ValidateSet('SelfTest','Mutex','Filesystem','System','Vulkan','Verify','Boot')]
    [string]$Mode = 'Boot',
    [string]$AndroidSdk = 'C:\Android\Sdk',
    [string]$NdkVersion = '30.0.16248370'
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskDeviceFile = Join-Path $taskRoot 'local-reports\device-target.json'
if (-not $Serial -and (Test-Path -LiteralPath $taskDeviceFile)) {
    $Serial = (Get-Content -LiteralPath $taskDeviceFile -Raw | ConvertFrom-Json).adb_serial
}
if (-not $Serial) { throw 'Provide -Serial from adb devices. Device identifiers are kept local.' }
$taskAdb = Join-Path $AndroidSdk 'platform-tools\adb.exe'
$taskBinary = Join-Path $taskRoot 'build\android-gamecode\ct-diagnostic'
$taskCpp = Join-Path $AndroidSdk "ndk\$NdkVersion\toolchains\llvm\prebuilt\windows-x86_64\sysroot\usr\lib\aarch64-linux-android\libc++_shared.so"
$taskRemote = '/data/local/tmp/captain-toad'
function Invoke-CtAdb {
    & $taskAdb -s $Serial @args
    if ($LASTEXITCODE -ne 0) { throw "ADB preparation failed, exit $LASTEXITCODE" }
}
foreach ($taskPath in @($taskAdb,$taskBinary,$taskCpp)) {
    if (-not (Test-Path -LiteralPath $taskPath)) { throw "Missing file: $taskPath" }
}
Invoke-CtAdb get-state
Invoke-CtAdb shell mkdir -p "$taskRemote/code"
Invoke-CtAdb push $taskBinary "$taskRemote/ct-diagnostic"
Invoke-CtAdb push $taskCpp "$taskRemote/libc++_shared.so"
Invoke-CtAdb shell chmod 755 "$taskRemote/ct-diagnostic"
if ($Mode -in @('Verify','Boot')) {
    $taskRpx = Join-Path $taskRoot 'game\code\Kinopio.rpx'
    $taskProfile = Get-Content -LiteralPath (Join-Path $taskRoot 'profiles\captain-toad-eur-v16.json') -Raw | ConvertFrom-Json
    if ((Get-FileHash -LiteralPath $taskRpx -Algorithm SHA256).Hash.ToLower() -ne $taskProfile.rpx_sha256) {
        throw 'RPX does not match the Captain Toad EUR v16 profile'
    }
    Invoke-CtAdb push $taskRpx "$taskRemote/code/Kinopio.rpx"
}
$taskOptions = switch ($Mode) {
    SelfTest { '--self-test' }
    Mutex { '--mutex-self-test' }
    Filesystem { "--fs-self-test $taskRemote/fs-fixture" }
    System { '--system-self-test' }
    Vulkan { '--vulkan-probe' }
    Verify { "--game $taskRemote --verify-only" }
    Boot { "--game $taskRemote --seconds 10" }
}
$taskReportDir = Join-Path $taskRoot 'local-reports'
New-Item -ItemType Directory -Path $taskReportDir -Force | Out-Null
$taskLog = Join-Path $taskReportDir ("android-{0}-{1}.log" -f $Mode.ToLower(),(Get-Date -Format 'yyyyMMdd-HHmmss'))
# Windows PowerShell 5 treats native stderr as ErrorRecords even on successful diagnostics.
# Capture both native streams in Python so the actual exit code controls the result.
& python -c "import subprocess,sys; log=open(sys.argv[1],'wb'); result=subprocess.run(sys.argv[2:],stdout=log,stderr=subprocess.STDOUT); log.close(); sys.exit(result.returncode)" `
    $taskLog $taskAdb -s $Serial shell "LD_LIBRARY_PATH=$taskRemote $taskRemote/ct-diagnostic $taskOptions"
$taskRunExit = $LASTEXITCODE
Get-Content -LiteralPath $taskLog
Write-Output "Diagnostic exit=$taskRunExit. Exit 78 identifies an unsupported API; 124 is the diagnostic deadline."
if ($taskRunExit -eq 0) { exit 0 }
if ($Mode -eq 'Boot' -and $taskRunExit -eq 78) { exit 78 }
throw "Diagnostic failed, exit $taskRunExit; see $taskLog"
