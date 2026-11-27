@echo off
setlocal
cd /d "%~dp0"
if not exist build\test_exp_exhaustive.exe (
    call compilar.bat
    exit /b
)
build\lc3_tests.exe
if errorlevel 1 exit /b 1
build\benchmark.exe build\funciones.obj build\benchmark.csv
if errorlevel 1 exit /b 1
build\test_calculadora.exe build\calculadora_automatica.obj build\calculadora.obj
if errorlevel 1 exit /b 1
build\test_exp_exhaustive.exe build\funciones.obj
if errorlevel 1 exit /b 1
build\test_exp_optimized.exe tests\exp_previa\principal.asm tests\exp_actual.asm build\exp_comparacion.csv build\exp_optimizacion.json
if errorlevel 1 exit /b 1
build\test_shift_exhaustive.exe
if errorlevel 1 exit /b 1
build\test_alu_extended.exe
if errorlevel 1 exit /b 1
build\test_sqrt_equivalence.exe benchmark\funciones.asm benchmark\modulos build\sqrt_integrada.bin tests\sqrt_reference.bin
if errorlevel 1 exit /b 1
if not exist build\test_gui_session.exe (
    call compilar_interfaz.bat
    if errorlevel 1 exit /b 1
)
build\test_gui_session.exe . build\gui_prueba.obj
if errorlevel 1 exit /b 1
if not exist build\test_gui_editor.exe (
    call compilar_interfaz.bat
    if errorlevel 1 exit /b 1
)
build\test_gui_editor.exe
if errorlevel 1 exit /b 1
exit /b 0
