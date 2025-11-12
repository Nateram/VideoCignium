@echo off
setlocal enabledelayedexpansion
title Compilar Instalador con Inno Setup
cd /d "%~dp0"

echo ========================================
echo  DETECTOR DE MOVIMIENTO
echo  Compilar Instalador con Inno Setup
echo ========================================
echo.

REM Verificar que Inno Setup esté instalado
set INNO_PATH="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %INNO_PATH% (
    echo [ERROR] Inno Setup no encontrado
    echo.
    echo Buscando en rutas alternativas...
    set INNO_PATH="C:\Program Files\Inno Setup 6\ISCC.exe"
    if not exist !INNO_PATH! (
        echo [ERROR] Inno Setup no encontrado en ninguna ubicacion conocida
        echo.
        echo Por favor instala Inno Setup desde:
        echo https://jrsoftware.org/isdl.php
        echo.
        pause
        exit /b 1
    )
)

echo [OK] Inno Setup encontrado: %INNO_PATH%
echo.

REM Verificar node_modules
echo [1/5] Verificando dependencias de Node.js...
if not exist "node_modules\" (
    echo    Instalando dependencias...
    call npm install
    if !errorlevel! neq 0 (
        echo [ERROR] Fallo al instalar dependencias
        pause
        exit /b 1
    )
    echo    [OK] Dependencias instaladas
) else (
    echo    [OK] Dependencias ya instaladas
)

REM Verificar modelo YOLO
echo.
echo [2/5] Verificando modelo YOLO...
if exist "yolov10n.pt" (
    echo    [OK] Modelo YOLO encontrado
) else (
    echo    [ADVERTENCIA] Modelo YOLO no encontrado: yolov10n.pt
    echo    El instalador se creara sin el modelo
)

REM Verificar FFmpeg
echo.
echo [3/5] Verificando FFmpeg...
if exist "ffmpeg-2025-09-28-git-0fdb5829e3-essentials_build\" (
    echo    [OK] FFmpeg encontrado
) else (
    echo    [ERROR] FFmpeg no encontrado
    echo    La aplicacion no funcionara sin FFmpeg
    pause
    exit /b 1
)

REM Crear carpeta dist
echo.
echo [4/5] Preparando carpeta de salida...
if not exist "dist\" (
    mkdir dist
    echo    [OK] Carpeta dist creada
) else (
    echo    [OK] Carpeta dist existe
)

REM Compilar instalador
echo.
echo [5/5] Compilando instalador (puede tardar varios minutos)...
echo      Por favor espera...
echo.

%INNO_PATH% installer.iss

if !errorlevel! equ 0 (
    echo.
    echo ========================================
    echo  INSTALADOR CREADO EXITOSAMENTE
    echo ========================================
    echo.
    
    REM Buscar el instalador generado
    for %%F in ("dist\DetectorMovimiento-Setup-*.exe") do (
        echo Archivo: %%~nxF
        set size=%%~zF
        set /a sizeMB=!size! / 1048576
        echo Tamano: !sizeMB! MB
        echo Ruta completa: %%~fF
    )
    
    echo.
    echo ========================================
    echo.
    echo El instalador esta listo para distribuir
    echo.
    choice /C SN /M "Abrir carpeta dist"
    if !errorlevel! equ 1 (
        explorer dist
    )
) else (
    echo.
    echo ========================================
    echo  ERROR AL COMPILAR
    echo ========================================
    echo.
    echo Revisa los mensajes de error arriba
    echo.
    pause
    exit /b 1
)
