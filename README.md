# Detector de Movimiento - Guía de Compilación y Ejecución

## 📋 Requisitos del Sistema

### Para Ejecutar la Aplicación Instalada
- **SO**: Windows 10 o superior (64-bit)
- **Memoria RAM**: Mínimo 4 GB, recomendado 8 GB
- **Espacio en disco**: Mínimo 5 GB para la instalación completa
- **Procesador**: Multi-core (recomendado Intel i5 o superior para procesamiento fluido)
- **GPU (opcional pero recomendada)**:
  - **GPU NVIDIA**: Cualquier GPU con soporte CUDA (compute capability 3.5+)
  - **CUDA Toolkit**: 11.8 o superior (si tienes GPU NVIDIA)
  - **cuDNN**: 8.0 o superior (si tienes GPU NVIDIA)
  - Si **NO tienes GPU NVIDIA**, la aplicación funciona con CPU (más lento pero funcional)

### Para Compilar y Ejecutar desde Código Fuente
- **Python**: 3.11 o superior
- **Node.js**: 16 o superior (para Electron)
- **npm**: 8 o superior
- **Visual C++ Build Tools**: 2019 o superior (requerido para compilar extensiones de Python)
- **Inno Setup 6**: Para crear el instalador
- **Git**: Para clonar y gestionar el código
- **GPU NVIDIA (opcional)**:
  - CUDA Toolkit 11.8+
  - cuDNN 8.0+
  - Drivers de NVIDIA actualizados

---

## 🚀 Cómo Ejecutar el Proyecto en Desarrollo

### 1. Preparar el Entorno

```bash
# Navegar a la carpeta del proyecto
cd <path-to-project>

# Crear un entorno virtual de Python
python -m venv venv

# Activar el entorno virtual
venv\Scripts\activate
```

### 2. Instalar Dependencias de Python

```bash
# Instalar paquetes de requirements.txt
pip install -r requirements.txt
```

### 3. Instalar Dependencias de Node.js

```bash
# Instalar módulos de Node.js (incluyendo Electron y Handsontable)
npm install
```

### 4. Ejecutar la Aplicación

Hay dos opciones:

#### Opción A: Ejecutar con el script de lanzamiento
```bash
# En Windows PowerShell
.\launch.bat
```

#### Opción B: Ejecutar componentes por separado (desarrollo)

**Terminal 1 - Servidor Flask:**
```bash
python app.py
```

**Terminal 2 - Interfaz Electron:**
```bash
npx electron electron/main.js
```

### 5. Verificar la Instalación

Una vez que la aplicación esté corriendo:
- Abre el navegador en `http://localhost:5000` (debe funcionar automáticamente)
- Verifica que los iconos Font Awesome se muestren correctamente
- Prueba la funcionalidad de OCR y procesamiento de video

---

## 🔧 Cómo Crear el Instalador Portable

### 1. Requisitos Previos
- Descargar e instalar **Inno Setup 6** desde: https://jrsoftware.org/isdl.php
- Asegurarse de que Python portable esté completamente compilado (está incluido en el proyecto)
- Verificar que todos los archivos offline estén presentes:
  - `static/libs/fontawesome.min.css`
  - `static/libs/webfonts/` (carpeta con .woff2)
  - `static/libs/handsontable/`
  - `static/libs/chart.js`
  - `easyocr-cache/` (modelos OCR)
  - `vc_redist.x64.exe`

### 2. Compilar el Instalador

```bash
# Navegar a la carpeta del proyecto
cd <path-to-project>

# Compilar usando Inno Setup
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer-portable-v2.iss
```

El proceso puede tardar varios minutos (5-10 minutos). El resultado será:
```
Successful compile (xxx,xxx sec)
Resulting Setup program filename is:
<path-to-project>\dist\DetectorMovimiento-Portable-Setup-1.0.0-v2.exe
```

### 3. Distribuir el Instalador

El archivo `DetectorMovimiento-Portable-Setup-1.0.0-v2.exe` está listo para distribuir:
- ✅ Completamente portable (no requiere instalaciones previas)
- ✅ Todos los componentes embebidos (Python, Node.js, Electron, FFmpeg, YOLO, EasyOCR)
- ✅ Configuración offline (sin descargas en tiempo de ejecución)
- ✅ Visual C++ Redistributable incluido
- ✅ Procesamiento con CPU (GPU NVIDIA opcional para acelerar)

---

## 📁 Estructura de Archivos Importantes

```
<project-root>/
├── app.py                          # Servidor Flask principal
├── launch.bat                      # Script de lanzamiento automático
├── electron/
│   ├── main.js                     # Proceso principal de Electron
│   └── preload.js                  # Preload script
├── templates/
│   ├── base.html                   # Template base con Font Awesome
│   ├── dashboard.html
│   └── directo.html
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── app.js
│   │   ├── dashboard.js
│   │   └── main.js
│   └── libs/
│       ├── fontawesome.min.css     # Font Awesome CSS (rutas corregidas)
│       ├── webfonts/               # Fuentes de Font Awesome
│       │   ├── fa-solid-900.woff2
│       │   ├── fa-regular-400.woff2
│       │   └── fa-brands-400.woff2
│       ├── handsontable/           # Tabla offline
│       └── chart.js                # Gráficos offline
├── offline_mode.py                 # Bloquea descargas de internet
├── ocr.py                          # Módulo OCR
├── video_processing.py             # Procesamiento de video
├── installer-portable-v2.iss       # Script de Inno Setup
├── easyocr-cache/                  # Modelos precompilados de EasyOCR
│   ├── craft_mlt_25k.pth
│   ├── english_g2.pth
│   └── model/
│       ├── craft_mlt_25k.pth
│       ├── english_g2.pth
│       └── latin_g2.pth
├── python-portable/                # Python embebido (generado por setup)
├── ffmpeg-2025-09-28-git-0fdb5829e3-essentials_build/
│   └── bin/
│       └── ffmpeg.exe
├── yolov10n.pt                     # Modelo YOLO precompilado
├── vc_redist.x64.exe               # Visual C++ Redistributable
└── requirements.txt                # Dependencias de Python
```

---

## 🔑 Características de Compilación

### Características del Instalador

✅ **Completamente Offline**
- Todas las dependencias embebidas
- No requiere conexión a internet
- Los modelos de OCR están precompilados

✅ **Portable**
- Incluye Python embebido
- Electron empaquetado
- FFmpeg integrado
- YOLO y EasyOCR precompilados

✅ **Fácil de Usar**
- Instalador visual (.exe)
- Desinstalador automático
- Atajos en Inicio/Escritorio

✅ **Optimizaciones**
- Compresión LZMA2 ultra
- Font Awesome CSS con rutas corregidas
- Detección de procesos duplicados en Electron
- Espera de 20 segundos para Flask startup

---

## 🛠️ Troubleshooting

### Problema: Flask no inicia
**Solución**: Aumentar el tiempo de espera en `launch.bat` (línea 80)
```batch
timeout /t 25 /nobreak
```

### Problema: Los iconos aparecen vacíos
**Solución**: Verificar que las rutas en `static/libs/fontawesome.min.css` sean:
```css
src:url(webfonts/fa-solid-900.woff2)   /* NO: ../webfonts/ */
```

### Problema: OCR no funciona o tarda mucho
**Solución**: 
1. Verificar que los modelos estén en:
   - `%LOCALAPPDATA%\DetectorMovimiento\data_local\easyocr-cache\model\`
   
2. Modelos necesarios (ver [ocr.py](ocr.py) líneas 16-30):
   - `craft_mlt_25k.pth` (detector de texto - 83 MB)
   - `english_g2.pth` (reconocimiento OCR inglés - 15 MB)
   - `latin_g2.pth` (reconocimiento OCR latino - 15 MB)

3. Si OCR tarda demasiado:
   - **Con GPU NVIDIA**: Habilitar GPU siguiendo instrucciones en sección "Sobre GPU y Aceleración"
   - **Con CPU**: Es normal que tarde (45-120 segundos por imagen)
   - Verificar que `gpu=False` en [ocr.py](ocr.py) línea 50 (por defecto sin GPU)

### Problema: PyTorch no carga o error con DLL
**Solución**: Instalar Visual C++ Redistributable manualmente desde `vc_redist.x64.exe`

### Problema: YOLO no detecta objetos
**Solución**: 
1. Verificar que `yolov10n.pt` (24 MB) esté en la raíz del proyecto
2. El modelo se carga en [video_processing.py](video_processing.py) línea 461
3. Por defecto usa CPU (ver `YOLO(yolo_path)`)
4. Para habilitar GPU: cambiar a `YOLO(yolo_path, device=0)`

### Problema: Procesamiento muy lento
**¿Tienes GPU NVIDIA?**
- Sí: Instalar CUDA 11.8+, cuDNN 8.0+, y habilitar GPU (ver sección "Sobre GPU y Aceleración")
- No: El procesamiento con CPU es normal (más lento pero funcional). Es esperado.

**Optimizaciones posibles**:
- Reducir resolución de entrada en [video_processing.py](video_processing.py)
- Reducir FPS de análisis
- Aumentar RAM de la máquina

---

## 📊 Dependencias Principales

| Componente | Versión | Propósito | GPU |
|-----------|---------|----------|-----|
| Python | 3.11 | Lenguaje principal | N/A |
| Flask | 3.1.2 | Framework web | N/A |
| PyTorch | 2.9.1 | Deep Learning (CPU) | CPU (opcional CUDA) |
| OpenCV | 4.12.0.88 | Procesamiento de video | CPU |
| EasyOCR | 1.7.2 | Reconocimiento OCR | CPU (gpu=False) |
| Electron | 28.3.3 | Interfaz de escritorio | N/A |
| Handsontable | 14.3.0 | Tabla de datos | N/A |
| Chart.js | 4.4.0 | Gráficos | N/A |
| Font Awesome | 6.4.0 | Iconos | N/A |
| FFmpeg | 2025-09-28 | Codificación de video | CPU |
| YOLO | v10 | Detección de objetos | CPU (ultralytics) |

---

## 📝 Variables de Entorno (Offline)

El proyecto utiliza:
- `HF_HUB_OFFLINE=1` - Deshabilita descargas de Hugging Face
- `EASYOCR_HOME` - Ruta de modelos de EasyOCR (por defecto: AppData\DetectorMovimiento)
- `LOCALAPPDATA` - Ubicación de datos locales (Windows)
- Módulo `offline_mode.py` - Bloquea urllib.request.urlopen para garantizar modo offline

### Sobre GPU y Aceleración

**Estado Actual (CPU)**:
- EasyOCR utiliza `gpu=False` (procesamiento con CPU) - ver [ocr.py](ocr.py) línea 50
- YOLO (ultralytics) se ejecuta por defecto con CPU - ver [video_processing.py](video_processing.py) línea 461
- Funciona en cualquier máquina Windows 10+, sin requisitos de GPU
- PyTorch se compila para CPU (torch-2.9.1-cp311-cp311-win_amd64.whl)

**Para Habilitar GPU NVIDIA** (opcional - requiere CUDA):
1. Instalar CUDA Toolkit 11.8+ desde: https://developer.nvidia.com/cuda-toolkit
2. Instalar cuDNN 8.0+ desde: https://developer.nvidia.com/cudnn
3. Actualizar drivers de NVIDIA
4. Modificar en [ocr.py](ocr.py) línea 50: cambiar `gpu=False` a `gpu=True`
5. Modificar en [video_processing.py](video_processing.py) línea 461: agregar `device=0` al cargar YOLO
6. Ejecutar: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`

---

## ✅ Checklist de Compilación

Antes de compilar el instalador, verifica:

- [ ] Python portable funciona correctamente
- [ ] `pip install -r requirements.txt` sin errores
- [ ] `npm install` completado
- [ ] `static/libs/fontawesome.min.css` tiene rutas `webfonts/` (sin `../`)
- [ ] `easyocr-cache/` contiene los 3 modelos .pth
- [ ] `vc_redist.x64.exe` está en la raíz del proyecto
- [ ] `launch.bat` está actualizado
- [ ] `offline_mode.py` funciona correctamente
- [ ] Inno Setup 6 está instalado en `C:\Program Files (x86)\Inno Setup 6`

---

## 🎯 Ejecución Rápida (Resumen)

### En Desarrollo
```bash
# Activar entorno
venv\Scripts\activate

# Instalar dependencias (si es primera vez)
pip install -r requirements.txt
npm install

# Ejecutar
.\launch.bat
```

### Para Crear Instalador
```bash
# Compilar
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer-portable-v2.iss

# Resultado en:
# <path-to-project>\dist\DetectorMovimiento-Portable-Setup-1.0.0-v2.exe
```

---

## 📞 Soporte

Para problemas:
1. Revisar los logs en `%LOCALAPPDATA%\DetectorMovimiento\`
2. Verificar que Windows 10+ esté actualizado
3. Confirmar que Visual C++ Redistributable esté instalado
4. Comprobar espacio en disco disponible

---

**Última actualización**: Febrero 2026
**Versión**: 1.0.0-v2
**Estado**: ✅ Completamente Offline y Portable
**Procesamiento**: CPU (GPU NVIDIA opcional)
