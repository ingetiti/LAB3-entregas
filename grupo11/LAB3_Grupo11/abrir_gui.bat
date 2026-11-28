@echo off
rem Abre la interfaz grafica del benchmark (doble clic). Requiere Python 3.10+ con tkinter (viene con el instalador oficial).
cd /d "%~dp0"
where pythonw >nul 2>nul && (start "" pythonw gui.py & goto :eof)
where pyw >nul 2>nul && (start "" pyw -3 gui.py & goto :eof)
python gui.py
pause
