param([ValidateSet('tools','config','analyze','generate','build','all')][string]$Step = 'all', [switch]$Release, [switch]$Strict, [switch]$PCInput)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$argsList = @("$root\tools\pipeline.py", $Step)
if ($Release) { $argsList += '--release' }
if ($Strict) { $argsList += '--strict' }
if ($PCInput) { $argsList += '--pc-input' }
& "$root\.venv\Scripts\python.exe" @argsList
if ($LASTEXITCODE -ne 0) { throw "Pipeline failed: $LASTEXITCODE" }
