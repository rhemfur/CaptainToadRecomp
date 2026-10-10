param(
    [string]$ClangRoot = 'C:\msys64\clang64',
    [string]$CMakeBin = 'C:\Android\Sdk\cmake\4.1.2\bin',
    [int]$Jobs = 6
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskBuild = Join-Path $taskRoot 'build\windows-diagnostic'
$env:PATH = (Join-Path $ClangRoot 'bin') + ';' + $env:PATH
& (Join-Path $CMakeBin 'cmake.exe') -S $taskRoot -B $taskBuild -G Ninja `
    "-DCMAKE_MAKE_PROGRAM=$(Join-Path $CMakeBin 'ninja.exe')" `
    "-DCMAKE_C_COMPILER=$(Join-Path $ClangRoot 'bin\clang.exe')" `
    "-DCMAKE_CXX_COMPILER=$(Join-Path $ClangRoot 'bin\clang++.exe')" `
    "-DZLIB_ROOT=$ClangRoot" -DCMAKE_BUILD_TYPE=Release
if ($LASTEXITCODE -ne 0) { throw 'Windows configuration failed' }
& (Join-Path $CMakeBin 'cmake.exe') --build $taskBuild --target ct-diagnostic --parallel $Jobs
if ($LASTEXITCODE -ne 0) { throw 'Windows diagnostic compilation failed' }
& (Join-Path $CMakeBin 'ctest.exe') --test-dir $taskBuild --output-on-failure
if ($LASTEXITCODE -ne 0) { throw 'Runtime tests failed' }
