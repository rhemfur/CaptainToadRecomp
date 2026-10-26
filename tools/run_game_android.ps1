param(
    [string]$Serial,
    # copy the prepared game tree to the phone (once, or after preparing it again)
    [switch]$PushGame,
    [int]$LogSeconds = 60,
    [string]$AndroidSdk = 'C:\Android\Sdk'
)
# Installs the private Captain Toad APK on one phone, optionally copies the game files into the app's
# folder (Android/data/org.ctrecomp.captaintoad/files/game), starts it and saves its log locally.
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPackage = 'org.ctrecomp.captaintoad'
$taskDeviceFile = Join-Path $taskRoot 'local-reports\device-target.json'
if (-not $Serial -and (Test-Path -LiteralPath $taskDeviceFile)) {
    $Serial = (Get-Content -LiteralPath $taskDeviceFile -Raw | ConvertFrom-Json).adb_serial
}
if (-not $Serial) { throw 'Provide -Serial from adb devices. Device identifiers are kept local.' }
$taskAdb = Join-Path $AndroidSdk 'platform-tools\adb.exe'
$taskApk = Join-Path $taskRoot 'build\game-android\captain-toad.apk'
foreach ($taskPath in @($taskAdb, $taskApk)) {
    if (-not (Test-Path -LiteralPath $taskPath)) { throw "Missing file: $taskPath" }
}
function Invoke-CtAdb {
    & $taskAdb -s $Serial @args
    if ($LASTEXITCODE -ne 0) { throw "adb $($args[0]) failed, exit $LASTEXITCODE" }
}
Invoke-CtAdb get-state
Invoke-CtAdb install -r $taskApk
$taskFiles = "/sdcard/Android/data/$taskPackage/files"
if ($PushGame) {
    $taskRpx = Join-Path $taskRoot 'game\code\Kinopio.rpx'
    $taskSha = (Get-FileHash -LiteralPath $taskRpx -Algorithm SHA256).Hash.ToLower()
    $taskProfiles = Get-ChildItem -LiteralPath (Join-Path $taskRoot 'profiles') -Filter '*.json' |
        ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json }
    if (-not ($taskProfiles | Where-Object { $_.rpx_sha256 -eq $taskSha })) {
        throw 'RPX matches no Captain Toad profile'
    }
    Invoke-CtAdb shell mkdir -p "$taskFiles/game"
    foreach ($taskDir in @('code', 'content', 'meta')) {
        Invoke-CtAdb push (Join-Path $taskRoot "game\$taskDir") "$taskFiles/game/"
    }
}
if ($PushGame) {
    # adb writes as the shell user into folders only that user and ext_data_rw may open: let the app read them
    Invoke-CtAdb shell chmod -R 777 "$taskFiles/game"
}
Invoke-CtAdb logcat -c
Invoke-CtAdb shell monkey -p $taskPackage -c android.intent.category.LAUNCHER 1
Start-Sleep -Seconds $LogSeconds
$taskLog = Join-Path $taskRoot 'local-reports\android-game.log'
& $taskAdb -s $Serial logcat -d -s wwhd SDL AndroidRuntime DEBUG > $taskLog
Write-Output "Log saved to $taskLog (adb logcat -s wwhd). The runtime also writes $taskFiles/captures/captain-toad.log."
