@echo off
REM Script para ejecutar la app Flask con configuración de proxy
REM Nginx reescribe las rutas automáticamente, no necesitamos prefijo en Flask

echo ============================================
echo   Iniciando App Flask (Configuración Proxy)
echo ============================================
echo.
echo Modo: Proxy con reescritura de rutas (Nginx)
echo Puerto: 5000
echo.

REM Ejecutar la aplicación sin prefijo (Nginx lo maneja)
python run.py

pause
