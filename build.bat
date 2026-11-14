@echo off
rem Birdman64 HD texture pack builder.
rem Put your own Pilotwings 64 ROM (.z64/.n64/.v64/.zip) in the "rom" folder,
rem then double-click this file. Everything else is automatic.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\bootstrap.ps1" %*
echo.
pause
