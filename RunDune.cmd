@echo off
setlocal
cd /d "%~dp0build\native"
set "PATH=%~dp0third_party\toolchain\bin;%PATH%"
"Dune2000Native.exe" --game "%~dp0game.toml" --disc "%~dp0generated\assets\disc.cue" --renderer software
