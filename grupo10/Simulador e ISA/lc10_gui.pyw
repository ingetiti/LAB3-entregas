"""Abre la ventana del LC10 (editor + ensamblador + simulador).

Windows: doble clic en este archivo (o arrastrar archivos .asm encima).
Cualquier sistema:  python lc10_gui.pyw [programa.asm [modulo.asm ...]]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lc10.gui import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
