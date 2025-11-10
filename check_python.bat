@echo off
echo ================================================
echo   Verificando Python y dependencias
echo ================================================
echo.

echo [1/4] Buscando Python...
python --version 2>nul
if %errorlevel% equ 0 (
    echo OK: python encontrado
    python --version
) else (
    py --version 2>nul
    if %errorlevel% equ 0 (
        echo OK: py encontrado
        py --version
    ) else (
        echo ERROR: Python no encontrado
        echo Instala Python desde: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

echo.
echo [2/4] Verificando Flask...
python -c "import flask; print('Flask version:', flask.__version__)" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Flask no instalado
    echo Ejecuta: pip install -r requirements.txt
    pause
    exit /b 1
)
echo OK: Flask instalado

echo.
echo [3/4] Verificando OpenCV...
python -c "import cv2; print('OpenCV version:', cv2.__version__)" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: OpenCV no instalado
    echo Ejecuta: pip install -r requirements.txt
    pause
    exit /b 1
)
echo OK: OpenCV instalado

echo.
echo [4/4] Verificando app.py...
if not exist app.py (
    echo ERROR: app.py no encontrado
    pause
    exit /b 1
)
echo OK: app.py encontrado

echo.
echo ================================================
echo   Todo listo! Puedes ejecutar:
echo   npm start
echo ================================================
pause
