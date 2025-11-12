@echo off
title Detector de Movimiento
cd /d "%~dp0"

echo ========================================
echo  Detector de Movimiento
echo ========================================
echo.

REM Verificar si Node.js está instalado
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js no encontrado
    echo Por favor instala Node.js desde: https://nodejs.org/
    pause
    exit /b 1
)

REM Verificar si Python está instalado
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python no encontrado
    echo Por favor instala Python desde: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Verificar dependencias de Node
if not exist "node_modules\" (
    echo Instalando dependencias de Node.js...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Fallo al instalar dependencias de Node.js
        pause
        exit /b 1
    )
)

REM Verificar dependencias de Python
python -c "import flask" >nul 2>nul
if %errorlevel% neq 0 (
    echo Instalando dependencias de Python...
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Fallo al instalar dependencias de Python
        pause
        exit /b 1
    )
)

echo.
echo Iniciando aplicacion...
echo.

REM Iniciar Electron
npm start

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] La aplicacion se cerro inesperadamente
    pause
)
