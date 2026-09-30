@echo off
setlocal
cd /d "%~dp0build\pc"
set "PATH=%~dp0third_party\toolchain\bin;%PATH%"
set "DUNE_INPUT_CONFIG=%~dp0config\input.ini"
"Dune2000Native.exe" --game "%~dp0game.toml" --disc "%~dp0generated\assets\disc.cue" --renderer software --debug-port 0
