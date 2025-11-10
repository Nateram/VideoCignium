@echo off
echo ================================================
echo   Detector de Movimiento - Instalador
echo ================================================
echo.

echo [1/3] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado
    echo Por favor instala Python desde: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo OK: Python instalado

echo.
echo [2/3] Instalando dependencias de Python...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Fallo al instalar dependencias de Python
    pause
    exit /b 1
)

echo.
echo [3/3] Instalando dependencias de Node.js...
call npm install
if errorlevel 1 (
    echo ERROR: Fallo al instalar dependencias de Node.js
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Instalacion completada exitosamente!
echo ================================================
echo.
echo Para ejecutar la aplicacion usa:
echo   npm start
echo.
echo Para compilar el ejecutable usa:
echo   npm run build:win
echo.
pause
