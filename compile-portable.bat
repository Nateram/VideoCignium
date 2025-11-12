@echo off
setlocal enabledelayedexpansion
title Compilar Instalador PORTABLE con Inno Setup
cd /d "%~dp0"

echo ========================================
echo  DETECTOR DE MOVIMIENTO
echo  Compilar Instalador PORTABLE
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

REM Verificar Python portable
echo [1/6] Verificando Python portable...
if not exist "python-portable\python.exe" (
    echo.
    echo ========================================
    echo  [ADVERTENCIA] Python portable no encontrado
    echo ========================================
    echo.
    echo El instalador PORTABLE requiere Python portable con
    echo TODAS las dependencias preinstaladas.
    echo.
    echo Debes ejecutar primero:
    echo    prepare-portable-python.bat
    echo.
    echo Este proceso:
    echo   - Descarga Python 3.11.9 embeddable
    echo   - Instala pip
    echo   - Instala TODAS las dependencias (PyTorch, OpenCV, etc)
    echo   - Tarda 10-20 minutos
    echo   - Descarga ~2.5 GB
    echo.
    choice /C SN /M "Ejecutar prepare-portable-python.bat ahora"
    if !errorlevel! equ 1 (
        call prepare-portable-python.bat
        if !errorlevel! neq 0 (
            echo [ERROR] Fallo al preparar Python portable
            pause
            exit /b 1
        )
    ) else (
        echo.
        echo Cancelando compilacion. Por favor ejecuta:
        echo    prepare-portable-python.bat
        echo.
        pause
        exit /b 1
    )
)

echo    [OK] Python portable encontrado
echo.

REM Verificar node_modules
echo [2/6] Verificando dependencias de Node.js...
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
echo [3/6] Verificando modelo YOLO...
if exist "yolov10n.pt" (
    echo    [OK] Modelo YOLO encontrado
) else (
    echo    [ADVERTENCIA] Modelo YOLO no encontrado: yolov10n.pt
    echo    El instalador se creara sin el modelo
)

REM Verificar FFmpeg
echo.
echo [4/6] Verificando FFmpeg...
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
echo [5/6] Preparando carpeta de salida...
if not exist "dist\" (
    mkdir dist
    echo    [OK] Carpeta dist creada
) else (
    echo    [OK] Carpeta dist existe
)

REM Compilar instalador
echo.
echo [6/6] Compilando instalador PORTABLE...
echo.
echo ========================================
echo  ATENCION: Compilacion LARGA
echo ========================================
echo.
echo Este proceso puede tardar 15-30 MINUTOS
echo debido al tamaño de Python portable (~2.5 GB)
echo.
echo Por favor, ten MUCHA paciencia...
echo NO cierres esta ventana.
echo.
pause

%INNO_PATH% installer-portable.iss

if !errorlevel! equ 0 (
    echo.
    echo ========================================
    echo  INSTALADOR PORTABLE CREADO EXITOSAMENTE
    echo ========================================
    echo.
    
    REM Buscar el instalador generado
    for %%F in ("dist\DetectorMovimiento-Portable-Setup-*.exe") do (
        echo Archivo: %%~nxF
        set size=%%~zF
        set /a sizeMB=!size! / 1048576
        echo Tamano: !sizeMB! MB
        echo Ruta completa: %%~fF
    )
    
    echo.
    echo ========================================
    echo  CARACTERISTICAS DEL INSTALADOR
    echo ========================================
    echo.
    echo [+] Python 3.11.9 portable incluido
    echo [+] PyTorch, OpenCV, EasyOCR preinstalados
    echo [+] Ultralytics YOLO incluido
    echo [+] FFmpeg incluido
    echo [+] Node.js/Electron incluido
    echo [+] NO requiere instalar nada adicional
    echo [+] Funciona en CUALQUIER Windows 10/11
    echo.
    echo Tamano estimado del instalador: 2.8 - 3.5 GB
    echo.
    echo ========================================
    echo.
    echo El instalador esta listo para distribuir
    echo Puedes copiarlo a cualquier ordenador
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
    echo Posibles causas:
    echo - Python portable no tiene todas las dependencias
    echo - Falta algun archivo requerido
    echo - No hay suficiente espacio en disco
    echo.
    pause
    exit /b 1
)
