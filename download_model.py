#!/usr/bin/env python3
"""
Script para descargar el modelo YOLO localmente.
Ejecuta esto antes de construir la imagen Docker para incluir el modelo.

Uso: python download_model.py
"""

import os
import sys

def download_yolo_model():
    """Descarga el modelo YOLO si no existe."""
    model_name = "yolov10n.pt"
    
    # Verificar si ya existe
    if os.path.exists(model_name):
        print(f"✅ El modelo {model_name} ya existe en el directorio actual")
        return True
    
    try:
        print(f"📥 Descargando modelo YOLO: {model_name}...")
        from ultralytics import YOLO
        
        # Descargar el modelo
        model = YOLO(model_name)
        print(f"✅ Modelo descargado exitosamente")
        
        # Verificar que se descargó
        if os.path.exists(model_name):
            size_mb = os.path.getsize(model_name) / (1024 * 1024)
            print(f"📦 Tamaño del modelo: {size_mb:.2f} MB")
            print(f"📍 Ubicación: {os.path.abspath(model_name)}")
            return True
        else:
            print(f"⚠️ El modelo se descargó pero no está en el directorio actual")
            print(f"   Probablemente está en: ~/.cache/ultralytics/")
            return False
            
    except ImportError:
        print("❌ Error: No se pudo importar ultralytics")
        print("   Instala con: pip install ultralytics")
        return False
    except Exception as e:
        print(f"❌ Error al descargar el modelo: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("  Descargador de Modelo YOLO para Docker")
    print("=" * 60)
    print()
    
    success = download_yolo_model()
    
    print()
    if success:
        print("✅ ¡Listo! Ahora puedes construir la imagen Docker:")
        print("   docker compose build")
        print()
        print("El modelo será incluido en la imagen y no necesitará descargarse.")
    else:
        print("⚠️ No se pudo descargar el modelo localmente.")
        print("   El modelo se descargará durante el build de Docker.")
    
    sys.exit(0 if success else 1)
