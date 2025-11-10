@echo off
REM Script para descargar el modelo YOLO antes de construir Docker
REM Uso: download-model.bat

echo ============================================================
echo   Descargador de Modelo YOLO para Docker
echo ============================================================
echo.

echo Descargando modelo YOLO...
python download_model.py

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo   Modelo descargado exitosamente
    echo ============================================================
    echo.
    echo Ahora puedes construir la imagen Docker con:
    echo   docker compose build
    echo.
) else (
    echo.
    echo ============================================================
    echo   El modelo se descargara durante el build de Docker
    echo ============================================================
    echo.
)

pause
