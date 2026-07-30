@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0build_and_package.ps1" %*
exit /b %errorlevel%
