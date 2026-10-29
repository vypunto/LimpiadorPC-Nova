@echo off
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw -3 limpiador.py & exit /b)
where pythonw >nul 2>nul && (start "" pythonw limpiador.py & exit /b)
where py >nul 2>nul && (py -3 limpiador.py & exit /b)
python limpiador.py
if errorlevel 1 (
  echo No se pudo iniciar. Instala Python 3 desde https://www.python.org/downloads/
  pause
)
