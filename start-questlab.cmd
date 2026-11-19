@echo off
setlocal
rem Double-click/terminal entry point for the guarded WSL launcher.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-questlab.ps1" %*
exit /b %ERRORLEVEL%
