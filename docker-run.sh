#!/bin/bash

# Script para ejecutar la aplicación en Docker (Linux/Mac)
# Uso: ./docker-run.sh

echo "🐳 Construyendo y ejecutando aplicación en Docker..."

# Detener contenedores anteriores si existen
echo "🛑 Deteniendo contenedores anteriores..."
docker-compose down

# Construir imagen
echo "🔨 Construyendo imagen Docker..."
docker-compose build

# Ejecutar aplicación
echo "🚀 Iniciando aplicación..."
docker-compose up -d

# Esperar a que la aplicación esté lista
echo "⏳ Esperando a que la aplicación esté lista..."
sleep 10

# Verificar que esté corriendo
if curl -f http://localhost:5000 > /dev/null 2>&1; then
    echo "✅ Aplicación ejecutándose correctamente en http://localhost:5000"
    echo ""
    echo "📋 Comandos útiles:"
    echo "  - Ver logs: docker-compose logs -f"
    echo "  - Detener: docker-compose down"
    echo "  - Reiniciar: docker-compose restart"
else
    echo "❌ Error: La aplicación no responde en http://localhost:5000"
    echo "📋 Ver logs con: docker-compose logs"
    exit 1
fi