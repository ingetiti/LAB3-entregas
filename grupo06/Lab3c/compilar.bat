@echo off
setlocal
cd /d "%~dp0"
where gcc >nul 2>nul
if errorlevel 1 (
    echo Se necesita GCC en PATH, por ejemplo MinGW-w64 de MSYS2.
    exit /b 1
)
if not exist build mkdir build
set "FLAGS=-std=c11 -O2 -static -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror -Iinclude -Isrc -Ibuild"
set "ASM=src\assembler.c src\linker.c src\image.c"
set "CPU=src\lc3.c src\os.c src\image.c"
echo Compilando ensamblador independiente...
gcc %FLAGS% %ASM% src\assembler_main.c -o build\ensamblador.exe
if errorlevel 1 exit /b 1
build\ensamblador.exe ejemplos\sistema.asm -o build\sistema.obj --emit-c build\os_image.h
if errorlevel 1 exit /b 1
echo Compilando nucleo y entorno de desarrollo...
gcc %FLAGS% %CPU% src\console.c src\simulator_main.c -o build\simulador.exe
if errorlevel 1 exit /b 1
gcc %FLAGS% %ASM% src\lc3.c src\os.c src\console.c src\main.c -o build\lc3.exe
if errorlevel 1 exit /b 1
echo Compilando pruebas...
gcc %FLAGS% %ASM% src\lc3.c src\os.c tests\test_isa.c -o build\lc3_tests.exe
if errorlevel 1 exit /b 1
gcc %FLAGS% %CPU% tests\benchmark.c -o build\benchmark.exe
if errorlevel 1 exit /b 1
gcc %FLAGS% %CPU% tests\test_calculadora.c -o build\test_calculadora.exe
if errorlevel 1 exit /b 1
gcc %FLAGS% %CPU% tests\test_exp_exhaustive.c -lm -o build\test_exp_exhaustive.exe
if errorlevel 1 exit /b 1
gcc %FLAGS% %ASM% src\lc3.c src\os.c tests\test_exp_optimized.c -lm -o build\test_exp_optimized.exe
if errorlevel 1 exit /b 1
for %%P in (funciones calculadora calculadora_automatica) do (
    build\ensamblador.exe benchmark\%%P.asm -I benchmark\modulos -o build\%%P.obj
    if errorlevel 1 exit /b 1
)
gcc %FLAGS% %CPU% tests\test_shift_exhaustive.c -o build\test_shift_exhaustive.exe
if errorlevel 1 exit /b 1
gcc %FLAGS% %ASM% src\lc3.c src\os.c tests\test_alu_extended.c -o build\test_alu_extended.exe
if errorlevel 1 exit /b 1
gcc %FLAGS% %ASM% src\lc3.c src\os.c tests\test_sqrt_equivalence.c -o build\test_sqrt_equivalence.exe
if errorlevel 1 exit /b 1
build\ensamblador.exe ejemplos\alu_integrada.asm -o build\alu_integrada.obj
if errorlevel 1 exit /b 1
build\ensamblador.exe ejemplos\exp_isa3c.asm -I benchmark\modulos -o build\exp_isa3c.obj
if errorlevel 1 exit /b 1
call compilar_interfaz.bat
if errorlevel 1 exit /b 1
call probar.bat
if errorlevel 1 exit /b 1
echo Listo. Interfaz grafica: interfaz.bat. Consola: editor.bat. Calculadora: ejecutar.bat.
exit /b 0
