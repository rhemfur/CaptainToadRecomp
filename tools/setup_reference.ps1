param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskReference = Join-Path $taskRoot 'upstream'
$taskCommit = 'defb89f21607345e2e97b2c145a071a3f362640c'
if (-not (Test-Path -LiteralPath $taskReference)) {
    & git init $taskReference
    if ($LASTEXITCODE -ne 0) { throw 'Could not initialize reference checkout' }
    & git -C $taskReference remote add origin https://github.com/ZeldaWWHDRecomp/ZeldaWWHDRecomp.git
    if ($LASTEXITCODE -ne 0) { throw 'Could not configure reference remote' }
    & git -C $taskReference fetch --depth 1 origin $taskCommit
    if ($LASTEXITCODE -ne 0) { throw 'Could not fetch pinned reference commit' }
    & git -C $taskReference checkout --detach FETCH_HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Could not check out reference source' }
}
$taskActualCommit = & git -C $taskReference rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $taskActualCommit.Trim() -ne $taskCommit) {
    throw 'Existing reference has a different commit; review it before updating. No reset performed.'
}
& $Python (Join-Path $PSScriptRoot 'patch_reference.py') $taskReference
if ($LASTEXITCODE -ne 0) { throw 'Reference extension failed' }
& $Python (Join-Path $PSScriptRoot 'patch_diagnostic.py') $taskReference
if ($LASTEXITCODE -ne 0) { throw 'Strict diagnostic extension failed' }
Write-Output 'Pinned runtime/recompiler reference is ready. Supply your own extracted Captain Toad EUR files.'
