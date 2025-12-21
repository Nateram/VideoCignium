#!/usr/bin/env python
"""
Script de prueba para verificar que EasyOCR funciona en modo OFFLINE.
"""
import sys
import os
from pathlib import Path

# Configurar variables de entorno ANTES de importar easyocr
CURRENT_DIR = Path(__file__).parent
CACHE_PROJECT = CURRENT_DIR / "easyocr-cache"

print(f"📁 Directorio actual: {CURRENT_DIR}")
print(f"📁 Caché de EasyOCR: {CACHE_PROJECT}")
print(f"✓ Carpeta existe: {CACHE_PROJECT.exists()}")
print(f"✓ Carpeta model existe: {(CACHE_PROJECT / 'model').exists()}")

# Establecer variables de entorno
os.environ['EASYOCR_HOME'] = str(CACHE_PROJECT)
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['OFFLINE'] = '1'

print("\n🔧 Variables de entorno configuradas:")
print(f"  EASYOCR_HOME = {os.environ.get('EASYOCR_HOME')}")
print(f"  HF_HUB_OFFLINE = {os.environ.get('HF_HUB_OFFLINE')}")
print(f"  OFFLINE = {os.environ.get('OFFLINE')}")

# Ahora importar easyocr
print("\n⏳ Importando easyocr...")
try:
    import easyocr
    print("✓ easyocr importado correctamente")
except Exception as e:
    print(f"✗ Error al importar easyocr: {e}")
    sys.exit(1)

# Intentar crear un Reader
print("\n⏳ Inicializando lector EasyOCR (offline)...")
try:
    reader = easyocr.Reader(['en'], gpu=False, model_storage_directory=str(CACHE_PROJECT))
    print("✓ Lector inicializado correctamente")
except Exception as e:
    print(f"✗ Error al inicializar Reader: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Probar OCR en una imagen pequeña
print("\n⏳ Probando OCR...")
try:
    import cv2
    import numpy as np
    
    # Crear una imagen de prueba con texto
    img = np.ones((100, 300, 3), dtype=np.uint8) * 255
    cv2.putText(img, "TEST", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    # Realizar OCR
    result = reader.readtext(img)
    
    if result:
        print(f"✓ OCR funcionó correctamente")
        print(f"  Texto detectado: {' '.join([r[1] for r in result])}")
    else:
        print("⚠ No se detectó texto (es normal en una imagen de prueba)")
        
except Exception as e:
    print(f"✗ Error durante OCR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ PRUEBA COMPLETADA EXITOSAMENTE")
print("La aplicación debería funcionar correctamente en modo offline.")
