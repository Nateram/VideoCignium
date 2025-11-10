@echo off
REM Script para ejecutar la aplicación en Docker (Windows)
REM Uso: docker-run.bat

echo 🐳 Construyendo y ejecutando aplicación en Docker...

REM Detener contenedores anteriores si existen
echo 🛑 Deteniendo contenedores anteriores...
docker-compose down

REM Construir imagen
echo 🔨 Construyendo imagen Docker...
docker-compose build

REM Ejecutar aplicación
echo 🚀 Iniciando aplicación...
docker-compose up -d

REM Esperar a que la aplicación esté lista
echo ⏳ Esperando a que la aplicación esté lista...
timeout /t 10 /nobreak > nul

REM Verificar que esté corriendo
curl -f http://localhost:5000 > nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Aplicación ejecutándose correctamente en http://localhost:5000
    echo.
    echo 📋 Comandos útiles:
    echo   - Ver logs: docker-compose logs -f
    echo   - Detener: docker-compose down
    echo   - Reiniciar: docker-compose restart
) else (
    echo ❌ Error: La aplicación no responde en http://localhost:5000
    echo 📋 Ver logs con: docker-compose logs
    exit /b 1
)