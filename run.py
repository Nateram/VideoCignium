#!/usr/bin/env python3
"""
Script de inicio para la aplicación web de análisis de video.
Ejecuta: python run.py
"""

import sys
import os

# 🔥 USAR RUTA ABSOLUTA DEL SCRIPT PARA PATH
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

def main():
    """Función principal para iniciar la aplicación"""
    try:
        print("🚀 Iniciando aplicación web de análisis de video...")
        print("📁 Directorio del script:", BASE_DIR)
        print("📁 Directorio de trabajo actual:", os.getcwd())

        # Importar y ejecutar la aplicación Flask
        from app import app

        print("✅ Aplicación cargada correctamente")
        print("🌐 Iniciando servidor en http://localhost:5000")
        print("   Presiona Ctrl+C para detener")

        # Ejecutar en modo debug para desarrollo
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=False  # Deshabilitar reloader para evitar problemas con threads
        )

    except KeyboardInterrupt:
        print("\n👋 Aplicación detenida por el usuario")
    except Exception as e:
        print(f"❌ Error al iniciar la aplicación: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()