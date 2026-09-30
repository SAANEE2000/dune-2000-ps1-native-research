@echo off
setlocal
echo Strict AOT diagnostic: unresolved native coverage exits with code 86.
echo This is not yet a playable native-only release. Use RunPCInput.cmd to play the research build.
cd /d "%~dp0build\strict"
set "PATH=%~dp0third_party\toolchain\bin;%PATH%"
"Dune2000Native.exe" --game "%~dp0game.toml" --disc "%~dp0generated\assets\disc.cue" --renderer software
