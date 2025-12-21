@echo off
REM Script para iniciar Flask de manera más robusta
REM Se ejecuta desde launch.bat

setlocal enabledelayedexpansion

set "BASE_DIR=%~1"
set "LOGFILE=%~2"
set "PYTHON_CMD=%~3"

if "!BASE_DIR!"=="" (
    echo [ERROR] BASE_DIR no proporcionado
    exit /b 1
)

cd /d "!BASE_DIR!"

REM Crear carpeta de datos si no existe
if not exist "!BASE_DIR!AppData\Local\DetectorMovimiento\data_local" (
    mkdir "!BASE_DIR!AppData\Local\DetectorMovimiento\data_local"
)

REM Intentar iniciar Flask con manejo de errores
echo [%date% %time%] Iniciando Flask con: !PYTHON_CMD! app.py >> "!LOGFILE!"

REM Usar call para que se ejecute en el mismo proceso
"!PYTHON_CMD!" -u app.py >> "!LOGFILE!" 2>&1

if !errorlevel! neq 0 (
    echo [%date% %time%] Flask termino con codigo de error: !errorlevel! >> "!LOGFILE!"
    exit /b !errorlevel!
)
