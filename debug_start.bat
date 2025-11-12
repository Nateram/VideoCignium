@echo off
echo ================================================
echo   Debug de inicio de Electron
echo ================================================
echo.

echo Directorio actual:
cd
echo.

echo Contenido del directorio:
dir /b
echo.

echo Verificando Python:
python --version
echo.

echo Verificando Node.js:
node --version
echo.

echo Verificando npm:
npm --version
echo.

echo.
echo Intentando iniciar Flask directamente...
echo.
python app.py
