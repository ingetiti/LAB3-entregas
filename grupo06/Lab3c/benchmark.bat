@echo off
setlocal
cd /d "%~dp0"
if not exist build\benchmark.exe (
    call compilar.bat
    if errorlevel 1 exit /b 1
)
build\simulador.exe build\calculadora_automatica.obj --max-instructions 2000000
if errorlevel 1 exit /b 1
build\benchmark.exe build\funciones.obj build\benchmark.csv
if errorlevel 1 exit /b 1
pause
