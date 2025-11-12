@echo off
setlocal enabledelayedexpansion
title Preparar Python Portable con Dependencias
cd /d "%~dp0"

echo ========================================
echo  PREPARAR PYTHON PORTABLE
echo  Con todas las dependencias incluidas
echo ========================================
echo.

REM Crear carpeta para Python portable
set PORTABLE_DIR=python-portable
if exist "%PORTABLE_DIR%" (
    echo [ADVERTENCIA] La carpeta %PORTABLE_DIR% ya existe
    choice /C SN /M "Recrear carpeta (borrara contenido)"
    if !errorlevel! equ 1 (
        echo Eliminando carpeta existente...
        rmdir /s /q "%PORTABLE_DIR%"
    ) else (
        echo Usando carpeta existente
        goto :check_python
    )
)

echo.
echo ========================================
echo  PASO 1: Descargar Python Embeddable
echo ========================================
echo.

set PYTHON_VERSION=3.11.9
set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip
set PYTHON_ZIP=python-embed.zip

echo Descargando Python %PYTHON_VERSION% embeddable...
echo URL: %PYTHON_URL%
echo.

powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP%'}"

if !errorlevel! neq 0 (
    echo [ERROR] Fallo al descargar Python
    pause
    exit /b 1
)

echo [OK] Python descargado
echo.

echo Extrayendo Python...
powershell -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PORTABLE_DIR%' -Force"
del "%PYTHON_ZIP%"
echo [OK] Python extraido a %PORTABLE_DIR%
echo.

:check_python

echo ========================================
echo  PASO 2: Configurar pip en Python portable
echo ========================================
echo.

REM Descargar get-pip.py
echo Descargando get-pip.py...
powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PORTABLE_DIR%\get-pip.py'"

REM Habilitar site-packages en python embeddable
echo Configurando python311._pth para habilitar pip...
(
    echo python311.zip
    echo .
    echo import site
) > "%PORTABLE_DIR%\python311._pth"

echo [OK] Configuracion actualizada
echo.

REM Instalar pip
echo Instalando pip...
"%PORTABLE_DIR%\python.exe" "%PORTABLE_DIR%\get-pip.py" --no-warn-script-location
if !errorlevel! neq 0 (
    echo [ERROR] Fallo al instalar pip
    pause
    exit /b 1
)

echo [OK] pip instalado
del "%PORTABLE_DIR%\get-pip.py"
echo.

echo ========================================
echo  PASO 3: Instalar dependencias
echo  ESTO TARDARA 10-20 MINUTOS
echo  Descargara ~2.5 GB
echo ========================================
echo.

echo Instalando dependencias desde requirements.txt...
echo Por favor espera, esto puede tardar bastante...
echo.

"%PORTABLE_DIR%\python.exe" -m pip install --upgrade pip
"%PORTABLE_DIR%\python.exe" -m pip install -r requirements.txt --no-warn-script-location

if !errorlevel! neq 0 (
    echo.
    echo [ERROR] Fallo al instalar algunas dependencias
    echo.
    choice /C SN /M "Continuar de todas formas"
    if !errorlevel! equ 2 (
        exit /b 1
    )
)

echo.
echo [OK] Dependencias instaladas
echo.

echo ========================================
echo  PASO 4: Verificar instalacion
echo ========================================
echo.

echo Verificando modulos instalados...
"%PORTABLE_DIR%\python.exe" -c "import flask; print('Flask:', flask.__version__)"
"%PORTABLE_DIR%\python.exe" -c "import cv2; print('OpenCV:', cv2.__version__)"
"%PORTABLE_DIR%\python.exe" -c "import torch; print('PyTorch:', torch.__version__)"
"%PORTABLE_DIR%\python.exe" -c "import ultralytics; print('Ultralytics:', ultralytics.__version__)"
"%PORTABLE_DIR%\python.exe" -c "import easyocr; print('EasyOCR: OK')"

if !errorlevel! neq 0 (
    echo.
    echo [ADVERTENCIA] Algunos modulos no se pudieron verificar
    pause
)

echo.
echo ========================================
echo  RESUMEN
echo ========================================
echo.

REM Calcular tamaño
for /f "tokens=3" %%a in ('dir "%PORTABLE_DIR%" /s ^| find "bytes"') do set size=%%a
set /a sizeMB=!size! / 1048576

echo Carpeta: %PORTABLE_DIR%
echo Tamano aproximado: !sizeMB! MB
echo.
echo Python portable listo para empaquetar
echo.
echo Ahora puedes compilar el instalador con:
echo   compile-inno.bat
echo.

pause
