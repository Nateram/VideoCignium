@echo off
title Detector de Movimiento
cd /d "%~dp0"

echo ========================================
echo  DETECTOR DE MOVIMIENTO - PORTABLE
echo ========================================
echo.

REM Detectar si estamos usando Python portable o Python del sistema
set PYTHON_CMD=python
set PORTABLE_PYTHON=%~dp0python-portable\python.exe

if exist "%PORTABLE_PYTHON%" (
    echo [OK] Usando Python portable incluido
    set PYTHON_CMD=%PORTABLE_PYTHON%
    echo      Version: Python 3.11.9 Embebido
) else (
    echo [INFO] Python portable no encontrado, usando Python del sistema
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python no esta instalado
        echo.
        echo Por favor instala Python desde: https://www.python.org/
        pause
        exit /b 1
    )
    echo [OK] Python del sistema encontrado
)

REM Verificar Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js no esta instalado
    echo.
    echo Por favor instala Node.js desde: https://nodejs.org/
    pause
    exit /b 1
)

echo [OK] Node.js encontrado
echo.

REM Verificar e instalar dependencias de npm si es necesario
if not exist "node_modules\" (
    echo Instalando dependencias de Node.js...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Fallo al instalar dependencias de Node.js
        pause
        exit /b 1
    )
) else (
    echo [OK] Dependencias de Node.js instaladas
)

REM Si usamos Python portable, las dependencias ya estan instaladas
if exist "%PORTABLE_PYTHON%" (
    echo [OK] Dependencias de Python incluidas en version portable
) else (
    echo Verificando dependencias de Python...
    "%PYTHON_CMD%" -c "import flask" >nul 2>&1
    if %errorlevel% neq 0 (
        echo Instalando dependencias de Python (esto puede tardar varios minutos)...
        "%PYTHON_CMD%" -m pip install -r requirements.txt
        if %errorlevel% neq 0 (
            echo [ERROR] Fallo al instalar dependencias de Python
            pause
            exit /b 1
        )
    ) else (
        echo [OK] Dependencias de Python instaladas
    )
)

echo.
echo ========================================
echo  Iniciando aplicacion...
echo ========================================
echo.

REM Configurar variable de entorno para que Electron use el Python correcto
set PYTHON_PATH=%PYTHON_CMD%

REM Iniciar Electron
npm start

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] La aplicacion se cerro inesperadamente
    pause
)
