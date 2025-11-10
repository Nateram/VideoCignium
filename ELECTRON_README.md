# Detector de Movimiento - Aplicación de Escritorio

Aplicación de escritorio para detección de movimiento en videos, construida con Electron + Flask + Python.

## 🚀 Desarrollo

### Requisitos previos
- Python 3.8 o superior
- Node.js 16 o superior
- npm

### Instalación

1. **Instalar dependencias de Python:**
```bash
pip install -r requirements.txt
```

2. **Instalar dependencias de Node.js:**
```bash
npm install
```

### Ejecutar en modo desarrollo

```bash
npm start
```

## 📦 Compilar aplicación

### Compilar para Windows:
```bash
npm run build:win
```

El ejecutable estará en la carpeta `dist/`

## 🏗️ Estructura del proyecto

```
web_app/
├── electron/           # Código de Electron
│   ├── main.js        # Proceso principal
│   ├── preload.js     # Script de preload
│   └── icon.ico       # Icono de la app
├── static/            # Archivos estáticos web
├── templates/         # Templates HTML
├── app.py             # Servidor Flask
├── video_processing.py
├── db.py
├── package.json       # Configuración de Electron
└── requirements.txt   # Dependencias Python
```

## ⚙️ Características

- ✅ Interfaz nativa de escritorio
- ✅ Backend Flask integrado
- ✅ Sin necesidad de abrir navegador
- ✅ Instalador para Windows
- ✅ Icono personalizado
- ✅ Cierre limpio de procesos

## 📝 Notas

- La aplicación inicia automáticamente el servidor Flask
- Al cerrar la ventana, Flask se detiene automáticamente
- Los logs de Flask aparecen en la consola de Electron
- En modo desarrollo usa `npm start` para ver logs detallados
