param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
function Invoke-Checked([string]$Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Exe failed: $LASTEXITCODE" }
}
$lock = Get-Content -LiteralPath "$root\dependencies.lock.json" -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path "$root\third_party" -Force | Out-Null
foreach ($name in @('ps1-recomp','psxrecomp')) {
    $dep = $lock.$name
    $repo = Join-Path "$root\third_party" $name
    if (-not (Test-Path -LiteralPath $repo)) {
        Invoke-Checked 'git' @('clone','--no-checkout',$dep.url,$repo)
        Invoke-Checked 'git' @('-C',$repo,'checkout','--detach',$dep.commit)
    }
    $actual = & git -C $repo rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $actual -ne $dep.commit) { throw "Unexpected revision in $repo; leaving it untouched" }
    if ($dep.submodules.Count) {
        Invoke-Checked 'git' (@('-C',$repo,'submodule','update','--init','--recursive','--') + @($dep.submodules))
    }
}
$zip = Join-Path $root 'third_party\toolchain.zip'
if (-not (Test-Path -LiteralPath $zip)) { Invoke-WebRequest -Uri $lock.toolchain.url -OutFile $zip }
if ((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $lock.toolchain.sha256) { throw 'Toolchain checksum mismatch' }
if (-not (Test-Path -LiteralPath "$root\third_party\toolchain\bin\clang.exe")) {
    Expand-Archive -LiteralPath $zip -DestinationPath "$root\third_party\toolchain"
}
if (-not (Test-Path -LiteralPath "$root\.venv\Scripts\python.exe")) { Invoke-Checked $Python @('-m','venv',"$root\.venv") }
Invoke-Checked "$root\.venv\Scripts\python.exe" @('-m','pip','install','-r',"$root\requirements-dev.txt")
Write-Host 'Dependencies ready. No system PATH or system installation changed.'
