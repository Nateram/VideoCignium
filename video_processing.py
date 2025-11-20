# video_processing.py

import cv2
import numpy as np
import os
from datetime import datetime
import subprocess
import ocr
import sys
import logging

# ====================================================================
# 🔥 DEFINIR RUTA BASE DEL PROYECTO Y RUTA ABSOLUTA DE FFMPEG
# ====================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔥 RUTA ABSOLUTA DE FFMPEG (independiente del directorio de trabajo)
FFMPEG_PATH = os.path.join(BASE_DIR, 'ffmpeg-2025-09-28-git-0fdb5829e3-essentials_build', 'bin', 'ffmpeg.exe')

# Logger simple que usa la configuración del módulo principal
logger = logging.getLogger(__name__)

# Importar YOLO con manejo de errores
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    logger.info("Módulo YOLO cargado correctamente")
except ImportError as e:
    logger.error(f"Error al importar YOLO: {e}")
    YOLO_AVAILABLE = False

def get_dominant_color(image):
    """
    Identifica el color dominante de una imagen.
    """
    if image is None or image.size == 0:
        return "Desconocido"
    
    img_resized = cv2.resize(image, (64, 64))
    hsv_image = cv2.cvtColor(img_resized, cv2.COLOR_BGR2HSV)
    
    color_ranges = {
        "rojo": ([0, 70, 50], [10, 255, 255]),
        "rojo_claro": ([170, 70, 50], [180, 255, 255]),
        "verde": ([35, 70, 50], [80, 255, 255]),
        "azul": ([100, 70, 50], [140, 255, 255]),
        "amarillo": ([20, 70, 50], [35, 255, 255]),
        "naranja": ([11, 70, 50], [20, 255, 255]),
        "morado": ([140, 70, 50], [170, 255, 255])
    }
    
    gray_img = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
    color_counts = {}
    for color, (lower, upper) in color_ranges.items():
        mask = cv2.inRange(hsv_image, np.array(lower), np.array(upper))
        color_counts[color] = cv2.countNonZero(mask)

    total_pixels = gray_img.size
    white_pixels = np.sum(gray_img > 200)
    black_pixels = np.sum(gray_img < 50)

    if white_pixels > 0.6 * total_pixels:
        return "Blanco"
    elif black_pixels > 0.6 * total_pixels:
        return "Negro"

    dominant_color = max(color_counts, key=color_counts.get)
    if color_counts[dominant_color] > 0.1 * total_pixels:
        return dominant_color.capitalize()

    return "Gris/Otro"

def select_roi(video_path):
    """
    Permite al usuario seleccionar una Región de Interés (ROI) en un video con botones.
    Tras la selección, muestra el texto detectado en el primer frame usando OCR.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    
    ret, frame = cap.read()
    if not ret:
        return None
        
    # Usar la nueva función con botones
    roi = select_roi_with_buttons(frame, "Seleccione el área de movimiento")
    
    cap.release()
    # Mostrar el texto detectado en el primer frame usando OCR si se seleccionó un ROI válido
    if roi and len(roi) == 4 and roi[2] > 0 and roi[3] > 0:
        texto_detectado = ocr.extract_timestamp_from_roi(frame, roi)
        print(f"[OCR] Texto detectado en el primer frame: {texto_detectado}")
    return roi

def select_roi_with_buttons(frame, window_title="Seleccionar Región"):
    """
    Permite al usuario seleccionar una ROI usando la función estándar de OpenCV.
    """
    roi = cv2.selectROI(window_title, frame, False)
    cv2.destroyAllWindows()
    
    if roi[2] > 0 and roi[3] > 0:
        print(f"ROI seleccionado: {roi}")
        return roi
    else:
        print("Selección cancelada")
        return None

def process_video_for_motion(video_path, roi, threshold=None):
    """
    Procesa un video para detectar eventos de movimiento dentro de la ROI.
    Versión mejorada con umbral adaptativo y sin duración mínima.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    
    # Calcular umbral adaptativo si no se proporciona
    if threshold is None:
        roi_size = (roi[2], roi[3])  # ancho, alto
        threshold = calculate_adaptive_threshold(roi_size, threshold_percentage=1.0)
        
    # Configurar BackgroundSubtractor con parámetros más estables
    fgbg = cv2.createBackgroundSubtractorMOG2(
        varThreshold=16,        # Reducido para mayor estabilidad
        detectShadows=False,    # Desactivar sombras para mayor consistencia
        history=200             # Mayor historia para modelo más estable
    )
    
    # Variables de estado
    is_in_motion = False
    motion_start_time = 0
    last_motion_end_time = 0
    motion_events_ms = []
    cooldown_after_motion_ms = 2000  # Aumentado para evitar clips repetidos (7 segundos)
    
    frame_count = 0
    
    logger.info(f"Iniciando análisis de movimiento - ROI: {roi}")
    logger.info(f"Umbral adaptativo: {threshold} píxeles ({roi[2]}x{roi[3]} ROI)") 
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        
        # Validar ROI
        if (roi[1] + roi[3] > frame.shape[0] or roi[0] + roi[2] > frame.shape[1] or
            roi[0] < 0 or roi[1] < 0 or roi[2] <= 0 or roi[3] <= 0):
            logger.error(f"ROI inválido: {roi} para frame de tamaño {frame.shape}")
            break
            
        roi_frame = frame[roi[1]:roi[1]+roi[3], roi[0]:roi[0]+roi[2]]
        
        # Aplicar suavizado para reducir ruido
        roi_frame = cv2.GaussianBlur(roi_frame, (5, 5), 0)
        
        fgmask = fgbg.apply(roi_frame)
        
        # Procesamiento morfológico mejorado para reducir ruido
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_CLOSE, kernel)
        
        # Threshold más estable
        thresh = cv2.threshold(fgmask, 127, 255, cv2.THRESH_BINARY)[1]
        
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Calcular área total de movimiento para mayor estabilidad
        total_motion_area = sum(cv2.contourArea(contour) for contour in contours)
        movement_detected_this_frame = total_motion_area > threshold
        
        # Log detallado para debugging
        if frame_count % 100 == 0:
            logger.debug(f"Frame {frame_count}, Timestamp: {timestamp_ms:.0f}ms, Área movimiento: {total_motion_area}")

        if movement_detected_this_frame and not is_in_motion:
            if (timestamp_ms - last_motion_end_time) > cooldown_after_motion_ms:
                is_in_motion = True
                motion_start_time = timestamp_ms
                logger.info(f"Inicio de movimiento detectado en {timestamp_ms:.0f}ms")

        if not movement_detected_this_frame and is_in_motion:
            is_in_motion = False
            last_motion_end_time = timestamp_ms
            duration = last_motion_end_time - motion_start_time
            # Eliminar duración mínima - detectar eventos instantáneos como coches
            motion_events_ms.append(motion_start_time)
            logger.info(f"Evento de movimiento registrado: inicio {motion_start_time:.0f}ms, duración {duration:.0f}ms")

    cap.release()
    
    logger.info(f"Análisis completado. Eventos detectados: {len(motion_events_ms)}")
    for i, event_time in enumerate(motion_events_ms):
        logger.info(f"Evento {i+1}: {event_time:.0f}ms")
    
    return motion_events_ms

def get_motion_detection_config():
    """
    Obtiene la configuración de detección de movimiento.
    Primero intenta cargar desde la base de datos, si no usa valores por defecto.
    """
    # Valores base por defecto
    default_config = {
        'threshold_percentage': 1.0,         # Porcentaje del ROI (1% por defecto)
        'var_threshold': 16,                 # Sensibilidad del background subtractor
        'cooldown_ms': 2000,                # Tiempo mínimo entre detecciones (reducido)
        'gaussian_blur': (5, 5),            # Kernel de suavizado
        'morph_kernel_size': (3, 3),        # Kernel para operaciones morfológicas
        'binary_threshold': 127              # Threshold para binarización
    }
    
    try:
        import db
        # Intentar cargar desde la base de datos
        db_config = db.load_motion_detection_config()
        if db_config:
            # Mezclar configuración de BD con valores por defecto para asegurar que todos los parámetros estén presentes
            config = default_config.copy()
            config.update(db_config)
            logger.info(f"Configuración cargada desde BD con valores por defecto complementarios: {config}")
            return config
    except Exception as e:
        logger.info(f"No se pudo cargar configuración de BD, usando por defecto: {e}")
    
    # Usar valores por defecto si no hay configuración en BD
    logger.info(f"Usando configuración por defecto: {default_config}")
    return default_config

def calculate_adaptive_threshold(roi_size, threshold_percentage=1.0):
    """
    Calcula un umbral adaptativo basado en el tamaño del ROI.
    
    Args:
        roi_size: tupla (ancho, alto) del ROI
        threshold_percentage: porcentaje del área total del ROI (por defecto 1%)
    
    Returns:
        int: umbral de área calculado
    """
    roi_area = roi_size[0] * roi_size[1]
    adaptive_threshold = int(roi_area * (threshold_percentage / 100))
    
    # Establecer límites mínimo y máximo razonables
    min_threshold = 50   # Mínimo para evitar ruido
    max_threshold = 5000 # Máximo para ROIs muy grandes
    
    adaptive_threshold = max(min_threshold, min(adaptive_threshold, max_threshold))
    
    logger.info(f"ROI: {roi_size[0]}x{roi_size[1]} (área: {roi_area})")
    logger.info(f"Umbral adaptativo calculado: {adaptive_threshold} ({threshold_percentage}% del ROI)")
    
    return adaptive_threshold

def process_video_for_motion_advanced(video_path, roi, config=None):
    """
    Versión avanzada con configuración personalizable para mayor reproducibilidad.
    """
    if config is None:
        config = get_motion_detection_config()
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    
    # Calcular umbral adaptativo basado en el porcentaje del ROI
    roi_size = (roi[2], roi[3])
    threshold = calculate_adaptive_threshold(roi_size, config['threshold_percentage'])
    
    # Configurar BackgroundSubtractor con parámetros configurables
    fgbg = cv2.createBackgroundSubtractorMOG2(
        varThreshold=config['var_threshold'],
        detectShadows=False,
        history=200
    )
    
    # Variables de estado
    is_in_motion = False
    motion_start_time = 0
    last_motion_end_time = 0
    last_event_registered_time = 0  # Nuevo: tiempo del último evento REGISTRADO
    motion_events_ms = []
    frame_count = 0
    
    logger.info(f"Análisis avanzado - ROI: {roi}")
    logger.info(f"Umbral adaptativo: {threshold} píxeles (config: {config})")
    
    last_event_registered_time = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)

        # Validar ROI
        if (roi[1] + roi[3] > frame.shape[0] or roi[0] + roi[2] > frame.shape[1] or
            roi[0] < 0 or roi[1] < 0 or roi[2] <= 0 or roi[3] <= 0):
            logger.error(f"ROI inválido: {roi}")
            break

        roi_frame = frame[roi[1]:roi[1]+roi[3], roi[0]:roi[0]+roi[2]]
        roi_frame = cv2.GaussianBlur(roi_frame, config['gaussian_blur'], 0)

        fgmask = fgbg.apply(roi_frame)

        # Procesamiento morfológico
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, config['morph_kernel_size'])
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_CLOSE, kernel)

        thresh = cv2.threshold(fgmask, config['binary_threshold'], 255, cv2.THRESH_BINARY)[1]
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        total_motion_area = sum(cv2.contourArea(contour) for contour in contours)
        movement_detected_this_frame = total_motion_area > threshold

        if movement_detected_this_frame and not is_in_motion:
            # Iniciar nuevo período de movimiento
            is_in_motion = True
            motion_start_time = timestamp_ms
            logger.debug(f"Movimiento iniciado en {timestamp_ms:.0f}ms")

        if not movement_detected_this_frame and is_in_motion:
            # Fin del movimiento - verificar cooldown antes de registrar
            is_in_motion = False
            last_motion_end_time = timestamp_ms

            # Solo registrar evento si han pasado cooldown_ms desde el último evento registrado
            if last_event_registered_time is None or (motion_start_time - last_event_registered_time) >= config['cooldown_ms']:
                # Registrar evento
                # Evitar duplicados en la misma fecha/hora (redondeando a segundos)
                if len(motion_events_ms) == 0 or abs(motion_start_time - motion_events_ms[-1]) >= config['cooldown_ms']:
                    motion_events_ms.append(motion_start_time)
                    last_event_registered_time = motion_start_time
                    logger.info(f"✓ Evento registrado en {motion_start_time:.0f}ms (cooldown: {(motion_start_time - (last_event_registered_time if last_event_registered_time else 0)):.0f}ms)")
                else:
                    logger.debug(f"✗ Evento duplicado/omito en {motion_start_time:.0f}ms")
            else:
                logger.debug(f"✗ Evento ignorado en {motion_start_time:.0f}ms (cooldown insuficiente: {(motion_start_time - last_event_registered_time):.0f}ms < {config['cooldown_ms']}ms)")

    cap.release()
    logger.info(f"Análisis completado. Eventos: {len(motion_events_ms)}")
    return motion_events_ms

def find_yolo_model():
    """
    Busca el modelo YOLO usando rutas absolutas.
    Ya NO depende del directorio de trabajo actual.
    Busca en: 1) Directorio del proyecto, 2) Cache de ultralytics, 3) Descarga automática
    """
    if not YOLO_AVAILABLE:
        logger.warning("Módulo YOLO no disponible")
        return None
    
    # Nombre del modelo YOLO a usar
    model_name = "yolov10n.pt"
    
    # Prioridad 1: Buscar en el directorio del proyecto (mismo nivel que app.py)
    project_model_path = os.path.join(BASE_DIR, model_name)
    if os.path.exists(project_model_path):
        logger.info(f"✓ Modelo YOLO encontrado en proyecto: {project_model_path}")
        return project_model_path
    
    # Prioridad 2: Buscar en cache de ultralytics
    cache_dir = os.path.expanduser("~/.cache/ultralytics")
    cache_model_path = os.path.join(cache_dir, model_name)
    if os.path.exists(cache_model_path):
        logger.info(f"✓ Modelo YOLO encontrado en cache: {cache_model_path}")
        return cache_model_path
    
    # Prioridad 3: Detectar si estamos en Docker/Linux
    is_docker = os.path.exists('/.dockerenv') or os.environ.get('FLASK_ENV') == 'production'
    
    if is_docker:
        logger.info(f"Entorno Docker - ultralytics descargará automáticamente: {model_name}")
        return model_name  # ultralytics lo descargará automáticamente
    
    # Si no se encuentra localmente, devolver nombre para descarga automática
    logger.info(f"Modelo YOLO no encontrado localmente - ultralytics lo descargará automáticamente: {model_name}")
    logger.info(f"  Buscado en: {project_model_path}")
    logger.info(f"  Buscado en: {cache_model_path}")
    return model_name

def classify_vehicle_type(class_name, box_area):
    """
    Clasifica mejor los vehículos basándose en el nombre de clase YOLO y el área del bounding box.
    Enfocado en objetos comunes en videos de cámaras de seguridad.
    Basado en las clases que YOLO puede detectar realmente.
    """
    # Mapeo de clases YOLO a nuestras categorías (solo objetos que YOLO detecta)
    vehicle_mapping = {
        'car': 'coche',
        'truck': 'camión', 
        'bus': 'autobús',
        'motorcycle': 'moto',
        'bicycle': 'bicicleta',
    }
    
    if class_name == 'person':
        return 'persona'
    elif class_name in vehicle_mapping:
        return vehicle_mapping[class_name]
    elif 'vehicle' in class_name.lower():
        # Para vehículos genéricos, clasificar por tamaño
        if box_area > 50000:  # Área grande
            return 'camión'
        elif box_area > 20000:  # Área mediana
            return 'furgoneta'
        else:  # Área pequeña
            return 'coche'
    else:
        return 'otro'

def analyze_motion_event(video_path, event_ms, roi_coords):
    """
    Analiza un evento de movimiento para detectar vehículos y personas en la ROI.
    Devuelve una lista de tuplas (objeto, color dominante).
    Incluye detección mejorada de: coches, furgonetas, camiones, motos, personas.
    """
    try:
        yolo_path = find_yolo_model()
        if yolo_path is None:
            logger.warning("Modelo YOLO no encontrado, utilizando valores predeterminados")
            return [("otro", "desconocido")]
            
        model = YOLO(yolo_path)  # Cargar el modelo YOLO con la ruta encontrada
    except Exception as e:
        logger.error(f"Error al cargar modelo YOLO: {e}")
        return [("otro", "desconocido")]  # Valor fallback si falla la carga del modelo
        
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    cap.set(cv2.CAP_PROP_POS_MSEC, event_ms)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return []
        
    try:
        results = model(frame, verbose=False)
        objetos_detectados = []
        
        # Categorías que queremos detectar (enfocado en seguridad)
        target_classes = ["car", "truck", "bus", "motorcycle", "bicycle", "person"]
        
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = [int(coord) for coord in box.xyxy[0]]
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                confidence = float(box.conf[0])
                
                # Solo objetos con confianza alta y en nuestras categorías de interés
                if class_name in target_classes and confidence > 0.3:
                    # Verificar si está dentro de la ROI
                    if (roi_coords[0] <= x1 < roi_coords[0] + roi_coords[2] and 
                        roi_coords[1] <= y1 < roi_coords[1] + roi_coords[3]):
                        
                        # Calcular área del bounding box para mejor clasificación
                        box_area = (x2 - x1) * (y2 - y1)
                        
                        # Clasificar el objeto de forma más específica
                        classified_type = classify_vehicle_type(class_name, box_area)
                        
                        # Obtener color dominante
                        cropped_object = frame[y1:y2, x1:x2]
                        color = get_dominant_color(cropped_object)
                        
                        objetos_detectados.append((classified_type, color))
                        
        if not objetos_detectados:
            return [("otro", "n/a")]
        return objetos_detectados
    except Exception as e:
        logger.error(f"Error en detección de objetos: {e}")
        return [("Otro", "Desconocido")]  # Valor fallback si falla la detección

def select_timestamp_roi(video_path):
    """
    Permite al usuario seleccionar la región donde aparece la fecha/hora en el video.
    Usa la interfaz mejorada con botones.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    
    ret, frame = cap.read()
    if not ret:
        cap.release()
        return None
    
    # Usar la nueva función con botones específicamente para timestamp
    roi = select_roi_with_buttons(frame, "Seleccione el area donde aparece la fecha/hora")
    
    cap.release()
    
    # Mostrar texto detectado para verificación
    if roi and len(roi) == 4 and roi[2] > 0 and roi[3] > 0:
        texto_detectado = ocr.extract_timestamp_from_roi(frame, roi)
        print(f"[OCR] Texto de fecha/hora detectado: {texto_detectado}")
    
    return roi

def get_ffmpeg_path():
    """
    Devuelve la ruta absoluta de ffmpeg en el proyecto.
    Ya NO depende del directorio de trabajo actual.
    """
    # Verificar que ffmpeg existe en la ruta configurada
    if os.path.exists(FFMPEG_PATH):
        logger.info(f"✓ ffmpeg encontrado: {FFMPEG_PATH}")
        return FFMPEG_PATH
    else:
        logger.warning(f"⚠️ ffmpeg NO encontrado en {FFMPEG_PATH}")
        # Intentar usar ffmpeg del PATH del sistema como fallback
        logger.warning("  Intentando usar ffmpeg del PATH del sistema...")
        return 'ffmpeg'

def create_clip_from_event(video_path, event_ms, clip_duration_ms=16000, roi_coords=None):
    """
    Crea un clip de video de una duración específica alrededor de un evento.
    El parámetro roi_coords se acepta para compatibilidad pero no se usa.
    """
    logger.info(f"Creando clip para evento en tiempo {event_ms}ms del video: {video_path}")
    
    temp_source_path = None
    if video_path.lower().endswith('.dav'):
        temp_source_path = os.path.join(os.path.dirname(video_path), f"temp_clip_source_{os.path.basename(video_path)}.mp4")
        try:
            logger.info(f"Convirtiendo video DAV a MP4 temporal: {temp_source_path}")
            # Obtener la ruta de ffmpeg (local o sistema)
            ffmpeg_cmd = get_ffmpeg_path()
            logger.info(f"Usando ffmpeg desde: {ffmpeg_cmd}")
            
            # Usar CREATE_NO_WINDOW flag para evitar que aparezcan ventanas de consola
            creation_flags = 0x08000000 if sys.platform == 'win32' else 0  # 0x08000000 es CREATE_NO_WINDOW
            subprocess.run([ffmpeg_cmd, '-i', video_path, '-c', 'copy', '-y', temp_source_path, '-loglevel', 'quiet'], 
                           check=True, 
                           creationflags=creation_flags)
            video_path = temp_source_path
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Error al convertir el archivo DAV. Asegúrate de que ffmpeg esté instalado: {e}")
            return None
    
    start_time_ms = max(0, event_ms - clip_duration_ms / 2)
    end_time_ms = event_ms + clip_duration_ms / 2
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Error: No se pudo abrir el video: {video_path}")
        if temp_source_path and os.path.exists(temp_source_path):
            os.remove(temp_source_path)
        return None
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_duration_ms = (total_frames / fps * 1000) if fps > 0 else 0
    
    logger.info(f"Video: FPS={fps}, Total frames={total_frames}, Duration={total_duration_ms/1000}s")
    logger.info(f"Clip: Inicio={start_time_ms/1000}s, Fin={end_time_ms/1000}s")
    
    if end_time_ms > total_duration_ms:
        end_time_ms = total_duration_ms
        start_time_ms = max(0, end_time_ms - clip_duration_ms)
        
    cap.set(cv2.CAP_PROP_POS_MSEC, start_time_ms)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    event_time = datetime.fromtimestamp(os.path.getmtime(video_path) + event_ms / 1000)
    
    # Agregar parte del nombre del video original al nombre del clip para mejor identificación
    video_name_part = os.path.splitext(os.path.basename(video_path))[0]
    # Limitar la longitud y eliminar caracteres problemáticos
    video_name_part = ''.join(e for e in video_name_part if e.isalnum() or e in '._- ')[:20]
    
    clip_filename = f"{event_time.strftime('%H-%M-%S_%d-%m-%Y')}_{video_name_part}_clip.mp4"
    clip_path = os.path.join(os.path.dirname(video_path), "clips_analisis", clip_filename)
    
    if not os.path.exists(os.path.dirname(clip_path)):
        os.makedirs(os.path.dirname(clip_path))
        
    out = cv2.VideoWriter(clip_path, fourcc, fps, (frame_width, frame_height))
    
    frames_written = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        current_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        if current_ms < start_time_ms:
            continue
        if current_ms > end_time_ms:
            break
            
        out.write(frame)
        frames_written += 1
        
    out.release()
    cap.release()
    
    if frames_written == 0:
        logger.error(f"No se escribieron frames en el clip {clip_path}")
        if os.path.exists(clip_path):
            os.remove(clip_path)
        if temp_source_path and os.path.exists(temp_source_path):
            os.remove(temp_source_path)
        return None
        
    logger.info(f"Clip creado exitosamente: {clip_filename} ({frames_written} frames)")
    
    # Recodificar con FFmpeg para compatibilidad con navegadores web (H.264)
    try:
        clip_h264_path = clip_path.replace('.mp4', '_web.mp4')
        logger.info(f"Recodificando clip a H.264 para compatibilidad web...")
        
        # 🔥 USAR RUTA ABSOLUTA DE FFMPEG
        ffmpeg_cmd = [
            get_ffmpeg_path(), '-y',
            '-i', clip_path,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',  # Crítico para Safari/iOS
            '-movflags', '+faststart',  # Permite streaming progresivo
            clip_h264_path
        ]
        
        # Usar CREATE_NO_WINDOW flag para evitar que aparezca la ventana de terminal
        creation_flags = 0x08000000 if sys.platform == 'win32' else 0
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, creationflags=creation_flags)
        
        if result.returncode == 0 and os.path.exists(clip_h264_path):
            # Eliminar clip original mp4v y usar el H.264
            os.remove(clip_path)
            os.rename(clip_h264_path, clip_path)
            logger.info(f"✅ Clip recodificado a H.264 correctamente")
        else:
            logger.warning(f"⚠️ No se pudo recodificar a H.264, usando mp4v original")
            logger.warning(f"FFmpeg error: {result.stderr}")
    except Exception as e:
        logger.warning(f"⚠️ Error al recodificar con FFmpeg: {e}")
        logger.warning("Se usará el clip original (puede no reproducirse en algunos navegadores)")
    
    if temp_source_path and os.path.exists(temp_source_path):
        os.remove(temp_source_path)
        
    return clip_path

def extract_timestamp_from_frame(frame, roi_coords=None, roi_override=None):
    """
    Extrae el texto de la zona de fecha/hora usando OCR.
    Si roi_coords no se especifica, intenta usar la zona de timestamp guardada.
    Reintenta con diferentes preprocesamientos hasta obtener una fecha válida.
    
    Args:
        frame: Frame de video (numpy array)
        roi_coords: Coordenadas ROI (compatibilidad, usa roi_override si existe)
        roi_override: Tupla (x, y, w, h) para sobreescribir configuración guardada
    """
    import re
    if frame is None:
        logger.warning("Frame nulo pasado a extract_timestamp_from_frame")
        return None
    
    # Prioridad: roi_override > roi_coords > archivo config
    if roi_override:
        roi_coords = roi_override
    elif roi_coords is None:
        # 🔥 USAR RUTA ABSOLUTA PARA ARCHIVO DE CONFIGURACIÓN
        config_path = os.path.join(BASE_DIR, "timestamp_roi_config.json")
        if os.path.exists(config_path):
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
                roi_coords = tuple([config.get('x', 0), config.get('y', 0), 
                                   config.get('w', 0), config.get('h', 0)])
    
    if not roi_coords or roi_coords[2] <= 0 or roi_coords[3] <= 0:
        logger.warning("ROI de timestamp inválido o no configurado")
        return None
    
    try:
        x, y, w, h = roi_coords
        roi = frame[y:y+h, x:x+w]
        # Lista de preprocesamientos
        attempts = [roi,
                    cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY),
                    cv2.threshold(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 127, 255, cv2.THRESH_BINARY)[1],
                    cv2.threshold(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 127, 255, cv2.THRESH_BINARY_INV)[1]]
        for img in attempts:
            text = ocr.extract_timestamp_from_roi(img, (0,0,img.shape[1],img.shape[0]))
            fixed = fix_timestamp_format(text)
            # Validar formato dd-mm-yyyy hh:mm:ss
            if fixed and re.match(r'\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}', fixed):
                logger.info(f"Fecha extraída correctamente: {fixed}")
                return fixed
        
        # Si llegamos aquí, no se pudo extraer una fecha válida
        if text:
            logger.warning(f"Texto extraído pero no es una fecha válida: {text}")
        else:
            logger.warning("No se pudo extraer texto del ROI de timestamp")
        return fix_timestamp_format(text) if text else None
    except Exception as e:
        logger.error(f"Error al extraer timestamp: {e}")
        return None

def fix_timestamp_format(text):
    """
    Corrige el formato de fecha/hora detectado por OCR para que sea dd-mm-yyyy hh:mm:ss
    Solo asegura los separadores correctos y la cantidad de dígitos en la hora.
    """
    import re
    if not text:
        return None
    # Eliminar espacios extra
    text = re.sub(r'\s+', ' ', text)
    # Buscar patrón completo de fecha y hora
    match = re.search(r'(\d{2}-\d{2}-\d{4})[\sT]*(\d{2}:\d{2}:\d{2})', text)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    # Buscar todos los números
    nums = re.findall(r'\d+', text)
    if len(nums) >= 6:
        fecha = f"{nums[0]:0>2}-{nums[1]:0>2}-{nums[2]:0>4}"
        h = nums[3][:2]
        m = nums[4][:2]
        s = nums[5][:2]
        return f"{fecha} {h}:{m}:{s}"
    # Si no hay suficientes números, devolver None
    return None

def extract_timestamp_from_video_at_ms(video_path, event_ms, roi_override=None):
    """
    Extrae el timestamp del OCR de un frame específico del video en el tiempo dado (en ms).
    OPTIMIZACIÓN: Extrae el timestamp del primer frame y calcula el resto sumando el offset.
    Retorna la fecha en formato 'dd-mm-yyyy hh:mm:ss' o None si falla.
    
    Args:
        video_path: Ruta al video
        event_ms: Tiempo en milisegundos donde extraer el frame
        roi_override: Tupla (x, y, w, h) para usar en vez del ROI guardado (opcional)
    """
    frame = None
    cap = None
    
    # Log de configuración ROI al inicio
    if roi_override:
        logger.info(f"📍 ROI override especificado: x={roi_override[0]}, y={roi_override[1]}, w={roi_override[2]}, h={roi_override[3]}")
    else:
        # Verificar si existe configuración guardada
        # 🔥 USAR RUTA ABSOLUTA PARA ARCHIVO DE CONFIGURACIÓN
        config_path = os.path.join(BASE_DIR, "timestamp_roi_config.json")
        if os.path.exists(config_path):
            try:
                import json
                with open(config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"📍 ROI de timestamp configurado: x={config.get('x', 0)}, y={config.get('y', 0)}, w={config.get('w', 0)}, h={config.get('h', 0)}")
            except Exception as e:
                logger.warning(f"⚠️ Error al leer configuración ROI: {e}")
        else:
            logger.warning(f"⚠️ NO HAY ROI DE TIMESTAMP CONFIGURADO - timestamp_roi_config.json no existe en {config_path}")
    
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"No se pudo abrir el video: {video_path}")
            return None
        
        # ESTRATEGIA OPTIMIZADA: Leer timestamp del primer frame y calcular el resto
        logger.info(f"⏱️ Calculando timestamp para evento en {event_ms}ms ({event_ms/1000.0:.2f}s):")
        
        # 1. Extraer timestamp del PRIMER frame (frame 0)
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, first_frame = cap.read()
        
        if not ret or first_frame is None:
            logger.error("❌ No se pudo leer el primer frame del video")
            return None
        
        # Extraer timestamp del primer frame usando OCR
        start_timestamp_str = extract_timestamp_from_frame(first_frame, roi_override=roi_override)
        
        if not start_timestamp_str:
            logger.warning("⚠️ No se pudo extraer timestamp del primer frame, intentando con frame del evento...")
            # Fallback: intentar con el frame específico del evento
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 25
            target_frame = int((event_ms / 1000.0) * fps)
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            
            if ret and frame is not None:
                timestamp = extract_timestamp_from_frame(frame, roi_override=roi_override)
                cap.release()
                return timestamp
            else:
                cap.release()
                return None
        
        logger.info(f"   ✓ Timestamp del primer frame: {start_timestamp_str}")
        
        # 2. Parsear el timestamp del primer frame
        from datetime import datetime, timedelta
        try:
            # Formato esperado: 'dd-mm-yyyy hh:mm:ss'
            start_datetime = datetime.strptime(start_timestamp_str, '%d-%m-%Y %H:%M:%S')
        except ValueError as e:
            logger.error(f"❌ Error al parsear timestamp '{start_timestamp_str}': {e}")
            cap.release()
            return None
        
        # 3. Calcular timestamp del evento sumando el offset
        event_seconds = event_ms / 1000.0
        event_datetime = start_datetime + timedelta(seconds=event_seconds)
        
        # 4. Formatear de vuelta a string
        result_timestamp = event_datetime.strftime('%d-%m-%Y %H:%M:%S')
        
        logger.info(f"   📊 Cálculo:")
        logger.info(f"      - Inicio del video: {start_timestamp_str}")
        logger.info(f"      - Offset del evento: +{event_seconds:.2f}s")
        logger.info(f"      - Timestamp calculado: {result_timestamp}")
        
        cap.release()
        return result_timestamp
        
    except Exception as e:
        logger.error(f"Error al extraer timestamp en {event_ms}ms: {e}")
        if cap is not None:
            cap.release()
        return None

def get_timestamp_roi():
    """
    Devuelve la zona de timestamp guardada en el archivo de configuración.
    """
    # 🔥 USAR RUTA ABSOLUTA PARA ARCHIVO DE CONFIGURACIÓN
    config_path = os.path.join(BASE_DIR, "timestamp_roi_config.json")
    if os.path.exists(config_path):
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
            roi = tuple(config.get("timestamp_roi", [0,0,0,0]))
            return roi
    return None

def analyze_clip_object(clip_path, roi_coords):
    """
    Analiza el objeto y color dominante en la ROI a lo largo de todo el clip.
    Devuelve el objeto y color más frecuente detectado en la ROI.
    """
    from collections import Counter
    try:
        yolo_path = find_yolo_model()
        if yolo_path is None:
            logger.warning("Modelo YOLO no encontrado, utilizando valores predeterminados")
            return "Otro", "Desconocido"
            
        model = YOLO(yolo_path)  # Cargar el modelo YOLO con la ruta encontrada
    except Exception as e:
        logger.error(f"Error al cargar modelo YOLO: {e}")
        return "Otro", "Desconocido"
        
    cap = cv2.VideoCapture(clip_path)
    if not cap.isOpened():
        return "Otro", "N/A"
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_indices = list(range(0, total_frames, int(fps)))  # Un frame por segundo
    objetos = []
    colores = []
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue
        x, y, w, h = roi_coords
        roi_frame = frame[y:y+h, x:x+w]
        results = model(roi_frame, verbose=False)
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                if class_name in ["car", "truck", "person"]:
                    x1, y1, x2, y2 = [int(coord) for coord in box.xyxy[0]]
                    cropped_object = roi_frame[y1:y2, x1:x2]
                    color = get_dominant_color(cropped_object)
                    objetos.append(class_name)
                    colores.append(color)
    cap.release()
    if not objetos:
        return "Otro", "N/A"
    objeto_final = Counter(objetos).most_common(1)[0][0]
    color_final = Counter(colores).most_common(1)[0][0]
    return objeto_final, color_final

def debug_analyze_clip_objects(clip_path, roi_coords):
    """
    Analiza todos los objetos detectados en la ROI del clip y muestra el conteo por tipo en consola (debug).
    """
    from collections import Counter
    try:
        yolo_path = find_yolo_model()
        if yolo_path is None:
            logger.warning("Modelo YOLO no encontrado, saltando análisis de objetos")
            return
            
        model = YOLO(yolo_path)  # Cargar el modelo YOLO con la ruta encontrada
    except Exception as e:
        logger.error(f"Error al cargar modelo YOLO: {e}")
        return
    
    cap = cv2.VideoCapture(clip_path)
    if not cap.isOpened():
        logger.warning(f"No se pudo abrir el clip: {clip_path}")
        return
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_indices = list(range(0, total_frames, int(fps)))  # Un frame por segundo
    objetos = []
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue
        x, y, w, h = roi_coords
        roi_frame = frame[y:y+h, x:x+w]
        results = model(roi_frame, verbose=False)
        frame_objetos = []
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                if class_name in ["car", "truck", "person"]:
                    objetos.append(class_name)
                    frame_objetos.append(class_name)
        logger.info(f"Frame {idx}: objetos detectados en ROI: {frame_objetos}")
    cap.release()
    logger.info(f"Conteo total de objetos en el clip {os.path.basename(clip_path)}: {Counter(objetos)}")

def process_event_with_clip_analysis(clip_path, event_ms_unused, roi_coords, clip_duration_ms_unused=16000):
    """
    Analiza el objeto y color dominante en el clip completo en la ROI.
    Muestra el conteo de objetos detectados en consola (debug).
    """
    try:
        debug_analyze_clip_objects(clip_path, roi_coords)
        objeto, color = analyze_clip_object(clip_path, roi_coords)
        logger.info(f"Objeto/color más frecuente en el clip: {objeto}, {color}")
        return objeto, color
    except Exception as e:
        logger.error(f"Error al analizar clip {clip_path}: {e}")
        return "Otro", "Desconocido"  # Valor fallback en caso de error

def analyze_frame_at_timestamp(video_path, event_ms, roi_coords):
    """
    Analiza un frame específico del video en el timestamp dado sin crear clip.
    Devuelve el objeto y color detectado en la ROI.
    Útil para modo 'sin clips' donde solo se registran eventos.
    """
    from collections import Counter
    try:
        yolo_path = find_yolo_model()
        if yolo_path is None:
            logger.warning("Modelo YOLO no encontrado, utilizando valores predeterminados")
            return "Otro", "Desconocido"
            
        model = YOLO(yolo_path)
    except Exception as e:
        logger.error(f"Error al cargar modelo YOLO: {e}")
        return "Otro", "Desconocido"
    
    # Abrir video y posicionar en el timestamp del evento
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"No se pudo abrir video: {video_path}")
        return "Otro", "N/A"
    
    # Posicionar en el frame del evento
    cap.set(cv2.CAP_PROP_POS_MSEC, event_ms)
    ret, frame = cap.read()
    
    if not ret:
        logger.warning(f"No se pudo leer frame en {event_ms}ms")
        cap.release()
        return "Otro", "N/A"
    
    # Extraer ROI del frame
    x, y, w, h = roi_coords
    roi_frame = frame[y:y+h, x:x+w]
    
    # Analizar objetos en la ROI
    objetos = []
    colores = []
    
    results = model(roi_frame, verbose=False)
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = model.names[class_id]
            confidence = float(box.conf[0])
            
            # Solo detectar objetos de interés con buena confianza
            if class_name in ["car", "truck", "bus", "motorcycle", "person"] and confidence > 0.3:
                x1, y1, x2, y2 = [int(coord) for coord in box.xyxy[0]]
                
                # Extraer el objeto del frame ROI
                cropped_object = roi_frame[y1:y2, x1:x2]
                if cropped_object.size > 0:
                    color = get_dominant_color(cropped_object)
                    objetos.append(class_name)
                    colores.append(color)
                    logger.info(f"Detectado en frame {event_ms}ms: {class_name} ({color}) - confianza: {confidence:.2f}")
    
    cap.release()
    
    # Si se detectaron objetos, devolver el más común
    if objetos:
        objeto_final = Counter(objetos).most_common(1)[0][0]
        color_final = Counter(colores).most_common(1)[0][0] if colores else "Desconocido"
        return objeto_final, color_final
    
    # No se detectó nada
    logger.info(f"No se detectaron objetos en frame {event_ms}ms")
    return None, None



def analyze_frame_at_timestamp(video_path, event_ms, roi_coords):
    """
    Analiza un frame específico del video en el timestamp dado sin crear clip.
    Devuelve el objeto y color detectado en la ROI.
    Útil para modo 'sin clips' donde solo se registran eventos.
    """
    from collections import Counter
    try:
        yolo_path = find_yolo_model()
        if yolo_path is None:
            logger.warning("Modelo YOLO no encontrado, utilizando valores predeterminados")
            return "Otro", "Desconocido"
            
        model = YOLO(yolo_path)
    except Exception as e:
        logger.error(f"Error al cargar modelo YOLO: {e}")
        return "Otro", "Desconocido"
    
    # Abrir video y posicionar en el timestamp del evento
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"No se pudo abrir video: {video_path}")
        return "Otro", "N/A"
    
    # Posicionar en el frame del evento
    cap.set(cv2.CAP_PROP_POS_MSEC, event_ms)
    ret, frame = cap.read()
    
    if not ret:
        logger.warning(f"No se pudo leer frame en {event_ms}ms")
        cap.release()
        return "Otro", "N/A"
    
    # Extraer ROI del frame
    x, y, w, h = roi_coords
    roi_frame = frame[y:y+h, x:x+w]
    
    # Analizar objetos en la ROI
    objetos = []
    colores = []
    
    results = model(roi_frame, verbose=False)
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = model.names[class_id]
            confidence = float(box.conf[0])
            
            # Solo detectar objetos de interés con buena confianza
            if class_name in ["car", "truck", "bus", "motorcycle", "person"] and confidence > 0.3:
                x1, y1, x2, y2 = [int(coord) for coord in box.xyxy[0]]
                
                # Extraer el objeto del frame ROI
                cropped_object = roi_frame[y1:y2, x1:x2]
                if cropped_object.size > 0:
                    color = get_dominant_color(cropped_object)
                    objetos.append(class_name)
                    colores.append(color)
                    logger.info(f"Detectado en frame {event_ms}ms: {class_name} ({color}) - confianza: {confidence:.2f}")
    
    cap.release()
    
    # Si se detectaron objetos, devolver el más común
    if objetos:
        objeto_final = Counter(objetos).most_common(1)[0][0]
        color_final = Counter(colores).most_common(1)[0][0] if colores else "Desconocido"
        return objeto_final, color_final
    
    # No se detectó nada
    logger.info(f"No se detectaron objetos en frame {event_ms}ms")
    return None, None
