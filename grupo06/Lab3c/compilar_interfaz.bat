@echo off
setlocal
cd /d "%~dp0"
where gcc >nul 2>nul
if errorlevel 1 (
    echo Se necesita GCC en PATH, por ejemplo MinGW-w64 de MSYS2.
    exit /b 1
)
where windres >nul 2>nul
if errorlevel 1 (
    echo Se necesita windres, incluido en MinGW-w64 de MSYS2.
    exit /b 1
)
if not exist build mkdir build
set "FLAGS=-std=c11 -O2 -static -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror -Iinclude -Isrc -Ibuild"
set "ASM=src\assembler.c src\linker.c src\image.c"
if not exist build\ensamblador.exe (
    gcc %FLAGS% %ASM% src\assembler_main.c -o build\ensamblador.exe
    if errorlevel 1 exit /b 1
)
if not exist build\os_image.h (
    build\ensamblador.exe ejemplos\sistema.asm -o build\sistema.obj --emit-c build\os_image.h
    if errorlevel 1 exit /b 1
)
build\ensamblador.exe benchmark\calculadora.asm -I benchmark\modulos -o build\calculadora.obj
if errorlevel 1 exit /b 1
windres -Iresources resources\isa3c.rc -o build\isa3c_resources.o
if errorlevel 1 exit /b 1
gcc %FLAGS% -municode -mwindows %ASM% src\lc3.c src\os.c src\gui_session.c src\gui_editor.c src\gui_win32.c build\isa3c_resources.o -lcomctl32 -lcomdlg32 -lshell32 -lole32 -lgdi32 -ldwmapi -luuid -o build\isa3c_gui.exe
if errorlevel 1 exit /b 1
gcc %FLAGS% %ASM% src\lc3.c src\os.c src\gui_session.c tests\test_gui_session.c -o build\test_gui_session.exe
if errorlevel 1 exit /b 1
build\test_gui_session.exe . build\gui_prueba.obj
if errorlevel 1 exit /b 1
gcc %FLAGS% src\gui_editor.c tests\test_gui_editor.c -lcomctl32 -o build\test_gui_editor.exe
if errorlevel 1 exit /b 1
build\test_gui_editor.exe
if errorlevel 1 exit /b 1

echo Interfaz lista. Abrir interfaz.bat.
exit /b 0
