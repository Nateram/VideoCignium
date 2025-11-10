# 🐳 Construcción de Imagen Docker con Modelo YOLO Incluido

Esta guía explica cómo construir la imagen Docker con el modelo YOLO ya integrado para portabilidad.

## 📦 Ventajas de incluir el modelo en la imagen

- ✅ **Portabilidad total**: Mueve la imagen a cualquier servidor sin descargas adicionales
- ✅ **Inicio rápido**: No hay descarga de modelo en el primer uso
- ✅ **Offline-ready**: Funciona sin conexión a internet (después del build)
- ✅ **Reproducibilidad**: La misma imagen funciona idénticamente en cualquier lugar

## 🚀 Opción 1: Build rápido (recomendado)

### Paso 1: Descargar el modelo localmente (opcional pero más rápido)

```powershell
# En Windows PowerShell
python download_model.py

# O usando el script batch
download-model.bat
```

Esto descargará `yolov10n.pt` (~6MB) al directorio actual.

### Paso 2: Construir la imagen Docker

```powershell
docker compose build
```

El Dockerfile detectará el modelo local y lo copiará a la imagen, o lo descargará si no existe.

## 🐌 Opción 2: Build directo (sin pre-descarga)

Si no pre-descargas el modelo, el Dockerfile lo descargará automáticamente durante el build:

```powershell
docker compose build
```

⚠️ Esto puede tardar más tiempo y requiere conexión a internet durante el build.

## 🔍 Verificar que el modelo está incluido

Después del build, puedes verificar que el modelo está en la imagen:

```powershell
# Iniciar un contenedor temporal
docker run --rm -it web_app-video-analysis-app:latest /bin/bash

# Dentro del contenedor, buscar el modelo
find / -name "yolov10n.pt" 2>/dev/null
ls -lh ~/.cache/ultralytics/

# Salir
exit
```

## 📤 Exportar imagen para otro dispositivo

Una vez construida, puedes exportar la imagen (con modelo incluido):

```powershell
# Exportar a archivo .tar
docker save -o video-analysis-app.tar web_app-video-analysis-app:latest

# Copiar video-analysis-app.tar al otro dispositivo (USB, red, etc.)

# En el otro dispositivo, importar:
docker load -i video-analysis-app.tar

# Ejecutar
docker compose up -d
```

## 🏷️ Subir a Docker Hub (alternativa)

Si prefieres usar un registro en lugar de archivos .tar:

```powershell
# Login
docker login

# Etiquetar
docker tag web_app-video-analysis-app:latest tu-usuario/video-analysis:v1.0

# Push
docker push tu-usuario/video-analysis:v1.0

# En otro dispositivo:
docker pull tu-usuario/video-analysis:v1.0
```

## 📁 Estructura de archivos relevantes

```
web_app/
├── Dockerfile              # Configurado para incluir modelo YOLO
├── .dockerignore          # Permite copiar yolov10n.pt
├── download_model.py      # Script Python para descargar modelo
├── download-model.bat     # Script batch para Windows
├── requirements.txt       # Incluye ultralytics
└── yolov10n.pt           # Modelo YOLO (si se pre-descarga)
```

## ⚙️ Variables de entorno útiles

Para cambiar el modelo YOLO (si quieres usar otro):

Edita `video_processing.py` línea 343:
```python
model_name = "yolov10n.pt"  # Cambiar a yolov10s.pt, yolov10m.pt, etc.
```

## 🐛 Troubleshooting

### El modelo no se descarga durante el build
- Verifica conexión a internet durante `docker compose build`
- Intenta pre-descargar con `python download_model.py`

### Imagen muy grande
- `yolov10n.pt` (~6MB) es el modelo más pequeño
- Si quieres reducir tamaño, usa `.dockerignore` para excluirlo (descarga en runtime)

### Modelo no encontrado al ejecutar
- Verifica logs: `docker compose logs -f`
- El código tiene fallback automático para descargar si falta

## 📊 Tamaños aproximados

- Imagen base: ~1.5 GB
- Con modelo YOLO: ~1.51 GB (+6MB)
- Exportado .tar: ~600 MB (comprimido)

## 🎯 Resumen de comandos

```powershell
# Flujo completo recomendado
python download_model.py          # Descargar modelo
docker compose build              # Construir imagen
docker compose up -d              # Ejecutar
docker save -o app.tar ...        # Exportar (opcional)
```

---

**Nota**: El modelo YOLO se almacena en `/root/.cache/ultralytics/` dentro del contenedor. Si destruyes el contenedor pero la imagen persiste, el modelo sigue ahí. Solo se pierde si eliminas la imagen con `docker rmi`.
