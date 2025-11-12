@echo off
echo ========================================
echo EMPAQUETANDO DETECTOR DE MOVIMIENTO
echo ========================================
echo.

echo [1/3] Empaquetando Flask con PyInstaller...
python -m PyInstaller app.spec --clean --noconfirm

if %errorlevel% neq 0 (
    echo.
    echo ERROR: PyInstaller fallo
    pause
    exit /b 1
)

echo.
echo [2/3] Creando carpeta backend...
if exist "electron\backend" rmdir /s /q "electron\backend"
mkdir "electron\backend"
xcopy /E /I /Y "dist\app\*" "electron\backend\"

echo.
echo [3/3] Empaquetando con Electron...
call npm run package

echo.
echo ========================================
echo COMPLETADO
echo ========================================
echo.
echo Instalador creado en: dist\
echo.
pause
