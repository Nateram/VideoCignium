@echo off
echo ========================================
echo  DETECTOR DE MOVIMIENTO - BUILD
echo ========================================
echo.

REM Limpiar build anterior
echo [1/4] Limpiando builds anteriores...
if exist dist (
    rmdir /s /q dist
    echo    √ Carpeta dist eliminada
)

REM Verificar node_modules
echo.
echo [2/4] Verificando dependencias...
if not exist node_modules (
    echo    Instalando dependencias...
    call npm install
) else (
    echo    √ Dependencias OK
)

REM Crear carpetas necesarias
echo.
echo [3/4] Preparando estructura...
if not exist electron mkdir electron
if not exist data_local mkdir data_local
if not exist logs mkdir logs
echo    √ Estructura preparada

REM Construir instalador
echo.
echo [4/4] Construyendo instalador (esto puede tomar varios minutos)...
echo    Por favor espera...
echo.
call npm run build:win

REM Verificar resultado
echo.
echo ========================================
if exist dist (
    echo  √ BUILD COMPLETADO
    echo ========================================
    echo.
    echo Instalador creado en: dist\
    echo.
    dir /b dist\*.exe 2>nul
    echo.
    echo Abre la carpeta 'dist' para ver los instaladores
    echo.
    pause
) else (
    echo  × BUILD FALLIDO
    echo ========================================
    echo.
    echo Revisa los errores arriba
    echo.
    pause
)
