@echo off
REM Script para descargar modelos de EasyOCR offline
setlocal

set "BASE_DIR=%~dp0"
set "PYTHON_EXE=%BASE_DIR%python-portable\python.exe"
set "EASYOCR_CACHE=%BASE_DIR%python-portable\easyocr-cache"
set "LOGFILE=%BASE_DIR%logs\easyocr-download.log"

if not exist "%BASE_DIR%logs" mkdir "%BASE_DIR%logs"

echo. >> "%LOGFILE%"
echo ======================================== >> "%LOGFILE%"
echo Descarga de modelos EasyOCR >> "%LOGFILE%"
echo Fecha: %date% %time% >> "%LOGFILE%"
echo ======================================== >> "%LOGFILE%"
echo.

echo Verificando Python portable...
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python no encontrado >> "%LOGFILE%"
    exit /b 1
)

echo Descargando modelos de EasyOCR (esto puede tardar 5-10 minutos)...
echo Descargando modelos de EasyOCR... >> "%LOGFILE%"

REM Establecer variable de entorno para que EasyOCR guarde los modelos en nuestra carpeta
set "EASYOCR_HOME=%EASYOCR_CACHE%"

REM Descargar modelos para español e inglés
"%PYTHON_EXE%" -c "import easyocr; import os; os.environ['EASYOCR_HOME'] = r'%EASYOCR_CACHE%'; print('[INFO] Descargando modelos...'); reader = easyocr.Reader(['es', 'en'], gpu=False); print('[OK] Modelos descargados')" 1>>"%LOGFILE%" 2>&1

if %errorlevel% neq 0 (
    echo [ERROR] Fallo al descargar modelos EasyOCR >> "%LOGFILE%"
    echo Error durante la descarga de modelos EasyOCR
    type "%LOGFILE%"
    pause
    exit /b 1
) else (
    echo [OK] Modelos EasyOCR descargados exitosamente >> "%LOGFILE%"
    echo ✓ Modelos EasyOCR descargados exitosamente
)

endlocal
