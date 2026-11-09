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
# A locked screen pauses the activity at once, and Samsung's process freezer then stops the game.
Invoke-CtAdb shell input keyevent KEYCODE_WAKEUP
if ((& $taskAdb -s $Serial shell dumpsys window) -match 'isKeyguardShowing=true') {
    throw 'The phone is locked: unlock it, keep the screen on and run this script again'
}
Invoke-CtAdb shell am force-stop $taskPackage
# On Android the runtime writes captures/captain-toad.log only when env.txt (read at startup) asks for it,
# and a path given there must already have its folder.
Invoke-CtAdb shell mkdir -p "$taskFiles/captures"
& $taskAdb -s $Serial shell "test -e $taskFiles/env.txt || echo WWHD_LOG_FILE=captures/captain-toad.log > $taskFiles/env.txt"
Invoke-CtAdb logcat -c
Invoke-CtAdb shell monkey -p $taskPackage -c android.intent.category.LAUNCHER 1
Start-Sleep -Seconds $LogSeconds
$taskLog = Join-Path $taskRoot 'local-reports\android-game.log'
# Windows PowerShell's > writes UTF-16; keep the log UTF-8 like the runtime's own.
& $taskAdb -s $Serial logcat -d -s wwhd SDL AndroidRuntime DEBUG | Out-File -LiteralPath $taskLog -Encoding utf8
$taskRuntimeLog = Join-Path $taskRoot 'local-reports\android-wwhd.log'
& $taskAdb -s $Serial pull "$taskFiles/captures/captain-toad.log" $taskRuntimeLog
if ($LASTEXITCODE -ne 0) { Write-Warning "The runtime has not written $taskFiles/captures/captain-toad.log" }
Write-Output "Logs saved to $taskLog (adb logcat -s wwhd) and $taskRuntimeLog (captures/captain-toad.log)."
