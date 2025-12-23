# Modo 100 % local: la aplicación no usa internet en ningún momento.
# Se importa ANTES que ultralytics, easyocr y torch (app.py y video_processing.py lo cargan primero).
import os
from pathlib import Path
from urllib.parse import urlparse

# Ultralytics (YOLO): sin comprobación de conexión, sin descargas y sin telemetría
os.environ['YOLO_OFFLINE'] = 'true'
# HuggingFace: solo caché local
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
# torch: caché dentro de la carpeta de la aplicación (se fija antes de importar torch)
os.environ.setdefault('TORCH_HOME', str(Path(__file__).parent / "torch-cache"))

_LOCAL_HOSTS = {'localhost', '127.0.0.1', '::1', ''}


def _es_local(url):
    """True si la URL apunta a la propia máquina (o es un archivo local)."""
    try:
        u = url if isinstance(url, str) else getattr(url, 'full_url', str(url))
        return (urlparse(u).hostname or '') in _LOCAL_HOSTS
    except Exception:
        return False


# urllib (lo usan EasyOCR y torch para descargar modelos): bloquear todo lo que no sea local
import urllib.request
_original_urlopen = urllib.request.urlopen


def patched_urlopen(url, *args, **kwargs):
    if not _es_local(url):
        raise RuntimeError(f"🚫 OFFLINE MODE: conexión externa bloqueada: {url}")
    return _original_urlopen(url, *args, **kwargs)


urllib.request.urlopen = patched_urlopen

# requests (lo usa ultralytics): igual
try:
    import requests
    _original_request = requests.Session.request

    def patched_request(self, method, url, *args, **kwargs):
        if not _es_local(url):
            raise RuntimeError(f"🚫 OFFLINE MODE: conexión externa bloqueada: {url}")
        return _original_request(self, method, url, *args, **kwargs)

    requests.Session.request = patched_request
except ImportError:
    pass
