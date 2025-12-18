@echo off
title Verificador de Instalacion - Detector de Movimiento
setlocal

set "BASE_DIR=%~dp0"
set "LOGFILE=%BASE_DIR%logs\install-verify.log"

if not exist "%BASE_DIR%logs" mkdir "%BASE_DIR%logs"

echo ========================================
echo  Verificador de Instalacion
echo ========================================
echo Timestamp: %date% %time% >> "%LOGFILE%"
echo. >> "%LOGFILE%"

echo Verificando archivos esenciales...
echo. >> "%LOGFILE%"
echo Verificando archivos esenciales... >> "%LOGFILE%"

REM Verificar Python
if exist "%BASE_DIR%python-portable\python.exe" (
    echo [OK] Python portable encontrado >> "%LOGFILE%"
    echo.
    echo ✓ Python portable
) else (
    echo [ERROR] Python portable NO encontrado >> "%LOGFILE%"
    echo ✗ Python portable FALTA
)

REM Verificar Electron
if exist "%BASE_DIR%node_modules\electron\dist\electron.exe" (
    echo [OK] Electron encontrado >> "%LOGFILE%"
    echo ✓ Electron
) else (
    echo [ERROR] Electron NO encontrado >> "%LOGFILE%"
    echo ✗ Electron FALTA
)

REM Verificar tree-kill
if exist "%BASE_DIR%node_modules\tree-kill\package.json" (
    echo [OK] tree-kill encontrado >> "%LOGFILE%"
    echo ✓ tree-kill
) else (
    echo [ERROR] tree-kill NO encontrado >> "%LOGFILE%"
    echo ✗ tree-kill FALTA
)

REM Verificar package.json
if exist "%BASE_DIR%package.json" (
    echo [OK] package.json encontrado >> "%LOGFILE%"
    echo ✓ package.json
) else (
    echo [ERROR] package.json NO encontrado >> "%LOGFILE%"
    echo ✗ package.json FALTA
)

REM Verificar main.js
if exist "%BASE_DIR%electron\main.js" (
    echo [OK] electron\main.js encontrado >> "%LOGFILE%"
    echo ✓ electron/main.js
) else (
    echo [ERROR] electron\main.js NO encontrado >> "%LOGFILE%"
    echo ✗ electron/main.js FALTA
)

REM Verificar app.py
if exist "%BASE_DIR%app.py" (
    echo [OK] app.py encontrado >> "%LOGFILE%"
    echo ✓ app.py
) else (
    echo [ERROR] app.py NO encontrado >> "%LOGFILE%"
    echo ✗ app.py FALTA
)

REM Verificar FFmpeg
if exist "%BASE_DIR%ffmpeg-2025-09-28-git-0fdb5829e3-essentials_build\bin\ffmpeg.exe" (
    echo [OK] FFmpeg encontrado >> "%LOGFILE%"
    echo ✓ FFmpeg
) else (
    echo [ERROR] FFmpeg NO encontrado >> "%LOGFILE%"
    echo ✗ FFmpeg FALTA
)

REM Verificar YOLO
if exist "%BASE_DIR%yolov10n.pt" (
    echo [OK] Modelo YOLO encontrado >> "%LOGFILE%"
    echo ✓ Modelo YOLO
) else (
    echo [ERROR] Modelo YOLO NO encontrado >> "%LOGFILE%"
    echo ✗ Modelo YOLO FALTA
)

echo.
echo Verificacion completada. Log: %LOGFILE%
echo.
REM Pausa opcional (descomenta si quieres ver la salida)
REM pause

endlocal
