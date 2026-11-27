@echo off
setlocal
cd /d "%~dp0"
if not exist "build\isa3c_gui.exe" (
    echo Falta compilar la interfaz. Ejecute compilar_interfaz.bat.
    pause
    exit /b 1
)
start "" "build\isa3c_gui.exe"
exit /b 0
