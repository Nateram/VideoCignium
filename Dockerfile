# Dockerfile para la aplicación web de análisis de video
FROM python:3.11-slim

# Instalar dependencias del sistema necesarias para OpenCV y otras librerías
RUN apt-get update && apt-get install -y \
    # Para OpenCV
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    # Para procesamiento de video
    ffmpeg \
    # Para compilación de paquetes
    build-essential \
    # Para PyTorch (CPU)
    libopenblas-dev \
    # Utilidades
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt .

# Actualizar pip y instalar dependencias de Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Descargar modelo YOLO durante la construcción (después de copiar el código)
# Esto asegura que el modelo esté incluido en la imagen Docker para portabilidad
RUN echo "Descargando modelo YOLO..." && \
    python3 -c "from ultralytics import YOLO; model = YOLO('yolov10n.pt'); print('✅ Modelo YOLO descargado y almacenado en cache')" && \
    echo "Modelo YOLO incluido en la imagen Docker" || \
    echo "⚠️ Advertencia: Modelo YOLO se descargará en el primer uso"

# Crear directorios necesarios
RUN mkdir -p static/uploads/temp static/uploads/session_* logs data

# Exponer puerto
EXPOSE 5000

# Variables de entorno
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Comando para ejecutar la aplicación
CMD ["python", "run.py"]
