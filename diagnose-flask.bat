@echo off
REM Script de diagnóstico para Flask
title Diagnostico de Flask

setlocal
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

echo ====================================
echo Diagnostico de Flask
echo ====================================
echo.

REM Crear carpeta de logs
if not exist "%BASE_DIR%logs" mkdir "%BASE_DIR%logs"
set "LOGFILE=%BASE_DIR%logs\flask-diagnostics.log"

REM Detectar Python
set "PY_PORTABLE=%BASE_DIR%python-portable"
set "PY_EXE=%PY_PORTABLE%\python.exe"
set "PYW_EXE=%PY_PORTABLE%\pythonw.exe"

if exist "%PYW_EXE%" (
    set "PYTHON_CMD=%PYW_EXE%"
) else if exist "%PY_EXE%" (
    set "PYTHON_CMD=%PY_EXE%"
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python no encontrado
    pause
    exit /b 1
)

echo [INFO] Python: %PYTHON_CMD%
echo [INFO] Verificando dependencias...
echo.

REM Verificar Flask
"%PYTHON_CMD%" -c "import flask; print('OK: Flask ' + flask.__version__)" 1>>"%LOGFILE%" 2>&1
if !errorlevel! equ 0 (
    echo [OK] Flask instalado
) else (
    echo [ERROR] Flask no esta instalado
    pause
    exit /b 1
)

REM Verificar que el puerto 5000 no esta en uso
echo [INFO] Verificando puerto 5000...
netstat -an | find ":5000" > nul
if !errorlevel! equ 0 (
    echo [ADVERTENCIA] Puerto 5000 ya esta en uso
) else (
    echo [OK] Puerto 5000 disponible
)

REM Intentar iniciar Flask
echo.
echo [INFO] Iniciando Flask en modo diagnostico...
echo [INFO] Log en: %LOGFILE%
echo.
echo (Presiona Ctrl+C para detener)
echo.

"%PYTHON_CMD%" -u app.py >> "%LOGFILE%" 2>&1

endlocal
