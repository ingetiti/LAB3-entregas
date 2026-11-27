#!/bin/bash
# Traduce el benchmark de la cátedra a LC10, lo ensambla y lo ejecuta (Linux o macOS; en Windows usar los
# comandos de abajo uno por uno).
#   uso: tools/run_port.sh RUTA/lc3-project DIR_SALIDA [--solo archivo.asm ...]
set -e
cd "$(dirname "$0")/.."
if [ $# -lt 2 ]; then
    echo "uso: tools/run_port.sh RUTA/lc3-project DIR_SALIDA [--solo archivo.asm ...]" >&2
    exit 1
fi
LC3="$1"; G="$2"; shift 2
python3 tools/lc3_to_lc10.py "$LC3" -o "$G" "$@" | tail -2
python3 -m lc10.assembler "$G/main_grupo27.asm" $(ls "$G"/*.asm | grep -v main_grupo27) -o "$G/p.bin" | head -1
python3 -m lc10.simulator "$G/p.bin" --max 3000000 > "$G/out.txt" 2> "$G/err.txt" || true
tail -n 6 "$G/out.txt"
