# Parche para deshabilitar descargas de EasyOCR
import sys
import os
from pathlib import Path

# Monkeypatch para urllib3 (usado por EasyOCR para descargar)
import urllib.request
_original_urlopen = urllib.request.urlopen

def patched_urlopen(url, *args, **kwargs):
    """Bloquea cualquier descarga de EasyOCR"""
    if 'easyocr' in str(url).lower() or 'github' in str(url).lower():
        raise RuntimeError(f"🚫 OFFLINE MODE: Descarga bloqueada: {url}")
    return _original_urlopen(url, *args, **kwargs)

urllib.request.urlopen = patched_urlopen

# También monkeypatch torch
try:
    import torch
    os.environ['TORCH_HOME'] = str(Path(__file__).parent / "torch-cache")
except:
    pass

# Monkeypatch HuggingFace
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'
