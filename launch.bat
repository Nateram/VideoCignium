@echo off
title Detector de Movimiento
setlocal

REM Preparar carpeta de logs
set "LOGDIR=%~dp0logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOGFILE=%LOGDIR%\launcher.log"

REM Punto base de la instalación (misma carpeta que este .bat)
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

echo ========================================
echo  Detector de Movimiento (portable)
echo ========================================
echo.

REM ==== Python portable incluido ====
set "PY_PORTABLE=%BASE_DIR%python-portable"
set "PY_EXE=%PY_PORTABLE%\python.exe"
set "PYW_EXE=%PY_PORTABLE%\pythonw.exe"

if exist "%PYW_EXE%" (
    set "PYTHON_CMD=%PYW_EXE%"
) else if exist "%PY_EXE%" (
    set "PYTHON_CMD=%PY_EXE%"
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] No se encontro la carpeta python-portable dentro de la instalacion.
    echo Ruta esperada: %PY_PORTABLE%
    echo Reinstala la aplicacion o verifica que no haya sido bloqueada por el antivirus.
    pause
    exit /b 1
)

REM ==== Electron portable (no requiere Node global) ====
set "ELECTRON_EXE=%BASE_DIR%node_modules\electron\dist\electron.exe"
if not exist "%ELECTRON_EXE%" (
    echo [ERROR] Electron no esta disponible en node_modules\electron\dist.
    echo Ruta esperada: %ELECTRON_EXE%
    echo.
    echo Posibles causas:
    echo - La instalacion fue incompleta o corrupta
    echo - El antivirus bloqueo los archivos
    echo - La descarga no se completo
    echo.
    echo Ejecuta verify-installation.bat para diagnosticar.
    pause
    exit /b 1
)

echo Usando Python portable: %PYTHON_CMD%
echo.

REM ==== Validaciones previas ====
if not exist "%BASE_DIR%package.json" (
    echo [ERROR] No se encontro package.json en %BASE_DIR%
    echo La carpeta base no es valida.
    pause
    exit /b 1
)

if not exist "%BASE_DIR%electron\main.js" (
    echo [ERROR] No se encontro electron\main.js
    pause
    exit /b 1
)

echo Iniciando aplicacion...
echo (log: %LOGFILE%)
echo (directorio: %BASE_DIR%)
echo.

REM Cambiar al directorio base ANTES de ejecutar Electron
pushd "%BASE_DIR%"

echo [%date% %time%] Iniciando servidor Flask... >> "%LOGFILE%"
echo Iniciando servidor Flask en background...

REM Asegurar que el puerto 5000 está libre (matar procesos antiguos)
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Flask*" >nul 2>&1

REM Esperar un momento a que se libere el puerto
timeout /t 2 /nobreak > nul

REM Lanzar Flask en un proceso separado que se mantenga activo
REM CRÍTICO: /B permite que vuelva inmediatamente
REM /HIGH prioridad normal
REM /MIN ocultar ventana
start "Flask_Server" /B /MIN "%PYTHON_CMD%" -u app.py >"%LOGFILE%" 2>&1

REM Esperar a que Flask se inicie (incrementar a 20 segundos)
echo Esperando a que Flask inicie y se estabilice...
for /L %%i in (1,1,20) do (
    timeout /t 1 /nobreak > nul
)

echo [%date% %time%] Iniciando Electron... >> "%LOGFILE%"
echo.
echo Iniciando Electron...

REM Ejecutar Electron (NO redirigir salida, dejar que fluya naturalmente)
"%ELECTRON_EXE%" . 
set "EXITCODE=%errorlevel%"

REM Registrar cierre y matar cualquier proceso de Python que haya quedado
echo [%date% %time%] Electron cerrado, limpiando procesos... >> "%LOGFILE%"
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Flask*" >nul 2>&1

popd

if not "%EXITCODE%"=="0" (
    echo.
    echo [ERROR] La aplicacion se cerro inesperadamente (codigo %EXITCODE%).
    echo Mostrando las ultimas lineas del log:
    echo --------------------------------------------------
    for /f "usebackq skip=0 delims=" %%L in ("%LOGFILE%") do set "LAST=%%L" & echo %%L
    echo --------------------------------------------------
    echo Log completo en: %LOGFILE%
    pause
)

endlocal
