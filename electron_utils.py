"""
Script de inicialización para Electron
Detecta si está corriendo en modo empaquetado y ajusta rutas
"""
import os
import sys

def is_packaged():
    """Detecta si la aplicación está empaquetada con Electron"""
    return hasattr(sys, '_MEIPASS') or os.environ.get('ELECTRON_RUN_AS_NODE')

def get_base_path():
    """Obtiene el directorio base correcto según el modo de ejecución"""
    if is_packaged():
        # En modo empaquetado, usar resourcesPath
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    else:
        # En desarrollo
        return os.path.dirname(os.path.abspath(__file__))

# Exportar para uso en otros módulos
BASE_PATH = get_base_path()
IS_PACKAGED = is_packaged()
