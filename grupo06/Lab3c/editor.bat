@echo off
setlocal
cd /d "%~dp0"
if not exist build\lc3.exe (
    call compilar.bat
    if errorlevel 1 exit /b 1
)
build\lc3.exe
