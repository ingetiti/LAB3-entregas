@echo off
setlocal
cd /d "%~dp0"
if not exist build\simulador.exe (
    call compilar.bat
    if errorlevel 1 exit /b 1
)
build\simulador.exe build\calculadora.obj --max-instructions 10000000
pause
