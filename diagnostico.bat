@echo off
echo ================================================
echo   Diagnostico de Detector de Movimiento
echo ================================================
echo.

echo [1] Verificando Python...
python --version 2>nul
if errorlevel 1 (
    echo   ERROR: Python no encontrado
    echo   Instala Python desde: https://www.python.org/downloads/
) else (
    echo   OK: Python instalado
)

echo.
echo [2] Verificando Node.js...
node --version 2>nul
if errorlevel 1 (
    echo   ERROR: Node.js no encontrado
    echo   Instala Node.js desde: https://nodejs.org/
) else (
    echo   OK: Node.js instalado
)

echo.
echo [3] Verificando npm...
npm --version 2>nul
if errorlevel 1 (
    echo   ERROR: npm no encontrado
) else (
    echo   OK: npm instalado
)

echo.
echo [4] Verificando dependencias Python...
pip show flask 2>nul | find "Version" >nul
if errorlevel 1 (
    echo   ADVERTENCIA: Flask no instalado
    echo   Ejecuta: pip install -r requirements.txt
) else (
    echo   OK: Flask instalado
)

echo.
echo [5] Verificando dependencias Node...
if exist "node_modules\electron" (
    echo   OK: Electron instalado
) else (
    echo   ADVERTENCIA: Electron no instalado
    echo   Ejecuta: npm install
)

echo.
echo [6] Verificando archivos...
if exist "app.py" (
    echo   OK: app.py encontrado
) else (
    echo   ERROR: app.py no encontrado
)

if exist "electron\main.js" (
    echo   OK: electron\main.js encontrado
) else (
    echo   ERROR: electron\main.js no encontrado
)

echo.
echo [7] Probando Flask directamente...
echo   Iniciando Flask en modo prueba (presiona Ctrl+C para detener)...
timeout /t 2 /nobreak >nul
python app.py

echo.
echo ================================================
pause
