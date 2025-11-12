
# app.py - Aplicación Flask para Detector de Movimiento
# VERSIÓN: 20251107-chunks-20MB-fix-spaces
import os
import sys
import json
import subprocess
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for, Response, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime
from urllib.parse import unquote
import threading
import logging
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
import pandas as pd
import requests
import numpy as np
from collections import deque

# ====================================================================
# 🔥 DEFINIR RUTA BASE DEL PROYECTO (INDEPENDIENTE DEL DIRECTORIO DE TRABAJO)
# ====================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Buffer para logs de eventos en directo
live_event_logs = deque(maxlen=100)

# Agregar el directorio actual al path para importar módulos
sys.path.insert(0, BASE_DIR)

import db
import video_processing
from excel_report import create_excel_report, create_session_excel_report, create_or_update_session_excel, create_or_update_session_excel

# ====================================================================
# 🔥 CONFIGURAR RUTAS ABSOLUTAS PARA FLASK
# ====================================================================
STATIC_DIR = os.path.join(BASE_DIR, 'static')
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

# 🔥 CONFIGURAR PREFIJO DE RUTA PARA PROXY INVERSO
# Si la app está detrás de un proxy con prefijo (ej: /proyect1/), configurar aquí
from werkzeug.middleware.proxy_fix import ProxyFix

# Detectar si estamos detrás de un proxy con prefijo
# Puedes configurar esto con una variable de entorno
APPLICATION_ROOT = os.environ.get('APPLICATION_ROOT', '/')

app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATE_DIR)

# Si hay un prefijo de aplicación, configurarlo
if APPLICATION_ROOT != '/':
    app.config['APPLICATION_ROOT'] = APPLICATION_ROOT

# Configurar para trabajar detrás de proxy inverso (Nginx)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# 🔥 Middleware para manejar prefijo de ruta automáticamente
class PrefixMiddleware:
    def __init__(self, app, prefix=''):
        self.app = app
        self.prefix = prefix.rstrip('/')

    def __call__(self, environ, start_response):
        # Si la ruta comienza con el prefijo, quitarlo para Flask
        if self.prefix and environ['PATH_INFO'].startswith(self.prefix):
            environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
            if not environ['PATH_INFO']:
                environ['PATH_INFO'] = '/'
            environ['SCRIPT_NAME'] = self.prefix
        return self.app(environ, start_response)

# Aplicar middleware si hay prefijo configurado
PREFIX = os.environ.get('URL_PREFIX', '')  # Por defecto sin prefijo
if PREFIX:
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, PREFIX)
    # Log se agregará después cuando logger esté configurado

CORS(app)

# ====================================================================
# 📂 CONFIGURACIÓN DE CARPETA DE DATOS DE USUARIO
# ====================================================================
# Usar carpeta de datos de usuario en lugar de Program Files (permisos de escritura)
if os.name == 'nt':  # Windows
    USER_DATA_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'DetectorMovimiento')
else:  # Linux/Mac
    USER_DATA_DIR = os.path.join(os.path.expanduser('~'), '.detector_movimiento')

# Configuración
app.config['SECRET_KEY'] = 'detector-movimiento-secret-key-2025'
app.config['MAX_CONTENT_LENGTH'] = 2000 * 1024 * 1024  # 2GB máximo (para videos grandes)
app.config['UPLOAD_FOLDER'] = os.path.join(USER_DATA_DIR, 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'dav', 'mkv'}

# ====================================================================
# 📂 CONFIGURACIÓN MODO LOCAL (Sin sesiones - BD única)
# ====================================================================
app.config['DATA_FOLDER'] = os.path.join(USER_DATA_DIR, 'data_local')
app.config['DB_PATH'] = os.path.join(app.config['DATA_FOLDER'], 'detector_movimiento.db')
app.config['CLIPS_FOLDER'] = os.path.join(app.config['DATA_FOLDER'], 'clips_analisis')

# Crear carpetas
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)
os.makedirs(app.config['CLIPS_FOLDER'], exist_ok=True)

# ====================================================================
# 🎯 CONFIGURACIÓN DE CONCURRENCIA - ARQUITECTURA SECUENCIAL
# ====================================================================
# IMPORTANTE: Procesamiento SECUENCIAL de tareas (una carpeta a la vez)
# Dentro de cada tarea se procesan videos/clips en paralelo

MAX_WORKERS = max(2, multiprocessing.cpu_count() - 1)  # Workers para videos/clips

# Crear carpetas necesarias
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configurar logging - SESIÓN TEMPORAL con timestamp único (usar carpeta de usuario)
log_folder = os.path.join(USER_DATA_DIR, 'logs')
os.makedirs(log_folder, exist_ok=True)

def cleanup_old_logs():
    """Verifica cuántos logs hay (la limpieza real se hace al cerrar la app)"""
    try:
        # Solo contar archivos, no intentar eliminar (se eliminan al cerrar)
        log_files = [f for f in os.listdir(log_folder) if f.startswith('session_') and f.endswith('.log')]
        log_count = len(log_files)
        
        if log_count <= 10:
            logger.info(f"📋 Logs actuales: {log_count} archivos")
        else:
            logger.info(f"📋 Logs actuales: {log_count} archivos (se limpiarán al cerrar la app)")
        
    except Exception as e:
        logger.error(f"Error al verificar logs: {e}")

# Limpiar logs antiguos antes de crear el nuevo
# cleanup_old_logs()  # <-- MOVIDO DESPUÉS DE DEFINIR LOGGER

# Crear archivo de log único por sesión (cada vez que se inicia el servidor)
session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_folder, f'session_{session_timestamp}.log')

# Formato detallado de logs con más precisión
log_format = logging.Formatter(
    '%(asctime)s.%(msecs)03d | %(levelname)-8s | %(funcName)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# IMPORTANTE: Limpiar todos los handlers existentes para evitar duplicados
root_logger = logging.getLogger()
root_logger.handlers.clear()

# Handler para archivo de sesión
file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='w')
file_handler.setFormatter(log_format)
file_handler.setLevel(logging.DEBUG)

# Handler para consola
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
console_handler.setLevel(logging.INFO)

# Configurar logger raíz (esto afecta a TODOS los módulos)
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# SILENCIAR LOGS DE WERKZEUG (solo mostrar WARNING o superior)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.WARNING)

# Obtener logger para este módulo
logger = logging.getLogger(__name__)

# Limpiar logs antiguos antes de crear el nuevo
cleanup_old_logs()

# NO usar basicConfig - ya configuramos el root logger arriba
# logging.basicConfig(...) <- ELIMINADO para evitar duplicados

app.config['LOG_FILE'] = log_file
app.config['LOG_FOLDER'] = log_folder
app.config['SESSION_ID'] = session_timestamp

# Log de inicio de sesión
logger.info("="*80)
logger.info(f"🚀 NUEVA SESIÓN INICIADA - ID: {session_timestamp}")
logger.info(f"📁 Archivo de log: {log_file}")
logger.info(f"⚙️ Configuración de concurrencia: {MAX_WORKERS} workers")

# Log del prefijo de URL si está configurado
if PREFIX:
    logger.info(f"🔧 Aplicación configurada con prefijo de URL: {PREFIX}")
else:
    logger.info(f"🔧 Aplicación sin prefijo de URL (modo standalone)")

logger.info("="*80)

# Función para verificar herramientas disponibles
def check_system_dependencies():
    """Verifica que todas las herramientas necesarias estén disponibles"""
    logger.info("🔍 Verificando dependencias del sistema...")
    dependencies_status = {}
    
    # 1. Verificar Python y versión
    python_version = sys.version.split()[0]
    logger.info(f"   ✓ Python {python_version}")
    dependencies_status['python'] = {'available': True, 'version': python_version}
    
    # 2. Verificar OpenCV
    try:
        cv_version = cv2.__version__
        logger.info(f"   ✓ OpenCV {cv_version}")
        dependencies_status['opencv'] = {'available': True, 'version': cv_version}
    except Exception as e:
        logger.error(f"   ❌ OpenCV no disponible: {e}")
        dependencies_status['opencv'] = {'available': False, 'error': str(e)}
    
    # 3. Verificar ffmpeg
    try:
        # 🔥 USAR RUTA ABSOLUTA DE FFMPEG
        ffmpeg_exe = video_processing.get_ffmpeg_path()
        
        result = subprocess.run(
            [ffmpeg_exe, '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Extraer versión
            version_line = result.stdout.split('\n')[0]
            ffmpeg_version = version_line.split('version')[1].split()[0] if 'version' in version_line else 'unknown'
            logger.info(f"   ✓ ffmpeg {ffmpeg_version} (ruta: {ffmpeg_exe})")
            dependencies_status['ffmpeg'] = {'available': True, 'version': ffmpeg_version, 'path': ffmpeg_exe}
        else:
            logger.warning("   ⚠️ ffmpeg encontrado pero con errores")
            dependencies_status['ffmpeg'] = {'available': False, 'error': 'Error al ejecutar'}
    except FileNotFoundError:
        logger.warning("   ⚠️ ffmpeg NO encontrado - conversión DAV limitada")
        logger.warning(f"      Verifica la ruta: {video_processing.FFMPEG_PATH}")
        dependencies_status['ffmpeg'] = {'available': False, 'error': 'No instalado'}
    except Exception as e:
        logger.warning(f"   ⚠️ Error verificando ffmpeg: {e}")
        dependencies_status['ffmpeg'] = {'available': False, 'error': str(e)}
    
    # 4. Verificar SQLite (base de datos)
    try:
        import sqlite3
        sqlite_version = sqlite3.sqlite_version
        logger.info(f"   ✓ SQLite {sqlite_version}")
        dependencies_status['sqlite'] = {'available': True, 'version': sqlite_version}
    except Exception as e:
        logger.error(f"   ❌ SQLite no disponible: {e}")
        dependencies_status['sqlite'] = {'available': False, 'error': str(e)}
    
    # 5. Verificar Flask y dependencias web
    try:
        import flask
        flask_version = flask.__version__
        logger.info(f"   ✓ Flask {flask_version}")
        dependencies_status['flask'] = {'available': True, 'version': flask_version}
    except Exception as e:
        logger.error(f"   ❌ Flask no disponible: {e}")
        dependencies_status['flask'] = {'available': False, 'error': str(e)}
    
    # 6. Verificar espacio en disco
    try:
        import shutil
        total, used, free = shutil.disk_usage(os.path.dirname(__file__))
        free_gb = free // (2**30)
        logger.info(f"   ✓ Espacio libre en disco: {free_gb} GB")
        dependencies_status['disk_space'] = {'available': True, 'free_gb': free_gb}
        
        if free_gb < 1:
            logger.warning("   ⚠️ Poco espacio en disco (<1GB)")
    except Exception as e:
        logger.warning(f"   ⚠️ No se pudo verificar espacio en disco: {e}")
        dependencies_status['disk_space'] = {'available': False, 'error': str(e)}
    
    logger.info("="*80)
    
    # Guardar estado de dependencias en config
    app.config['DEPENDENCIES_STATUS'] = dependencies_status
    
    return dependencies_status

def check_roi_configuration():
    """Verifica si el ROI de timestamp está configurado al iniciar el servidor"""
    logger.info("="*80)
    logger.info("🔍 Verificando configuración de ROI de timestamp...")
    
    config_file = os.path.join(BASE_DIR, 'timestamp_roi_config.json')
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                roi_config = json.load(f)
            
            x = roi_config.get('x', 0)
            y = roi_config.get('y', 0)
            w = roi_config.get('w', 0)
            h = roi_config.get('h', 0)
            
            if w > 0 and h > 0:
                logger.info(f"   ✅ ROI de timestamp CONFIGURADO:")
                logger.info(f"      📍 Posición: x={x}, y={y}")
                logger.info(f"      📐 Dimensiones: {w}x{h} px")
                logger.info(f"      📄 Archivo: {config_file}")
                return True
            else:
                logger.warning(f"   ⚠️ ROI configurado pero dimensiones inválidas (w={w}, h={h})")
                return False
        except Exception as e:
            logger.error(f"   ❌ Error al leer configuración ROI: {e}")
            return False
    else:
        logger.warning("   ⚠️ ROI de timestamp NO CONFIGURADO")
        logger.warning("      → Los eventos usarán fecha del sistema en vez del OCR")
        logger.warning("      → Configura el ROI en: 🕐 Configurar Zona de Hora")
        return False

# Verificar dependencias al inicio
check_system_dependencies()

# Verificar ROI al inicio
check_roi_configuration()
logger.info("="*80)

# Inicializar BD única persistente (sin sesiones)
logger.info("📊 Inicializando base de datos única...")
db.create_tables(app.config['DB_PATH'])

# ✅ VERIFICAR que la tabla configuracion_deteccion existe (migración)
try:
    conn = db.create_db_connection(app.config['DB_PATH'])
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configuracion_deteccion'")
    if not cursor.fetchone():
        logger.info("📝 Creando tabla configuracion_deteccion...")
        cursor.execute("""
            CREATE TABLE configuracion_deteccion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                threshold_percentage REAL NOT NULL DEFAULT 1.0,
                var_threshold INTEGER NOT NULL DEFAULT 16,
                cooldown_ms INTEGER NOT NULL DEFAULT 2000,
                fecha_actualizacion TEXT NOT NULL,
                activa INTEGER NOT NULL DEFAULT 1
            );
        """)
        conn.commit()
        logger.info("✅ Tabla configuracion_deteccion creada")
    conn.close()
except Exception as e:
    logger.error(f"Error al verificar tabla configuracion_deteccion: {e}")

logger.info(f"   ✅ BD inicializada: {app.config['DB_PATH']}")
logger.info("="*80)

# Variable global para configuración de detección (se carga más adelante después de definir la función)
global_motion_config = None

# Variable global para tracking de progreso (ahora incluye info de sesión)
processing_status = {
    'is_processing': False,
    'current_video': '',
    'progress': 0,
    'total_videos': 0,
    'status_message': '',
    'motion_events_detected': 0,
    'clips_generated': 0,
    'objects_detected': 0,
    'current_phase': '',  # 'detecting_motion', 'creating_clips', 'analyzing_objects'
    'last_completed': None,  # Timestamp del último completado
    'just_completed': False,  # Flag para mostrar mensaje de completado
    'session_id': None,  # ID de sesión actual
    'session_db_path': None,  # Ruta de BD de la sesión actual
    'completed_tasks': []  # Lista de tareas completadas con su info
}

# Cola de procesamiento
processing_queue = []
queue_lock = threading.Lock()

# Diccionario para mantener sesiones activas {session_id: {db_path, folder_path, created_at, uploaded_videos}}
active_sessions = {}

# ====================================================================
# 💾 CONFIGURACIÓN PERSISTENTE (se guarda en BASE DE DATOS)
# ====================================================================

# Variable global para configuración (se carga de la BD)
analyze_from_original_path = False

def load_app_config():
    """
    Carga la configuración de la aplicación desde la BASE DE DATOS.
    Incluye configuración de detección de movimiento y opciones de análisis.
    """
    global analyze_from_original_path
    
    try:
        # Cargar configuración de detección de movimiento desde la BD PERMANENTE
        motion_config = db.load_motion_detection_config(app.config['DB_PATH'])
        
        if motion_config:
            logger.info(f"✅ Configuración de detección cargada desde BD")
            logger.info(f"   • Threshold: {motion_config['threshold_percentage']}%")
            logger.info(f"   • Var threshold: {motion_config['var_threshold']}")
            logger.info(f"   • Cooldown: {motion_config['cooldown_ms']}ms")
        else:
            logger.info("📝 No hay configuración guardada, se usarán valores por defecto")
            motion_config = {
                'threshold_percentage': 1.0,
                'var_threshold': 16,
                'cooldown_ms': 2000,
                'gaussian_blur': (5, 5),
                'morph_kernel_size': (3, 3),
                'binary_threshold': 127
            }
        
        # Por ahora, analyze_from_original_path se mantiene en False por defecto
        # En el futuro se puede añadir una tabla de configuración general
        analyze_from_original_path = False
        
        return motion_config
    
    except Exception as e:
        logger.error(f"❌ Error al cargar configuración: {e}")
        return {
            'threshold_percentage': 1.0,
            'var_threshold': 16,
            'cooldown_ms': 2000,
            'gaussian_blur': (5, 5),
            'morph_kernel_size': (3, 3),
            'binary_threshold': 127
        }

# ✅ CARGAR CONFIGURACIÓN AL INICIAR LA APLICACIÓN
logger.info("📋 Cargando configuración de detección...")
global_motion_config = load_app_config()
logger.info("="*80)

def get_or_create_session():
    """Obtiene o crea una sesión activa para el usuario"""
    # Por ahora, una sesión global simple (en el futuro se puede usar Flask sessions)
    if processing_status['session_id'] is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_id = f"session_{timestamp}"
        
        # Crear carpeta de sesión
        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        os.makedirs(session_folder, exist_ok=True)
        
        # Usar BD única persistente en lugar de BD por sesión
        session_db_path = app.config['DB_PATH']
        
        # Crear Excel de sesión
        excel_path = create_or_update_session_excel(session_db_path, session_folder)
        
        # Guardar info de sesión
        processing_status['session_id'] = session_id
        processing_status['session_db_path'] = session_db_path
        processing_status['session_folder_path'] = session_folder
        processing_status['session_excel_path'] = excel_path
        
        # LIMPIAR HISTORIAL DE TAREAS COMPLETADAS AL INICIAR NUEVA SESIÓN
        processing_status['completed_tasks'] = []
        
        active_sessions[session_id] = {
            'db_path': session_db_path,
            'folder_path': session_folder,
            'created_at': datetime.now(),
            'uploaded_videos': []  # Lista de videos subidos en esta sesión
        }
        
        logger.info(f"🆕 Nueva sesión creada: {session_id}")
        logger.info(f"   📁 Carpeta: {session_folder}")
        logger.info(f"   🗄️ BD: {session_db_path}")
        logger.info(f"   📊 Excel: {excel_path}")
    
    return processing_status['session_id'], processing_status['session_db_path']

def get_session_db():
    """Helper para obtener la BD de sesión actual o None"""
    return app.config['DB_PATH']  # Siempre usar BD única

def cleanup_old_sessions():
    """Limpia TODAS las sesiones anteriores al iniciar el servidor - solo mantiene sesión actual"""
    logger.info("🧹 Limpiando sesiones anteriores...")
    
    upload_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        return
    
    cleaned_count = 0
    
    for item in os.listdir(upload_folder):
        item_path = os.path.join(upload_folder, item)
        
        # Eliminar TODAS las carpetas session_XXXXXX (sesiones anteriores)
        if os.path.isdir(item_path) and item.startswith('session_'):
            try:
                import shutil
                shutil.rmtree(item_path)
                cleaned_count += 1
                logger.info(f"   ✓ Eliminada sesión anterior: {item}")
            except Exception as e:
                logger.warning(f"   ⚠️ Error al limpiar {item}: {e}")
        
        # Eliminar carpeta temp si existe
        elif item == 'temp' and os.path.isdir(item_path):
            try:
                import shutil
                shutil.rmtree(item_path)
                os.makedirs(item_path, exist_ok=True)
                logger.info(f"   ✓ Carpeta temp limpiada")
            except Exception as e:
                logger.warning(f"   ⚠️ Error al limpiar temp: {e}")
        
        # Eliminar archivos sueltos que no deberían estar
        elif os.path.isfile(item_path):
            try:
                os.remove(item_path)
                logger.info(f"   ✓ Eliminado archivo suelto: {item}")
                cleaned_count += 1
            except Exception as e:
                logger.warning(f"   ⚠️ Error al eliminar {item}: {e}")
    
    if cleaned_count > 0:
        logger.info(f"✅ Limpiadas {cleaned_count} sesiones/archivos anteriores")
    else:
        logger.info(f"✓ No hay sesiones antiguas que limpiar")

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    """Página principal con sidebar y vistas dinámicas"""
    # Agregar timestamp para evitar caché
    cache_bust = datetime.now().strftime('%Y%m%d%H%M%S')
    return render_template('index.html', cache_bust=cache_bust)

# Dashboard ahora es una vista dentro de la aplicación principal (botón Estadísticas)
# @app.route('/dashboard')
# def dashboard():
#     """Dashboard con análisis de videos"""
#     return render_template('dashboard.html')

@app.route('/api/folders', methods=['GET'])
def get_folders():
    """Obtiene todas las carpetas analizadas de la BD PERMANENTE"""
    try:
        # ✅ USAR BD PERMANENTE en lugar de BD temporal de sesión
        conn = db.create_db_connection(app.config['DB_PATH'])
        cursor = conn.cursor()
        cursor.execute("SELECT id, ruta, fecha_subida FROM carpetas ORDER BY fecha_subida DESC")
        folders = cursor.fetchall()
        conn.close()
        
        result = []
        for folder in folders:
            result.append({
                'id': folder[0],
                'path': folder[1],
                'upload_date': folder[2],
                'name': os.path.basename(folder[1])
            })
        
        logger.info(f"✅ Cargadas {len(result)} carpetas de la BD permanente")
        return jsonify({'success': True, 'folders': result})
    except Exception as e:
        logger.error(f"Error al obtener carpetas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/folder/<int:folder_id>', methods=['GET'])
def get_folder_details(folder_id):
    """Obtiene detalles de una carpeta específica de la BD PERMANENTE"""
    try:
        # ✅ USAR BD PERMANENTE
        conn = db.create_db_connection(app.config['DB_PATH'])
        cursor = conn.cursor()
        
        # Obtener videos de la carpeta
        cursor.execute("""
            SELECT id, nombre_archivo, fecha_creacion, roi_x, roi_y, roi_w, roi_h
            FROM videos WHERE carpeta_id = ? ORDER BY fecha_creacion DESC
        """, (folder_id,))
        videos = cursor.fetchall()
        
        result = []
        for video in videos:
            # Contar clips de este video
            cursor.execute("SELECT COUNT(*) FROM clips WHERE video_id = ?", (video[0],))
            clip_count = cursor.fetchone()[0]
            
            result.append({
                'id': video[0],
                'name': video[1],
                'creation_date': video[2],
                'roi': [video[3], video[4], video[5], video[6]] if video[3] else None,
                'clip_count': clip_count
            })
        
        conn.close()
        return jsonify({'success': True, 'videos': result})
    except Exception as e:
        logger.error(f"Error al obtener detalles de carpeta: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/video/<int:video_id>/clips', methods=['GET'])
def get_video_clips(video_id):
    """Obtiene clips de un video específico de la BD PERMANENTE"""
    try:
        # ✅ USAR BD PERMANENTE
        conn = db.create_db_connection(app.config['DB_PATH'])
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, nombre_archivo, ruta_absoluta, tiempo_evento_ms, fecha_evento,
                   objeto_detectado, color_detectado
            FROM clips WHERE video_id = ? ORDER BY fecha_evento DESC
        """, (video_id,))
        clips = cursor.fetchall()
        
        result = []
        for clip in clips:
            # Si hay ruta de clip, generar nombre del archivo. Si no (modo sin clips), es None
            if clip[2]:  # ruta_absoluta existe
                clip_filename = os.path.basename(clip[2])
            else:  # Evento sin clip MP4 (solo registro de movimiento)
                clip_filename = None
            
            result.append({
                'id': clip[0],
                'name': clip[1],
                'nombre': clip[1],  # Compatibilidad con modal
                'ruta_relativa': clip_filename,  # Nombre del archivo para URL /clips/<filename>
                'url': f'/clips/{clip_filename}' if clip_filename else None,
                'event_time_ms': clip[3],
                'timestamp': clip[4],  # Compatibilidad con modal
                'event_date': clip[4],
                'detected_object': clip[5],
                'object_type': clip[5],
                'color': clip[6],
                'object_color': clip[6],
                'has_clip': clip[2] is not None  # Flag para saber si tiene clip MP4
            })
        
        conn.close()
        return jsonify({'success': True, 'clips': result})
    except Exception as e:
        logger.error(f"Error al obtener clips: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/clips/<path:filename>')
def serve_clip(filename):
    """Sirve archivos de clip de video de la sesión actual con soporte para streaming"""
    # Decodificar el nombre del archivo (espacios y caracteres especiales)
    filename = unquote(filename)
    
    logger.info(f"🎬 Intentando servir clip: {filename}")
    
    # Usar BD de sesión
    session_db_path = processing_status.get('session_db_path')
    
    if not session_db_path or not os.path.exists(session_db_path):
        logger.error("❌ No hay sesión activa")
        return jsonify({'error': 'No hay sesión activa'}), 404
    
    # Buscar el clip en la base de datos
    conn = db.create_db_connection(session_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT ruta_absoluta FROM clips WHERE nombre_archivo = ?", (filename,))
    result = cursor.fetchone()
    conn.close()
    
    if not result or not result[0]:
        if result and not result[0]:
            logger.warning(f"⚠️ Clip '{filename}' es un evento sin archivo MP4 (ruta_absoluta es NULL)")
            return jsonify({'error': 'Este evento no tiene clip de video asociado'}), 404
        
        logger.error(f"❌ Clip no encontrado en BD: {filename}")
        return jsonify({'error': 'Clip no encontrado'}), 404
    
    clip_path = result[0]
    logger.info(f"✅ Clip encontrado en BD: {clip_path}")
    
    # Verificar que el archivo existe
    if not os.path.exists(clip_path):
        logger.error(f"❌ Archivo de clip no existe en disco: {clip_path}")
        return jsonify({'error': 'Archivo de clip no encontrado en disco'}), 404
    
    file_size = os.path.getsize(clip_path)
    logger.info(f"✅ Archivo existe, tamaño: {file_size} bytes")
    
    # Soporte para HTTP Range Requests (crítico para streaming de video)
    range_header = request.headers.get('Range')
    
    if not range_header:
        # Sin Range header, enviar archivo completo
        logger.info("📤 Enviando archivo completo (sin Range)")
        
        def generate():
            with open(clip_path, 'rb') as f:
                chunk_size = 8192
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        
        response = Response(generate(), mimetype='video/mp4')
        response.headers['Content-Length'] = file_size
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Cache-Control'] = 'no-cache'
        return response
    
    # Con Range header, enviar parte específica (streaming)
    # Formato: "bytes=start-end"
    range_match = range_header.replace('bytes=', '').split('-')
    start = int(range_match[0]) if range_match[0] else 0
    end = int(range_match[1]) if range_match[1] else file_size - 1
    
    # Validar rango
    if start >= file_size or end >= file_size:
        logger.warning(f"⚠️ Rango inválido: {start}-{end} (tamaño: {file_size})")
        return Response('Rango solicitado no disponible', status=416)
    
    length = end - start + 1
    
    logger.info(f"📤 Streaming parcial: bytes {start}-{end}/{file_size} ({length} bytes)")
    
    def generate_range():
        with open(clip_path, 'rb') as f:
            f.seek(start)
            remaining = length
            chunk_size = 8192
            
            while remaining > 0:
                chunk = f.read(min(chunk_size, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
    
    response = Response(generate_range(), status=206, mimetype='video/mp4')
    response.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
    response.headers['Content-Length'] = length
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Cache-Control'] = 'no-cache'
    
    return response

@app.route('/uploads/<session_folder>/<path:filename>')
def serve_uploaded_video(session_folder, filename):
    """Sirve videos subidos desde las carpetas de sesión"""
    try:
        # Decodificar el nombre del archivo (espacios y caracteres especiales)
        filename = unquote(filename)
        
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], session_folder, filename)
        logger.info(f"📹 [SERVE] Sirviendo video: {filename} desde carpeta: {session_folder}")
        logger.info(f"📹 [SERVE] Ruta completa: {video_path}")
        
        if not os.path.exists(video_path):
            logger.error(f"❌ [SERVE] Video no encontrado en: {video_path}")
            return jsonify({'error': 'Video no encontrado'}), 404
        
        logger.info(f"✓ [SERVE] Video existe en disco")
        
        # Verificar que sea un archivo permitido
        if not allowed_file(filename):
            logger.error(f"❌ [SERVE] Tipo de archivo no permitido: {filename}")
            return jsonify({'error': 'Tipo de archivo no permitido'}), 403
        
        logger.info(f"✓ [SERVE] Tipo de archivo permitido: {filename}")
        
        # Si es un archivo DAV, convertir a MP4 para visualización
        if filename.lower().endswith('.dav'):
            logger.info(f"🔄 [CONVERT] Archivo DAV detectado: {filename}")
            
            # Guardar preview en carpeta temp (no en session folder)
            temp_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
            logger.info(f"📁 [CONVERT] Carpeta temp: {temp_folder}")
            
            os.makedirs(temp_folder, exist_ok=True)
            logger.info(f"✓ [CONVERT] Carpeta temp verificada/creada")
            
            # Nombre del archivo MP4 convertido (solo primeros 10 segundos para ROI)
            mp4_filename = filename.rsplit('.', 1)[0] + '_preview.mp4'
            mp4_path = os.path.join(temp_folder, mp4_filename)
            logger.info(f"📝 [CONVERT] Nombre preview: {mp4_filename}")
            logger.info(f"📝 [CONVERT] Ruta preview completa: {mp4_path}")
            
            # Si ya existe la conversión, servir ese archivo
            if os.path.exists(mp4_path):
                logger.info(f"✓ [CACHE] Preview ya existe, sirviendo: {mp4_filename}")
                logger.info(f"✓ [CACHE] Tamaño del archivo: {os.path.getsize(mp4_path)} bytes")
                return send_from_directory(
                    temp_folder,
                    mp4_filename,
                    mimetype='video/mp4',
                    conditional=True
                )
            
            logger.info(f"⏳ [CONVERT] Preview no existe, iniciando conversión...")
            
            # Convertir DAV a MP4 (solo primeros 10 segundos)
            try:
                # 🔥 USAR RUTA ABSOLUTA DE FFMPEG
                ffmpeg_exe = video_processing.get_ffmpeg_path()
                
                # Comando FFmpeg para conversión rápida (solo 10 segundos)
                cmd = [
                    ffmpeg_exe,
                    '-i', video_path,
                    '-t', '10',  # Solo primeros 10 segundos    
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',  # Más rápido
                    '-crf', '28',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-movflags', '+faststart',
                    '-y',
                    mp4_path
                ]
                
                logger.info(f"🔧 [FFMPEG] Comando: {' '.join(cmd)}")
                logger.info(f"⏰ [FFMPEG] Iniciando conversión (timeout: 30s)...") 
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                logger.info(f"✓ [FFMPEG] Proceso finalizado con código: {result.returncode}")
                
                if result.returncode == 0:
                    if os.path.exists(mp4_path):
                        file_size = os.path.getsize(mp4_path)
                        logger.info(f"✅ [SUCCESS] Conversión exitosa: {mp4_filename}")
                        logger.info(f"✅ [SUCCESS] Tamaño del archivo: {file_size} bytes")
                        logger.info(f"✅ [SUCCESS] Sirviendo preview desde temp")
                        return send_from_directory(
                            temp_folder,
                            mp4_filename,
                            mimetype='video/mp4',
                            conditional=True
                        )
                    else:
                        logger.error(f"❌ [ERROR] FFmpeg returncode=0 pero archivo no existe: {mp4_path}")
                        logger.error(f"❌ [ERROR] STDOUT: {result.stdout}")
                        logger.error(f"❌ [ERROR] STDERR: {result.stderr}")
                        return jsonify({'error': 'Error: archivo no generado'}), 500
                else:
                    logger.error(f"❌ [ERROR] FFmpeg falló con código: {result.returncode}")
                    logger.error(f"❌ [ERROR] STDOUT: {result.stdout}")
                    logger.error(f"❌ [ERROR] STDERR: {result.stderr}")
                    return jsonify({'error': 'Error al convertir video DAV'}), 500
                    
            except subprocess.TimeoutExpired:
                logger.error("❌ [TIMEOUT] FFmpeg excedió 30 segundos")
                return jsonify({'error': 'Timeout al convertir video'}), 500
            except Exception as e:
                logger.error(f"❌ [EXCEPTION] Error convirtiendo DAV: {type(e).__name__}: {e}")
                import traceback
                logger.error(f"❌ [TRACEBACK] {traceback.format_exc()}")
                return jsonify({'error': f'Error al convertir video: {str(e)}'}), 500
        
        # Para archivos MP4 u otros formatos soportados, servir directamente
        logger.info(f"📹 [DIRECT] Sirviendo archivo directamente (no es DAV): {filename}")
        return send_from_directory(
            os.path.join(app.config['UPLOAD_FOLDER'], session_folder),
            filename,
            mimetype='video/mp4',
            conditional=True  # Habilita soporte para Range requests
        )
    except Exception as e:
        logger.error(f"❌ [FATAL] Error inesperado sirviendo video: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"❌ [TRACEBACK] {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/convert-dav', methods=['POST'])
def convert_dav_to_mp4():
    """Convierte un archivo DAV subido temporalmente a MP4 para visualización en navegador"""
    try:
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No se envió archivo'}), 400
        
        file = request.files['video']
        if not file or file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        # Guardar temporalmente
        filename = secure_filename(file.filename)
        temp_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
        os.makedirs(temp_folder, exist_ok=True)
        
        dav_path = os.path.join(temp_folder, filename)
        file.save(dav_path)
        
        # Si es DAV, convertir a MP4
        if filename.lower().endswith('.dav'):
            mp4_filename = filename.rsplit('.', 1)[0] + '_converted.mp4'
            mp4_path = os.path.join(temp_folder, mp4_filename)
            
            # Verificar si ya existe la conversión Y es válida
            if os.path.exists(mp4_path):
                # Verificar que el video sea reproducible y tenga el codec correcto
                try:
                    # Verificar con ffprobe si está disponible
                    probe_cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', 
                                '-show_entries', 'stream=codec_name', '-of', 'default=noprint_wrappers=1:nokey=1', mp4_path]
                    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
                    codec = probe_result.stdout.strip()
                    
                    if codec == 'h264':
                        logger.info(f"✓ Conversión ya existe en caché con codec H.264: {mp4_filename}")
                        return jsonify({
                            'success': True,
                            'video_url': url_for('serve_temp_video', filename=mp4_filename)
                        })
                    else:
                        logger.warning(f"⚠️ Video en caché usa codec {codec}, reconvirtiendo con H.264...")
                        os.remove(mp4_path)
                except:
                    # Si ffprobe falla, reconvertir
                    logger.warning(f"⚠️ No se pudo verificar codec, reconvirtiendo...")
                    if os.path.exists(mp4_path):
                        os.remove(mp4_path)
            
            # Convertir usando OpenCV
            logger.info(f"🎬 Iniciando conversión DAV → MP4: {filename}")
            cap = cv2.VideoCapture(dav_path)
            
            if not cap.isOpened():
                logger.error(f"❌ No se pudo abrir el archivo DAV: {filename}")
                return jsonify({'success': False, 'error': 'No se pudo abrir el video DAV'}), 400
            
            # Obtener propiedades del video
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            if fps == 0:
                fps = 25  # FPS por defecto
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            logger.info(f"📐 Propiedades del video: {width}x{height} @ {fps}fps")
            cap.release()
            
            # Intentar usar ffmpeg primero (más compatible)
            ffmpeg_success = False
            try:
                logger.info("🎬 Intentando conversión con ffmpeg...")
                
                # 🔥 USAR RUTA ABSOLUTA DE FFMPEG
                ffmpeg_exe = video_processing.get_ffmpeg_path()
                
                # Comando ffmpeg optimizado para navegadores
                ffmpeg_cmd = [
                    ffmpeg_exe,
                    '-i', dav_path,
                    '-t', '10',  # Limitar a 10 segundos
                    '-c:v', 'libx264',  # Codec H.264
                    '-preset', 'fast',
                    '-crf', '23',
                    '-pix_fmt', 'yuv420p',  # Crucial para compatibilidad con navegadores
                    '-movflags', '+faststart',  # Optimizar para streaming web
                    '-y',  # Sobrescribir
                    mp4_path
                ]
                
                result = subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 and os.path.exists(mp4_path):
                    ffmpeg_success = True
                    logger.info("✅ Conversión con ffmpeg exitosa")
                else:
                    logger.warning(f"⚠️ ffmpeg falló: {result.stderr[:200]}")
                    
            except FileNotFoundError:
                logger.warning("⚠️ ffmpeg no encontrado en el sistema")
            except Exception as e:
                logger.warning(f"⚠️ Error con ffmpeg: {str(e)[:100]}")
            
            # Si ffmpeg falla, usar OpenCV como fallback
            if not ffmpeg_success:
                logger.info("📹 Usando OpenCV como fallback...")
                cap = cv2.VideoCapture(dav_path)
                
                # Intentar diferentes codecs
                codec_used = 'mp4v'
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(mp4_path, fourcc, fps, (width, height))
                
                if not out.isOpened():
                    logger.error("❌ No se pudo inicializar escritor de video")
                    return jsonify({'success': False, 'error': 'No se pudo crear el video de salida'}), 500
                
                frame_count = 0
                max_frames = 300  # Limitar a ~10 segundos
                
                logger.info(f"⏳ Procesando frames con OpenCV (máximo {max_frames})...")
                while frame_count < max_frames:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    out.write(frame)
                    frame_count += 1
                    
                    if frame_count % 50 == 0:
                        logger.debug(f"   Procesados {frame_count} frames...")
                
                cap.release()
                out.release()
                
                if frame_count == 0:
                    logger.error("❌ No se pudieron leer frames del video")
                    return jsonify({'success': False, 'error': 'No se pudieron leer frames del video'}), 400
            
            # Verificar que el archivo se haya creado correctamente
            if not os.path.exists(mp4_path):
                logger.error(f"❌ El archivo convertido no se creó: {mp4_path}")
                return jsonify({'success': False, 'error': 'El archivo convertido no se creó'}), 500
            
            file_size = os.path.getsize(mp4_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # Verificar que el archivo tenga contenido
            if file_size < 1000:
                logger.error(f"❌ Archivo muy pequeño ({file_size} bytes), posible error de conversión")
                return jsonify({'success': False, 'error': 'La conversión generó un archivo inválido'}), 500
            
            logger.info(f"✅ Conversión completada exitosamente")
            logger.info(f"   • Método: {'ffmpeg' if ffmpeg_success else 'OpenCV'}")
            logger.info(f"   • Tamaño archivo: {file_size_mb:.2f} MB ({file_size:,} bytes)")
            logger.info(f"   • Archivo: {mp4_filename}")
            
            # Verificar que el video sea reproducible
            test_cap = cv2.VideoCapture(mp4_path)
            if not test_cap.isOpened():
                logger.error("❌ El video convertido no se puede abrir")
                test_cap.release()
                return jsonify({'success': False, 'error': 'El video convertido no es válido'}), 500
            
            test_frame_count = int(test_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            test_cap.release()
            logger.info(f"   • Frames en video final: {test_frame_count}")
            
            video_url = url_for('serve_temp_video', filename=mp4_filename)
            
            return jsonify({
                'success': True,
                'video_url': video_url,
                'frames_converted': test_frame_count,
                'file_size': file_size
            })
        else:
            # Si no es DAV, servir directamente
            return jsonify({
                'success': True,
                'video_url': url_for('serve_temp_video', filename=filename)
            })
            
    except Exception as e:
        logger.error(f"Error al convertir DAV: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/temp/<path:filename>')
def serve_temp_video(filename):
    """Sirve videos temporales convertidos con soporte de Range Requests"""
    # Decodificar el nombre del archivo (espacios y caracteres especiales)
    filename = unquote(filename)
    
    temp_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
    file_path = os.path.join(temp_folder, filename)
    
    if not os.path.exists(file_path):
        logger.error(f"❌ Video temporal no encontrado: {filename}")
        return jsonify({'error': 'Video no encontrado'}), 404
    
    file_size = os.path.getsize(file_path)
    logger.debug(f"📹 Sirviendo video: {filename} ({file_size / 1024:.1f} KB)")
    
    # Soporte para Range Requests (crítico para video streaming)
    range_header = request.headers.get('Range', None)
    
    if range_header:
        # Parsear el header Range: bytes=start-end
        byte_range = range_header.replace('bytes=', '').split('-')
        start = int(byte_range[0]) if byte_range[0] else 0
        end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1
        length = end - start + 1
        
        with open(file_path, 'rb') as f:
            f.seek(start)
            data = f.read(length)
        
        response = Response(data, 206, mimetype='video/mp4')
        response.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Content-Length'] = str(length)
        response.headers['Cache-Control'] = 'no-cache'
        return response
    else:
        # Respuesta completa sin Range - leer archivo completo
        with open(file_path, 'rb') as f:
            data = f.read()
        
        response = Response(data, 200, mimetype='video/mp4')
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Content-Type'] = 'video/mp4'
        response.headers['Content-Length'] = str(file_size)
        response.headers['Cache-Control'] = 'no-cache'
        return response

@app.route('/api/generate-roi-preview', methods=['POST'])
def generate_roi_preview():
    """Genera un preview ligero (1 frame, resolución original) del video para selección de ROI"""
    try:
        data = request.json
        video_filename = data.get('filename')
        session_folder = data.get('session_folder')
        
        if not video_filename or not session_folder:
            return jsonify({'success': False, 'error': 'Faltan parámetros'}), 400
        
        # Ruta del video original
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], session_folder, video_filename)
        
        if not os.path.exists(video_path):
            logger.error(f"❌ Video no encontrado: {video_path}")
            return jsonify({'success': False, 'error': 'Video no encontrado'}), 404
        
        # Crear carpeta temp si no existe
        temp_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
        os.makedirs(temp_folder, exist_ok=True)
        
        # Nombre del preview (usando hash del path para evitar colisiones)
        import hashlib
        preview_id = hashlib.md5(video_path.encode()).hexdigest()[:8]
        preview_filename = f'roi_preview_{preview_id}.mp4'
        preview_path = os.path.join(temp_folder, preview_filename)
        
        # Si ya existe el preview, devolverlo
        if os.path.exists(preview_path):
            preview_size = os.path.getsize(preview_path) / 1024  # KB
            logger.info(f"✓ Preview ya existe (1 frame MP4, resolución original): {preview_filename} ({preview_size:.1f}KB)")
            return jsonify({
                'success': True,
                'preview_filename': preview_filename,
                'preview_url': f'/temp/{preview_filename}'
            })
        
        logger.info(f"🎬 Generando preview para ROI (resolución original - solo primer frame): {video_filename}")
        
        # Generar preview: video de 1 frame en resolución original (compatible con navegador)

        ffmpeg_exe = video_processing.get_ffmpeg_path()
        
        cmd = [
            ffmpeg_exe,
            '-i', video_path,
            '-vframes', '1',  # Solo 1 frame (el primero)
            '-c:v', 'libx264',  # Codec H.264 compatible
            '-pix_fmt', 'yuv420p',  # Formato de pixel compatible navegador
            '-movflags', '+faststart',  # Optimizar para web
            '-an',  # Sin audio
            '-y',
            preview_path
        ]
        
        logger.info(f"🔧 Ejecutando FFmpeg para preview (1 frame MP4)...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and os.path.exists(preview_path):
            preview_size = os.path.getsize(preview_path) / 1024  # KB
            logger.info(f"✅ Preview generado en resolución original (1 frame MP4): {preview_filename} ({preview_size:.1f}KB)")
            
            return jsonify({
                'success': True,
                'preview_filename': preview_filename,
                'preview_url': f'/temp/{preview_filename}'
            })
        else:
            logger.error(f"❌ Error generando preview: {result.stderr}")
            return jsonify({'success': False, 'error': 'Error al generar preview'}), 500
            
    except Exception as e:
        logger.error(f"❌ Error en generate_roi_preview: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_videos():
    """Endpoint LEGACY para subir videos (DEPRECADO - usar /api/upload/chunk)"""
    try:
        logger.warning("⚠️ " + "="*80)
        logger.warning("⚠️ ENDPOINT LEGACY /api/upload LLAMADO")
        logger.warning("⚠️ Este endpoint está DEPRECADO y causa ERR_CONNECTION_RESET")
        logger.warning("⚠️ Deberías estar usando /api/upload/chunk con chunking")
        logger.warning("⚠️ VERIFICA QUE EL NAVEGADOR NO ESTÉ USANDO CACHÉ VIEJO")
        logger.warning("⚠️ " + "="*80)
        logger.info("📤 Recibida solicitud de upload de videos")
        logger.info(f"📊 Content-Length: {request.content_length}")
        logger.info(f"📊 Remote addr: {request.remote_addr}")
        logger.info(f"📊 User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
        
        if 'videos' not in request.files:
            logger.error("❌ No se enviaron archivos en la solicitud")
            return jsonify({'success': False, 'error': 'No se enviaron archivos'}), 400
        
        files = request.files.getlist('videos')
        if not files or files[0].filename == '':
            logger.error("❌ No se seleccionaron archivos")
            return jsonify({'success': False, 'error': 'No se seleccionaron archivos'}), 400
        
        logger.info(f"📁 Recibidos {len(files)} archivos")
        
        # Advertir sobre archivos grandes
        for file in files:
            file.seek(0, 2)  # Ir al final
            size = file.tell()
            file.seek(0)  # Volver al inicio
            size_mb = size / (1024 * 1024)
            logger.info(f"📄 Archivo: {file.filename} - Tamaño: {size_mb:.2f} MB")
            if size_mb > 100:
                logger.warning(f"⚠️ ARCHIVO MUY GRANDE: {file.filename} ({size_mb:.2f} MB) - Puede causar ERR_CONNECTION_RESET")
                logger.warning(f"⚠️ Se recomienda usar chunking (/api/upload/chunk)")
        
        # Obtener o crear sesión
        session_id, session_db_path = get_or_create_session()
        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        
        logger.info(f"✓ Usando sesión: {session_id}")
        logger.info(f"✓ Carpeta de sesión: {session_folder}")
        
        uploaded_files = []
        duplicates = []  # Videos que ya existen en esta sesión
        
        # Conectar a BD de la sesión
        conn = db.create_db_connection(session_db_path)
        cursor = conn.cursor()
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(session_folder, filename)
                
                # SIEMPRE guardar el archivo físicamente (necesario para configurar ROI)
                file.save(filepath)
                logger.info(f"   💾 Archivo guardado físicamente: {filename}")
                
                # Verificar si el video ya existe en BD de esta sesión
                cursor.execute("SELECT id, nombre_archivo FROM videos WHERE nombre_archivo = ?", (filename,))
                existing_video = cursor.fetchone()
                
                if existing_video:
                    logger.warning(f"⚠️ Video duplicado en esta sesión: {filename} (ID: {existing_video[0]})")
                    duplicates.append({
                        'name': filename,
                        'path': filepath,
                        'existing_id': existing_video[0]
                    })
                    # Agregar también a uploaded_files para poder configurar ROI
                    uploaded_files.append({'name': filename, 'path': filepath, 'is_duplicate': True})
                else:
                    uploaded_files.append({'name': filename, 'path': filepath, 'is_duplicate': False})
                    logger.info(f"   ✓ Video nuevo: {filename}")
                    
                    # 🎯 AGREGAR A LA LISTA DE VIDEOS SUBIDOS DE LA SESIÓN
                    if session_id in active_sessions:
                        if filename not in active_sessions[session_id]['uploaded_videos']:
                            active_sessions[session_id]['uploaded_videos'].append(filename)
                            logger.info(f"   📝 Video agregado a lista de sesión: {filename}")
        
        conn.close()
        
        logger.info(f"✅ Total archivos guardados físicamente: {len(uploaded_files)}")
        if duplicates:
            logger.warning(f"⚠️ Duplicados detectados (solo advertencia): {len(duplicates)}")
        
        # Retornar session_id en lugar de folder_id temporal
        return jsonify({
            'success': True,
            'session_id': session_id,  # Usar session_id consistente
            'folder_id': session_id,  # Por compatibilidad con código existente
            'folder_path': session_folder,
            'uploaded_files': uploaded_files,
            'duplicates': duplicates,  # Lista de videos duplicados
            'has_duplicates': len(duplicates) > 0
        })
    
    except Exception as e:
        logger.error(f"Error al subir archivos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session/create', methods=['POST'])
def create_upload_session():
    """Crea una sesión de subida para chunking"""
    try:
        logger.info(f"📡 [SESSION] Recibiendo petición de creación de sesión")
        logger.info(f"📡 [SESSION] Headers: {dict(request.headers)}")
        logger.info(f"📡 [SESSION] Remote addr: {request.remote_addr}")
        
        session_id, session_db_path = get_or_create_session()
        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        
        logger.info(f"✅ [SESSION] Sesión de chunking creada: {session_id}")
        logger.info(f"✅ [SESSION] Carpeta: {session_folder}")
        logger.info(f"✅ [SESSION] DB Path: {session_db_path}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'session_folder': session_folder
        })
    except Exception as e:
        logger.error(f"❌ [SESSION] Error al crear sesión: {e}")
        logger.error(f"❌ [SESSION] Stack trace:", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload/chunk', methods=['POST'])
def upload_chunk():
    """Endpoint para subir chunks de archivos (5-10MB por chunk)"""
    try:
        logger.info(f"=" * 80)
        logger.info(f"📡 [CHUNK] NUEVA PETICIÓN RECIBIDA")
        logger.info(f"=" * 80)
        logger.info(f"📡 [CHUNK] Remote addr: {request.remote_addr}")
        logger.info(f"📡 [CHUNK] Method: {request.method}")
        logger.info(f"📡 [CHUNK] Content-Type: {request.content_type}")
        logger.info(f"📡 [CHUNK] Content-Length: {request.content_length}")
        logger.info(f"📡 [CHUNK] Headers: {dict(request.headers)}")
        logger.info(f"📡 [CHUNK] Form keys: {list(request.form.keys())}")
        logger.info(f"📡 [CHUNK] Files keys: {list(request.files.keys())}")
        
        if 'chunk' not in request.files:
            logger.error(f"❌ [CHUNK] No se envió chunk en request.files")
            logger.error(f"❌ [CHUNK] Files presentes: {list(request.files.keys())}")
            logger.error(f"❌ [CHUNK] Form presentes: {list(request.form.keys())}")
            return jsonify({'success': False, 'error': 'No se envió chunk'}), 400
        
        chunk = request.files['chunk']
        filename = request.form.get('filename')
        chunk_index = int(request.form.get('chunkIndex'))
        total_chunks = int(request.form.get('totalChunks'))
        folder_id = request.form.get('folderId')
        
        logger.info(f"📦 [CHUNK] Parámetros - File: {filename}, Chunk: {chunk_index+1}/{total_chunks}, Folder: {folder_id}")
        logger.info(f"📦 [CHUNK] Tamaño del chunk: {chunk.content_length if hasattr(chunk, 'content_length') else 'desconocido'}")
        
        if not all([filename, folder_id is not None]):
            logger.error(f"❌ [CHUNK] Faltan parámetros - filename: {filename}, folder_id: {folder_id}")
            return jsonify({'success': False, 'error': 'Faltan parámetros'}), 400
        
        # Sanitizar nombre de archivo
        filename = secure_filename(filename)
        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], folder_id)
        os.makedirs(session_folder, exist_ok=True)
        
        logger.info(f"📁 [CHUNK] Session folder: {session_folder}")
        
        # Carpeta temporal para chunks
        chunks_folder = os.path.join(session_folder, '.chunks', filename)
        os.makedirs(chunks_folder, exist_ok=True)
        
        logger.info(f"📁 [CHUNK] Chunks folder: {chunks_folder}")
        
        # Guardar chunk
        chunk_path = os.path.join(chunks_folder, f'chunk_{chunk_index}')
        logger.info(f"💾 [CHUNK] Guardando chunk en: {chunk_path}")
        
        chunk.save(chunk_path)
        
        chunk_size = os.path.getsize(chunk_path)
        logger.info(f"✅ [CHUNK] Chunk {chunk_index + 1}/{total_chunks} guardado - Tamaño: {chunk_size / (1024*1024):.2f}MB")
        
        # Si es el último chunk, ensamblar el archivo
        if chunk_index == total_chunks - 1:
            logger.info(f"🔧 [CHUNK] Último chunk recibido, ensamblando archivo completo...")
            final_path = os.path.join(session_folder, filename)
            
            logger.info(f"📝 [CHUNK] Ruta final: {final_path}")
            
            # Ensamblar chunks en orden
            try:
                with open(final_path, 'wb') as final_file:
                    for i in range(total_chunks):
                        chunk_file_path = os.path.join(chunks_folder, f'chunk_{i}')
                        logger.info(f"📄 [CHUNK] Leyendo chunk {i+1}/{total_chunks} desde {chunk_file_path}")
                        
                        if not os.path.exists(chunk_file_path):
                            logger.error(f"❌ [CHUNK] Chunk {i} NO EXISTE en {chunk_file_path}")
                            # Listar chunks disponibles
                            available_chunks = os.listdir(chunks_folder)
                            logger.error(f"❌ [CHUNK] Chunks disponibles: {available_chunks}")
                            raise FileNotFoundError(f"Chunk {i} no encontrado en {chunk_file_path}")
                        
                        with open(chunk_file_path, 'rb') as chunk_file:
                            chunk_data = chunk_file.read()
                            final_file.write(chunk_data)
                            logger.info(f"✅ [CHUNK] Chunk {i+1}/{total_chunks} escrito - {len(chunk_data) / (1024*1024):.2f}MB")
            except Exception as assembly_error:
                logger.error(f"❌ [CHUNK] Error ensamblando archivo: {assembly_error}")
                logger.error(f"❌ [CHUNK] Tipo de error: {type(assembly_error)}")
                import traceback
                logger.error(f"❌ [CHUNK] Traceback:\n{traceback.format_exc()}")
                raise
            
            final_size = os.path.getsize(final_path)
            logger.info(f"✅ [CHUNK] Archivo completo ensamblado: {filename} - Tamaño final: {final_size / (1024*1024):.2f}MB")
            
            # Verificación rápida del archivo ensamblado: hash + apertura con OpenCV
            try:
                import hashlib
                hash_sha256 = hashlib.sha256()
                with open(final_path, 'rb') as fh:
                    for chunk_bytes in iter(lambda: fh.read(8192), b''):
                        hash_sha256.update(chunk_bytes)
                file_hash = hash_sha256.hexdigest()
                logger.info(f"🔎 [CHUNK] SHA256 del archivo ensamblado: {file_hash}")

                # Intentar abrir con OpenCV y comprobar frames/fps
                try:
                    cap_check = cv2.VideoCapture(final_path)
                    if cap_check.isOpened():
                        frames = int(cap_check.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                        fps = float(cap_check.get(cv2.CAP_PROP_FPS) or 0.0)
                        duration_s = (frames / fps) if fps > 0 else 0
                        logger.info(f"🔧 [CHUNK] Verificación OpenCV: frames={frames}, fps={fps:.2f}, duration={duration_s:.2f}s")
                    else:
                        logger.error(f"❌ [CHUNK] OpenCV no pudo abrir el archivo ensamblado: {final_path}")
                    try:
                        cap_check.release()
                    except:
                        pass
                except Exception as cv_err:
                    logger.error(f"❌ [CHUNK] Error verificando video con OpenCV: {cv_err}")
            except Exception as hash_err:
                logger.warning(f"⚠️ [CHUNK] No se pudo calcular SHA256 del archivo: {hash_err}")

            # Limpiar chunks temporales
            import shutil
            logger.info(f"🗑️ [CHUNK] Limpiando chunks temporales...")
            try:
                shutil.rmtree(chunks_folder)
                logger.info(f"✅ [CHUNK] Chunks temporales eliminados")
            except Exception as rm_err:
                logger.warning(f"⚠️ [CHUNK] Error eliminando carpeta de chunks: {rm_err}")
            
            # Insertar o verificar en BD
            is_duplicate = False
            session_db_path = active_sessions.get(folder_id, {}).get('db_path')
            
            if session_db_path:
                logger.info(f"� [CHUNK] Insertando video en BD: {session_db_path}")
                conn = db.create_db_connection(session_db_path)
                cursor = conn.cursor()
                
                # Verificar si ya existe
                cursor.execute("SELECT id FROM videos WHERE nombre_archivo = ?", (filename,))
                existing = cursor.fetchone()
                
                if existing:
                    logger.warning(f"⚠️ [CHUNK] Video duplicado encontrado en BD: {filename}")
                    is_duplicate = True
                    
                    # IMPORTANTE: Agregar a la lista INCLUSO si es duplicado para permitir reprocesar
                    if folder_id in active_sessions:
                        active_sessions[folder_id]['uploaded_videos'].append(filename)
                        logger.info(f"✅ [CHUNK] Video duplicado agregado a active_sessions para reprocesar: {filename}")
                        logger.info(f"📋 [CHUNK] Lista actual de videos: {active_sessions[folder_id]['uploaded_videos']}")
                    
                else:
                    # Insertar el video en la BD
                    try:
                        # Obtener o crear carpeta en BD
                        cursor.execute("SELECT id FROM carpetas WHERE ruta = ?", (session_folder,))
                        carpeta_row = cursor.fetchone()
                        
                        if not carpeta_row:
                            logger.info(f"📁 [CHUNK] Creando carpeta en BD: {session_folder}")
                            fecha_subida = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            cursor.execute("INSERT INTO carpetas (ruta, fecha_subida) VALUES (?, ?)", 
                                         (session_folder, fecha_subida))
                            conn.commit()
                            carpeta_id = cursor.lastrowid
                        else:
                            carpeta_id = carpeta_row[0]
                        
                        logger.info(f"📁 [CHUNK] Carpeta ID: {carpeta_id}")
                        
                        # Insertar video
                        creation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        cursor.execute(
                            "INSERT INTO videos (carpeta_id, nombre_archivo, ruta_absoluta, fecha_creacion) VALUES (?, ?, ?, ?)",
                            (carpeta_id, filename, final_path, creation_date)
                        )
                        conn.commit()
                        video_id = cursor.lastrowid
                        logger.info(f"✅ [CHUNK] Video insertado en BD con ID: {video_id}")
                        
                        # Agregar video a la lista de uploaded_videos en active_sessions
                        if folder_id in active_sessions:
                            active_sessions[folder_id]['uploaded_videos'].append(filename)
                            logger.info(f"✅ [CHUNK] Video agregado a active_sessions: {filename}")
                            logger.info(f"📋 [CHUNK] Lista actual de videos: {active_sessions[folder_id]['uploaded_videos']}")
                        else:
                            logger.warning(f"⚠️ [CHUNK] Sesión {folder_id} no encontrada en active_sessions")
                        
                    except Exception as db_error:
                        logger.error(f"❌ [CHUNK] Error al insertar en BD: {db_error}")
                        conn.rollback()
                
                conn.close()
            else:
                logger.warning(f"⚠️ [CHUNK] No se encontró DB path para sesión {folder_id}")
                is_duplicate = False
            
            response_data = {
                'success': True,
                'complete': True,
                'filename': filename,
                'filepath': final_path,
                'is_duplicate': is_duplicate
            }
            logger.info(f"✅ [CHUNK] Respuesta final: {response_data}")
            
            return jsonify(response_data)
        
        logger.info(f"✅ [CHUNK] Chunk intermedio procesado correctamente")
        return jsonify({
            'success': True,
            'complete': False,
            'chunk_index': chunk_index
        })
        
    except Exception as e:
        logger.error(f"❌ [CHUNK] Error al subir chunk: {e}")
        logger.error(f"❌ [CHUNK] Tipo de error: {type(e).__name__}")
        logger.error(f"❌ [CHUNK] Stack trace:", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/analyze-mode', methods=['GET', 'POST'])
def config_analyze_mode():
    """
    GET: Obtiene el modo actual de análisis
    POST: Cambia el modo de análisis (duplicar vs analizar desde ruta original)
    """
    global analyze_from_original_path
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'analyze_from_original': analyze_from_original_path,
            'duplicate_files': not analyze_from_original_path
        })
    
    try:
        data = request.json
        mode = data.get('mode')  # 'duplicate' o 'original'
        
        if mode == 'duplicate':
            analyze_from_original_path = False
        elif mode == 'original':
            analyze_from_original_path = True
        else:
            return jsonify({'success': False, 'error': 'Modo inválido (use: duplicate u original)'}), 400
        
        # ℹ️ Esta configuración se mantiene solo durante la sesión actual
        # Para hacerla persistente, se debería añadir a una tabla de configuración general
        logger.info(f"⚙️ Modo de análisis cambiado a: {'Analizar desde ruta original' if analyze_from_original_path else 'Duplicar archivos'}")
        
        return jsonify({
            'success': True,
            'analyze_from_original': analyze_from_original_path,
            'duplicate_files': not analyze_from_original_path,
            'message': f"Modo cambiado a: {'Analizar desde ruta original' if analyze_from_original_path else 'Duplicar archivos'}"
        })
        
    except Exception as e:
        logger.error(f"❌ Error al cambiar modo de análisis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/motion-detection', methods=['GET', 'POST'])
def motion_detection_config():
    """
    GET: Obtiene la configuración actual de detección de movimiento desde la BD
    POST: Guarda nueva configuración de detección de movimiento en la BD
    """
    global global_motion_config
    
    if request.method == 'GET':
        # Devolver configuración actual
        return jsonify({
            'success': True,
            'config': global_motion_config
        })
    
    # POST: Guardar nueva configuración
    try:
        data = request.json
        
        # Validar datos
        threshold_percentage = float(data.get('threshold_percentage', 1.0))
        var_threshold = int(data.get('var_threshold', 16))
        cooldown_ms = int(data.get('cooldown_ms', 2000))
        
        # Guardar en BD PERMANENTE usando la función de db.py
        success = db.save_motion_detection_config(threshold_percentage, var_threshold, cooldown_ms, app.config['DB_PATH'])
        
        if success:
            # Actualizar configuración global en memoria
            global_motion_config = {
                'threshold_percentage': threshold_percentage,
                'var_threshold': var_threshold,
                'cooldown_ms': cooldown_ms,
                'gaussian_blur': (5, 5),
                'morph_kernel_size': (3, 3),
                'binary_threshold': 127
            }
            
            logger.info(f"✅ Configuración de detección guardada:")
            logger.info(f"   • Threshold: {threshold_percentage}%")
            logger.info(f"   • Var threshold: {var_threshold}")
            logger.info(f"   • Cooldown: {cooldown_ms}ms")
            
            return jsonify({
                'success': True,
                'config': global_motion_config,
                'message': 'Configuración guardada correctamente'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Error al guardar configuración en la base de datos'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Error al guardar configuración de detección: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/select-local-folder', methods=['POST'])
def select_local_folder():
    """
    Endpoint para seleccionar una carpeta local del sistema de archivos.
    Recibe la ruta de la carpeta y registra sus videos en la BD.
    Dependiendo de la configuración, duplica archivos o analiza desde ruta original.
    """
    try:
        data = request.json
        folder_path = data.get('folder_path')
        duplicate_files = data.get('duplicate_files', False)  # Por defecto: no duplicar
        
        if not folder_path or not os.path.isdir(folder_path):
            return jsonify({'success': False, 'error': 'Ruta de carpeta inválida'}), 400
        
        logger.info(f"📁 Seleccionando carpeta local: {folder_path}")
        logger.info(f"📋 Modo: {'Duplicar archivos' if duplicate_files else 'Analizar desde ruta original'}")
        
        # Crear sesión
        session_id, session_db_path = get_or_create_session()
        session_folder = processing_status['session_folder_path']
        
        # Escanear archivos de video en la carpeta
        video_extensions = tuple(f".{ext}" for ext in app.config['ALLOWED_EXTENSIONS'])
        video_files = []
        
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(video_extensions):
                original_path = os.path.join(folder_path, filename)
                video_files.append((filename, original_path))
        
        if not video_files:
            return jsonify({
                'success': False,
                'error': 'No se encontraron videos en la carpeta seleccionada'
            }), 400
        
        logger.info(f"📹 Videos encontrados: {len(video_files)}")
        
        # Registrar carpeta en BD
        folder_name = os.path.basename(folder_path)
        folder_db_id = db.insert_folder(
            session_db_path,
            folder_name,
            len(video_files)
        )
        
        # Procesar cada video
        videos_registered = []
        import shutil
        
        for filename, original_path in video_files:
            try:
                if duplicate_files:
                    # Modo 1: Copiar archivo a la carpeta de sesión
                    dest_path = os.path.join(session_folder, filename)
                    logger.info(f"   📄 Copiando: {filename}")
                    shutil.copy2(original_path, dest_path)
                    video_path_for_db = dest_path
                else:
                    # Modo 2: Usar ruta original directamente
                    logger.info(f"   📄 Registrando desde ruta original: {filename}")
                    video_path_for_db = original_path
                
                # Registrar en BD
                video_id = db.insert_video(
                    session_db_path,
                    folder_db_id,
                    filename,
                    video_path_for_db  # Guardar la ruta que se usará
                )
                
                videos_registered.append({
                    'id': video_id,
                    'filename': filename,
                    'original_path': original_path,
                    'duplicated': duplicate_files
                })
                
            except Exception as e:
                logger.error(f"❌ Error procesando {filename}: {e}")
                continue
        
        logger.info(f"✅ Carpeta registrada: {len(videos_registered)} videos")
        
        return jsonify({
            'success': True,
            'folder_id': folder_db_id,
            'folder_name': folder_name,
            'session_id': session_id,
            'videos_found': len(video_files),
            'videos_registered': len(videos_registered),
            'duplicate_mode': duplicate_files,
            'videos': videos_registered
        })
        
    except Exception as e:
        logger.error(f"❌ Error al seleccionar carpeta local: {e}")
        logger.error(f"Stack trace:", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process', methods=['POST'])
def process_videos():
    """Procesa videos para detectar movimiento (con sistema de cola)"""
    global processing_status, processing_queue
    
    logger.info("🎯 Endpoint /api/process llamado")
    
    try:
        data = request.json
        logger.info(f"📦 Datos recibidos: {data}")
        
        folder_id = data.get('folder_id')
        roi = data.get('roi')  # [x, y, w, h]
        
        if not folder_id:
            logger.error("❌ No se proporcionó folder_id")
            return jsonify({'success': False, 'error': 'folder_id requerido'}), 400
        
        # ✅ VALIDACIÓN CRÍTICA: ROI no puede tener coordenadas negativas o dimensiones inválidas
        if roi:
            x, y, w, h = roi
            if x < 0 or y < 0 or w <= 0 or h <= 0:
                logger.error(f"❌ ROI inválido rechazado: {roi} (coordenadas negativas o dimensiones inválidas)")
                return jsonify({
                    'success': False,
                    'error': f'ROI inválido: Las coordenadas no pueden ser negativas y las dimensiones deben ser positivas. ROI recibido: x={x}, y={y}, w={w}, h={h}'
                }), 400
            logger.info(f"✅ ROI validado correctamente: {roi}")
        
        logger.info(f"✓ folder_id: {folder_id}, ROI: {roi}")
        
        # folder_id ahora es un session_id (session_YYYYMMDD_HHMMSS)
        session_id = folder_id
        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        
        # Usar BD única persistente en lugar de BD por sesión
        session_db_path = app.config['DB_PATH']
        
        if not os.path.exists(session_folder):
            logger.error(f"❌ Carpeta de sesión no encontrada: {session_folder}")
            return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404
        
        logger.info(f"✓ Sesión encontrada: {session_id}")
        logger.info(f"✓ BD única: {session_db_path}")
        
        # Registrar carpeta en BD de la sesión AHORA (al iniciar procesamiento)
        conn = db.create_db_connection(session_db_path)
        real_folder_id = db.insert_folder(conn, session_folder)
        conn.close()
        logger.info(f"✓ Carpeta registrada en BD de sesión con ID: {real_folder_id}")
        
        # 🎯 OBTENER VIDEOS SOLO DE LA LISTA DE SUBIDOS (no leer toda la carpeta)
        if session_id in active_sessions and active_sessions[session_id]['uploaded_videos']:
            video_files = active_sessions[session_id]['uploaded_videos'].copy()
            logger.info(f"✓ Videos a procesar de la lista de sesión: {len(video_files)} ({', '.join(video_files)})")
            
            # Limpiar la lista después de obtenerla para el procesamiento
            active_sessions[session_id]['uploaded_videos'] = []
            logger.info(f"✓ Lista de videos de sesión limpiada (procesará solo los seleccionados)")
        else:
            logger.error("❌ No hay videos en la lista de la sesión")
            return jsonify({'success': False, 'error': 'No hay videos para procesar. Por favor, suba videos primero.'}), 400
        
        # Obtener opciones de procesamiento
        generate_clips = data.get('generate_clips', True)
        use_ai_analysis = data.get('use_ai_analysis', True)
        
        # ✅ Obtener configuración de detección desde la BD (global_motion_config)
        # Si el cliente envía configuración personalizada, se usa; sino, se usa la de la BD
        motion_config = data.get('motion_config', global_motion_config)
        
        # ✅ Crear trabajo para la cola con configuración INDEPENDIENTE
        job = {
            'session_id': session_id,
            'session_db_path': session_db_path,
            'folder_id': real_folder_id,
            'folder_path': session_folder,
            'video_files': video_files,
            'video_count': len(video_files),
            'roi': roi,  # ROI específico para esta tarea
            'generate_clips': generate_clips,
            'use_ai_analysis': use_ai_analysis,
            'motion_config': motion_config,  # Configuración de detección
            'folder_name': os.path.basename(session_folder)  # Para mostrar en UI
        }
        
        # Agregar a la cola
        with queue_lock:
            processing_queue.append(job)
            queue_position = len(processing_queue)
        
        logger.info(f"🎬 Trabajo agregado a la cola (posición {queue_position})")
        logger.info(f"   Carpeta: {job['folder_name']}")
        logger.info(f"   Videos: {len(video_files)}")
        logger.info(f"   ROI: {roi}")
        logger.info(f"   Opciones: Clips={generate_clips}, IA={use_ai_analysis}")
        
        # Si no hay procesamiento activo, iniciar el procesador de cola
        if not processing_status['is_processing']:
            logger.info(f"🚀 Iniciando procesador de cola (hay {queue_position} trabajos)")
            
            # IMPORTANTE: Marcar como procesando ANTES de iniciar el thread
            # para evitar race condition con el frontend
            processing_status['is_processing'] = True
            processing_status['total_videos'] = len(video_files)
            processing_status['progress'] = 0
            processing_status['current_video'] = 'Iniciando...'
            processing_status['status_message'] = 'Preparando procesamiento...'
            logger.info("✓ Estado marcado como procesando ANTES de iniciar thread")
            
            start_queue_processor()
        else:
            logger.info(f"⏳ Trabajo agregado a cola (ya hay procesamiento activo, posición {queue_position})")
        
        return jsonify({
            'success': True, 
            'message': 'Trabajo agregado a la cola' if queue_position > 1 else 'Procesamiento iniciado',
            'queue_position': queue_position,
            'is_processing': processing_status['is_processing']
        })
    
    except Exception as e:
        logger.error(f"Error al agregar trabajo a la cola: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def start_queue_processor():
    """Inicia el procesador de cola en un thread separado"""
    logger.info("🔄 Creando thread del procesador de cola...")
    thread = threading.Thread(target=process_queue)
    thread.daemon = True
    thread.start()
    logger.info("✅ Thread del procesador de cola iniciado")

def process_queue():
    """Procesa trabajos de la cola secuencialmente"""
    global processing_status, processing_queue
    
    logger.info("📋 Procesador de cola iniciado, revisando trabajos...")
    
    # Inicializar contadores ACUMULADOS para toda la cola (no resetear entre trabajos)
    processing_status['total_videos_in_queue'] = sum(len(j['video_files']) for j in processing_queue)
    processing_status['total_videos_processed_all'] = 0
    processing_status['motion_events_detected_all'] = 0
    processing_status['clips_generated_all'] = 0
    processing_status['objects_detected_all'] = 0
    
    logger.info(f"📊 Total de videos en cola: {processing_status['total_videos_in_queue']}")
    
    while True:
        # Resetear contadores del TRABAJO ACTUAL al inicio de cada trabajo
        processing_status['total_videos_processed'] = 0
        processing_status['motion_events_detected'] = 0
        processing_status['clips_generated'] = 0
        processing_status['objects_detected'] = 0
        processing_status['videos_processed_in_job'] = 0
        
        # Obtener siguiente trabajo de la cola
        job = None
        with queue_lock:
            if processing_queue:
                job = processing_queue.pop(0)
                logger.info(f"📦 Obtenido trabajo de la cola. Quedan {len(processing_queue)} trabajos")
            else:
                # No hay más trabajos, salir
                logger.info("✓ Cola vacía, finalizando procesador")
                break
        
        if not job:
            break
        
        # Procesar el trabajo
        logger.info(f"🎬 Iniciando procesamiento de trabajo: folder_id={job['folder_id']}, {len(job['video_files'])} videos")
        process_single_job(job)
        logger.info(f"✅ Trabajo completado")
    
    # Todos los trabajos completados
    processing_status['is_processing'] = False
    logger.info("🏁 Procesador de cola finalizado, is_processing=False")

def calculate_event_datetime(base_timestamp_str, event_ms):
    """
    Calcula la fecha/hora de un evento sumando el tiempo del evento al timestamp base del video.
    
    Args:
        base_timestamp_str: Timestamp base del video en formato 'dd-mm-yyyy hh:mm:ss'
        event_ms: Tiempo del evento en milisegundos desde el inicio del video
    
    Returns:
        str: Fecha del evento en formato 'dd-mm-yyyy hh:mm:ss'
    """
    try:
        from datetime import datetime, timedelta
        
        # Parsear timestamp base (formato: 'dd-mm-yyyy hh:mm:ss')
        base_datetime = datetime.strptime(base_timestamp_str, '%d-%m-%Y %H:%M:%S')
        
        # Calcular offset en segundos
        event_seconds = event_ms / 1000.0
        
        # Sumar el tiempo del evento al timestamp base
        event_datetime = base_datetime + timedelta(seconds=event_seconds)
        
        # Formatear de vuelta a string
        return event_datetime.strftime('%d-%m-%Y %H:%M:%S')
        
    except Exception as e:
        logger.error(f"Error calculando fecha del evento (base: {base_timestamp_str}, ms: {event_ms}): {e}")
        # Fallback: usar fecha del sistema
        return datetime.now().strftime('%d-%m-%Y %H:%M:%S')

def detect_motion_in_frame(prev_frame, curr_frame, roi):
    # ROI: [x, y, w, h]
    x, y, w, h = roi
    prev_roi = prev_frame[y:y+h, x:x+w]
    curr_roi = curr_frame[y:y+h, x:x+w]
    diff = cv2.absdiff(prev_roi, curr_roi)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 25, 255, cv2.THRESH_BINARY)[1]
    motion_score = np.sum(thresh) / 255
    return motion_score > 500  # Umbral simple, ajustable

@app.route('/api/live/start', methods=['POST'])
def start_live_analysis():
    """
    Inicia el análisis en tiempo real del stream MJPEG.
    Espera JSON: { "stream_url": "...", "roi": [x, y, w, h] }
    """
    data = request.get_json()
    stream_url = data.get('stream_url')
    roi = data.get('roi', [0, 0, 640, 480])

    if not stream_url:
        return jsonify({'success': False, 'error': 'stream_url requerido'}), 400

    # Log: inicio de análisis en directo y ROI recibido (en buffer y archivo físico)
    log_msg = f'🔴 [LIVE] Iniciando análisis en directo. URL: {stream_url}, ROI: {roi}'
    live_event_logs.append({
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'message': log_msg
    })
    logger.info(log_msg)

    # Log físico detallado del ROI recibido
    logger.info(f"[LIVE] ROI recibido: x={roi[0]}, y={roi[1]}, w={roi[2]}, h={roi[3]}")

    # Log de parámetros de análisis en directo
    logger.info(f"[LIVE] Parámetros de análisis: stream_url={stream_url}, ROI={roi}")

    # Procesar el stream MJPEG en un thread
    def live_analysis_worker(stream_url, roi):
        logger.info(f"[LIVE] Thread de análisis en directo iniciado para stream: {stream_url}")
        try:
            import requests
            import cv2
            import numpy as np
            from datetime import datetime

            # Conectar al stream MJPEG
            cap = cv2.VideoCapture(stream_url)
            if not cap.isOpened():
                logger.error(f"[LIVE] No se pudo abrir el stream: {stream_url}")
                return

            logger.info(f"[LIVE] Stream abierto correctamente. Procesando frames...")
            prev_frame = None
            frame_count = 0
            motion_events = 0
            last_motion_frame = -1000  # Para controlar el umbral de frames entre eventos
            MOTION_FRAME_GAP =200      # Mínimo de frames entre logs de movimiento
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    logger.warning(f"[LIVE] No se pudo leer frame {frame_count} del stream.")
                    break
                frame_count += 1
                # Validar dimensiones del frame y ROI
                x, y, w, h = roi
                frame_h, frame_w = frame.shape[:2]
                if (x < 0 or y < 0 or w <= 0 or h <= 0 or x+w > frame_w or y+h > frame_h):
                    if frame_count == 1:
                        logger.warning(f"[LIVE] ROI fuera de límites del frame. Frame: {frame_w}x{frame_h}, ROI: {roi}")
                    continue
                roi_frame = frame[y:y+h, x:x+w]
                if roi_frame is None or roi_frame.size == 0:
                    if frame_count == 1:
                        logger.warning(f"[LIVE] ROI vacío en frame {frame_count}. ROI: {roi}")
                    continue
                if prev_frame is not None:
                    prev_roi = prev_frame[y:y+h, x:x+w]
                    if prev_roi is None or prev_roi.size == 0:
                        continue
                    try:
                        diff = cv2.absdiff(prev_roi, roi_frame)
                        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                        thresh = cv2.threshold(gray, 25, 255, cv2.THRESH_BINARY)[1]
                        motion_score = np.sum(thresh) / 255
                        if motion_score > 500:
                            # Solo loguear si han pasado MOTION_FRAME_GAP frames desde el último evento Y si hay al menos MOTION_FRAME_GAP frames procesados
                            if frame_count >= MOTION_FRAME_GAP and frame_count - last_motion_frame >= MOTION_FRAME_GAP:
                                motion_events += 1
                                last_motion_frame = frame_count
                                event_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                logger.info(f"[LIVE] 🚨 Movimiento detectado en frame {frame_count} (score={motion_score}) | ROI={roi} | {event_time}")
                                live_event_logs.append({
                                    'timestamp': event_time,
                                    'message': f'🚨 Movimiento detectado en frame {frame_count} (score={motion_score})'
                                })
                    except Exception as e:
                        logger.error(f"[LIVE] Error procesando frame {frame_count}: {e}")
                prev_frame = frame.copy()
                # Eliminar límite de frames: el análisis nunca termina automáticamente
            cap.release()
            logger.info(f"[LIVE] Análisis en directo finalizado. Frames procesados: {frame_count}, eventos de movimiento: {motion_events}")
        except Exception as e:
            logger.error(f"[LIVE] Error en análisis en directo: {type(e).__name__}: {e}")

    import threading
    thread = threading.Thread(target=live_analysis_worker, args=(stream_url, roi))
    thread.daemon = True
    thread.start()
    def process_stream():
        try:
                resp = requests.get(stream_url, stream=True, timeout=5)
                bytes_data = b''
                prev_frame = None
                frame_count = 0
                logger.info(f"live_analysis | 🔴 Iniciando análisis en directo. URL: {stream_url}, ROI: {roi}")
                for chunk in resp.iter_content(chunk_size=1024):
                    bytes_data += chunk
                    a = bytes_data.find(b'\xff\xd8')
                    b = bytes_data.find(b'\xff\xd9')
                    if a != -1 and b != -1:
                        jpg = bytes_data[a:b+2]
                        bytes_data = bytes_data[b+2:]
                        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        frame_count += 1
                        if frame is not None:
                            if prev_frame is not None:
                                try:
                                    motion = detect_motion_in_frame(prev_frame, frame, roi)
                                    if motion:
                                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                        msg = f"Movimiento detectado en frame {frame_count} (ROI: {roi})"
                                        live_event_logs.append({
                                            'timestamp': timestamp,
                                            'message': msg,
                                        })
                                        logger.info(f"live_analysis | {msg}")
                                    else:
                                        live_event_logs.append({
                                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                            'message': msg
                                        })
                                        logger.info(f"live_analysis | {msg}")
                                except Exception as err:
                                    msg = f"Error procesando frame {frame_count}: {err}"
                                    live_event_logs.append({
                                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                        'message': msg
                                    })
                                    logger.error(f"live_analysis | {msg}")
                            else:
                                live_event_logs.append({
                                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'message': msg
                                })
                                logger.info(f"live_analysis | {msg}")
                            prev_frame = frame
                        else:
                            msg = f"Frame {frame_count}: Frame inválido (None)"
                            live_event_logs.append({
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'message': msg
                            })
                            logger.warning(f"live_analysis | {msg}")
        except Exception as e:
            msg = f"Error en stream: {e}"
            # No agregar el error al buffer de eventos para frontend
            logger.error(f"live_analysis | {msg}")

    threading.Thread(target=process_stream, daemon=True).start()
    return jsonify({'success': True, 'message': 'Análisis en directo iniciado'})

@app.route('/api/live/logs', methods=['GET'])
def get_live_logs():
    # Devuelve los logs de eventos en directo
    return jsonify({'success': True, 'logs': list(live_event_logs)})

def process_single_job(job):
    """
    🔥 ARQUITECTURA CORREGIDA: Procesa UNA tarea completa de forma SECUENCIAL
    - Thread principal del servidor maneja la cola
    - Este job procesa videos EN PARALELO dentro de la tarea
    - Cada video procesa clips EN PARALELO
    - Una única conexión de BD para insertar todo el job
    """
    global processing_status
    
    session_id = job['session_id']
    session_db_path = job['session_db_path']
    folder_id = job['folder_id']
    folder_path = job['folder_path']
    video_files = job['video_files']
    roi = job['roi']
    generate_clips = job['generate_clips']
    use_ai_analysis = job['use_ai_analysis']
    motion_config = job.get('motion_config', {})
    folder_name = job.get('folder_name', 'Carpeta')
    
    logger.info(f"🎯 Procesando trabajo:")
    logger.info(f"   • Sesión: {session_id}")
    logger.info(f"   • Carpeta: {folder_name}")
    logger.info(f"   • BD de sesión: {session_db_path}")
    logger.info(f"   • Ruta: {folder_path}")
    logger.info(f"   • Videos: {len(video_files)}")
    logger.info(f"   • ROI: {roi}")
    logger.info(f"   • Generar clips: {generate_clips}")
    logger.info(f"   • Análisis IA: {use_ai_analysis}")
    logger.info(f"   • Config movimiento: {motion_config}")
    
    # Actualizar estado global (NO resetear contadores acumulados)
    processing_status['just_completed'] = False
    processing_status['total_videos'] = len(video_files)  # Total de videos ESTE trabajo
    processing_status['progress'] = 0
    processing_status['current_video'] = 'Preparando...'
    processing_status['current_folder'] = folder_name
    processing_status['status_message'] = f'Iniciando procesamiento de {folder_name}...'
    
    logger.info("✓ Estado inicial configurado")
    
    # ✅ CREAR CONEXIÓN ÚNICA DE BD PARA TODO EL TRABAJO
    # Esta conexión NO se comparte entre threads, cada thread trabaja con datos en memoria
    main_conn = db.create_db_connection(session_db_path)
    cursor = main_conn.cursor()
    
    # ✅ PERMITIR VIDEOS DUPLICADOS - El mismo video se puede analizar múltiples veces
    # (Ya no borramos análisis anteriores del mismo video)
    
    # 🎯 PROCESAR VIDEOS SECUENCIALMENTE (para evitar conflictos de archivos temp)
    logger.info(f"� Procesando {len(video_files)} videos SECUENCIALMENTE...")
    
    videos_processed = 0
    total_motion_events = 0
    total_clips_created = 0
    total_objects_detected = 0
    
    for video_idx, video_file in enumerate(video_files):
        video_path = os.path.join(folder_path, video_file)
        logger.info(f"🎬 Procesando video {video_idx+1}/{len(video_files)}: {video_file}")
        
        # ✅ EXTRAER TIMESTAMP BASE DEL VIDEO UNA SOLA VEZ (OCR del primer frame)
        logger.info(f"⏰ Extrayendo timestamp base del video: {video_file}")
        video_base_timestamp = video_processing.extract_timestamp_from_video_at_ms(video_path, 0)  # Frame 0 = timestamp base
        
        if video_base_timestamp:
            logger.info(f"✅ Timestamp base del video: {video_base_timestamp}")
        else:
            logger.warning(f"⚠️ No se pudo extraer timestamp base, usando fecha del sistema")
            video_base_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Actualizar estado global SOLO para mostrar el video actual y fase
        processing_status['current_video'] = video_file
        processing_status['progress'] = video_idx + 1
        processing_status['current_phase'] = 'detecting_motion'
        processing_status['status_message'] = f'Video {video_idx+1}/{len(video_files)}: {video_file}'
        
        try:
            # Insertar video en BD
            creation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            video_id = db.insert_video(main_conn, folder_id, video_file, video_path, creation_date, roi)
            
            # FASE 1: Detectar movimiento
            config = video_processing.get_motion_detection_config()
            motion_events = video_processing.process_video_for_motion_advanced(
                video_path, tuple(roi) if roi else None, config
            )
            total_motion_events += len(motion_events)
            processing_status['motion_events_detected'] = total_motion_events
            logger.info(f"✓ [{video_file}] Detectados {len(motion_events)} eventos de movimiento")
            
            # Marcar video como procesado tras detectar movimientos
            videos_processed += 1
            processing_status['videos_processed_in_job'] = videos_processed
            processing_status['total_videos_processed'] = processing_status.get('total_videos_processed', 0) + 1
            processing_status['total_videos_processed_all'] = processing_status.get('total_videos_processed_all', 0) + 1
            
            # FASE 2: Generar clips si está activado
            if generate_clips and motion_events:
                clips_dir = os.path.join(folder_path, 'clips_analisis')
                os.makedirs(clips_dir, exist_ok=True)
                logger.info(f"🎞️ Generando {len(motion_events)} clips para {video_file}...")
                for clip_idx, event_ms in enumerate(motion_events):
                    try:
                        clip_path = video_processing.create_clip_from_event(
                            video_path, event_ms, roi_coords=tuple(roi) if roi else None
                        )
                        if clip_path and os.path.exists(clip_path):
                            clip_filename = os.path.basename(clip_path)
                            final_clip_path = os.path.join(clips_dir, clip_filename)
                            if clip_path != final_clip_path:
                                import shutil
                                shutil.move(clip_path, final_clip_path)
                            total_clips_created += 1
                            processing_status['clips_generated'] = total_clips_created
                            object_type = None
                            object_color = None
                            # FASE 3: Detectar objetos si está activado
                            if use_ai_analysis:
                                object_type, object_color = video_processing.process_event_with_clip_analysis(
                                    final_clip_path, event_ms, tuple(roi) if roi else None
                                )
                                if object_type:
                                    total_objects_detected += 1
                                    processing_status['objects_detected'] = total_objects_detected
                                    logger.info(f"✓ [{video_file}] Objeto detectado: {object_type} ({object_color})")
                            
                            # ✅ CALCULAR FECHA DEL EVENTO: timestamp_base + event_ms
                            event_datetime = calculate_event_datetime(video_base_timestamp, event_ms)
                            logger.info(f"📅 [{video_file}] Evento {clip_idx+1}: {event_datetime} (base: {video_base_timestamp} + {event_ms}ms)")
                            
                            db.insert_clip(main_conn, video_id, clip_filename, final_clip_path, 
                                         event_ms, event_datetime, object_type, object_color)
                            logger.info(f"✓ [{video_file}] Clip {clip_idx+1}/{len(motion_events)}: {clip_filename}")
                    except Exception as e:
                        logger.error(f"❌ [{video_file}] Error al crear clip en {event_ms}ms: {e}")
            elif not generate_clips and motion_events:
                # Modo sin clips: solo registrar eventos
                for event_ms in motion_events:
                    object_type = None
                    object_color = None
                    if use_ai_analysis:
                        try:
                            object_type, object_color = video_processing.analyze_frame_at_timestamp(
                                video_path, event_ms, tuple(roi) if roi else None
                            )
                            if object_type:
                                total_objects_detected += 1
                                processing_status['objects_detected'] = total_objects_detected
                        except Exception as e:
                            logger.warning(f"⚠️ Error al analizar frame: {e}")
                    
                    # ✅ CALCULAR FECHA DEL EVENTO: timestamp_base + event_ms
                    event_datetime = calculate_event_datetime(video_base_timestamp, event_ms)
                    logger.info(f"📅 [{video_file}] Evento sin clip: {event_datetime} (base: {video_base_timestamp} + {event_ms}ms)")
                    
                    db.insert_clip(main_conn, video_id, f"event_{event_ms}ms", None, 
                                 event_ms, event_datetime, object_type, object_color)
            
            logger.info(f"✅ Video completado: {video_file} - Eventos: {len(motion_events)}")
        except Exception as e:
            logger.error(f"❌ Error al procesar video {video_file}: {e}")
    
    # Cerrar conexión de BD
    main_conn.close()
    
    # Generar reporte Excel de la carpeta individual
    try:
        create_excel_report(folder_id, folder_path)
    except Exception as e:
        logger.error(f"Error al generar reporte Excel individual: {e}")
    
    # Actualizar Excel CONSOLIDADO de TODA la sesión después de cada trabajo
    try:
        session_excel_path = create_or_update_session_excel(session_db_path, folder_path)
        if session_excel_path:
            logger.info(f"✅ Excel consolidado de sesión actualizado: {session_excel_path}")
            # Actualizar el path en processing_status
            processing_status['session_excel_path'] = session_excel_path
        else:
            logger.warning("⚠️ No se pudo actualizar el Excel consolidado de sesión")
    except Exception as e:
        logger.error(f"Error al actualizar reporte Excel consolidado: {e}")
    
    # ACUMULAR totales del trabajo completado en los contadores globales
    processing_status['motion_events_detected_all'] = processing_status.get('motion_events_detected_all', 0) + total_motion_events
    processing_status['clips_generated_all'] = processing_status.get('clips_generated_all', 0) + total_clips_created
    processing_status['objects_detected_all'] = processing_status.get('objects_detected_all', 0) + total_objects_detected
    
    # AGREGAR LA TAREA COMPLETADA A LA LISTA DE COMPLETADAS
    completed_task = {
        'folder_name': folder_name,
        'video_count': len(video_files),
        'videos_processed': videos_processed,
        'motion_events': total_motion_events,
        'clips_generated': total_clips_created,
        'objects_detected': total_objects_detected,
        'completed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'generate_clips': generate_clips,
        'use_ai_analysis': use_ai_analysis
    }
    processing_status['completed_tasks'].append(completed_task)
    
    # LIMITAR A LAS ÚLTIMAS 10 TAREAS COMPLETADAS PARA NO ACUMULAR DEMASIADO
    if len(processing_status['completed_tasks']) > 10:
        processing_status['completed_tasks'] = processing_status['completed_tasks'][-10:]
    
    # Marcar como completado
    processing_status['status_message'] = f'¡Procesamiento completado! {videos_processed} videos'
    processing_status['last_completed'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    processing_status['just_completed'] = True
    
    logger.info(f"✅ TRABAJO COMPLETADO:")
    logger.info(f"   • Videos procesados: {videos_processed}/{len(video_files)}")
    logger.info(f"   • Eventos detectados: {total_motion_events}")
    logger.info(f"   • Clips generados: {total_clips_created}")
    logger.info(f"   • Objetos detectados: {total_objects_detected}")
    logger.info(f"   • TOTALES ACUMULADOS:")
    logger.info(f"     - Videos totales: {processing_status.get('total_videos_processed_all', 0)}")
    logger.info(f"     - Eventos totales: {processing_status.get('motion_events_detected_all', 0)}")
    logger.info(f"     - Clips totales: {processing_status.get('clips_generated_all', 0)}")
    logger.info(f"     - Objetos totales: {processing_status.get('objects_detected_all', 0)}")

@app.route('/api/processing-status', methods=['GET'])
def get_processing_status():
    """Obtiene el estado actual del procesamiento con información detallada de la cola"""
    with queue_lock:
        # Información detallada de cada tarea en cola
        queue_details = []
        for idx, job in enumerate(processing_queue):
            queue_details.append({
                'position': idx + 1,
                'folder_name': job.get('folder_name', 'Carpeta'),
                'video_count': job.get('video_count', 0),
                'generate_clips': job.get('generate_clips', True),
                'use_ai_analysis': job.get('use_ai_analysis', True),
                'roi': job.get('roi', [0, 0, 0, 0])
            })
        
        queue_info = {
            'pending_jobs': len(processing_queue),
            'tasks': queue_details
        }
        
        # NO auto-limpiar just_completed (dejarlo para que el frontend lo detecte)
        just_completed_flag = processing_status.get('just_completed', False)
    
    # Solo loggear cambios de estado, no cada polling
    current_is_processing = processing_status.get('is_processing', False)
    if not hasattr(get_processing_status, '_last_logged_state'):
        get_processing_status._last_logged_state = None
    
    if get_processing_status._last_logged_state != current_is_processing:
        logger.info(f"📊 Estado de procesamiento: is_processing={current_is_processing}, just_completed={just_completed_flag}")
        get_processing_status._last_logged_state = current_is_processing
    
    return jsonify({
        'is_processing': processing_status.get('is_processing', False),
        'current_video': processing_status.get('current_video', ''),
        'progress': processing_status.get('progress', 0),
        'total_videos': processing_status.get('total_videos', 0),  # Total de videos en el trabajo ACTUAL
        'videos_processed_in_job': processing_status.get('videos_processed_in_job', 0),  # Videos completados en el trabajo ACTUAL
        'total_videos_in_queue': processing_status.get('total_videos_in_queue', 0),  # Total en toda la cola
        'total_videos_processed': processing_status.get('total_videos_processed', 0),  # Total procesados en el trabajo ACTUAL
        'total_videos_processed_all': processing_status.get('total_videos_processed_all', 0),  # Total procesados ACUMULADOS en toda la cola
        'status_message': processing_status.get('status_message', ''),  # Mensaje completo
        'current_folder': processing_status.get('current_folder', ''),  # Carpeta actual
        'motion_events_detected': processing_status.get('motion_events_detected', 0),  # Eventos en el trabajo ACTUAL
        'motion_events_detected_all': processing_status.get('motion_events_detected_all', 0),  # Eventos ACUMULADOS en toda la cola
        'clips_generated': processing_status.get('clips_generated', 0),  # Clips en el trabajo ACTUAL
        'clips_generated_all': processing_status.get('clips_generated_all', 0),  # Clips ACUMULADOS en toda la cola
        'objects_detected': processing_status.get('objects_detected', 0),  # Objetos en el trabajo ACTUAL
        'objects_detected_all': processing_status.get('objects_detected_all', 0),  # Objetos ACUMULADOS en toda la cola
        'last_completed': processing_status.get('last_completed'),
        'just_completed': just_completed_flag,
        'queue': queue_info,
        'completed_tasks': processing_status.get('completed_tasks', [])  # Lista de tareas completadas
    })

@app.route('/api/clip/<int:clip_id>', methods=['GET'])
def get_clip_details(clip_id):
    """Obtiene detalles de un clip específico (o evento sin clip)"""
    try:
        session_db_path = get_session_db()
        if not session_db_path:
            return jsonify({'success': False, 'error': 'No hay sesión activa'}), 404
        
        conn = db.create_db_connection(session_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, nombre_archivo, ruta_absoluta, tiempo_evento_ms, fecha_evento,
                   objeto_detectado, color_detectado
            FROM clips WHERE id = ?
        """, (clip_id,))
        clip = cursor.fetchone()
        conn.close()
        
        if not clip:
            return jsonify({'success': False, 'error': 'Clip no encontrado'}), 404
        
        # Si hay ruta de clip, generar ruta relativa. Si no, es solo un evento
        clip_path = clip[2]
        if clip_path:
            clips_dir = os.path.dirname(clip_path)
            ruta_relativa = os.path.basename(clip_path)
        else:
            clips_dir = None
            ruta_relativa = None
        
        # Calcular tiempo transcurrido desde inicio del video
        tiempo_evento_ms = clip[3] if clip[3] is not None else 0
        tiempo_segundos = tiempo_evento_ms / 1000.0
        minutos = int(tiempo_segundos // 60)
        segundos = int(tiempo_segundos % 60)
        tiempo_formateado = f"{minutos:02d}:{segundos:02d}"
        
        return jsonify({
            'success': True,
            'clip': {
                'id': clip[0],
                'nombre': clip[1],
                'ruta_relativa': ruta_relativa,
                'timestamp': clip[4],
                'tiempo_video': tiempo_formateado,  # Tiempo desde inicio (MM:SS)
                'tiempo_video_ms': tiempo_evento_ms,  # Milisegundos originales
                'detected_object': clip[5],
                'color': clip[6],
                'has_clip': clip_path is not None  # Flag para saber si tiene archivo MP4
            }
        })
    except Exception as e:
        logger.error(f"Error al obtener detalles del clip: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clip/<int:clip_id>', methods=['PUT'])
def update_clip(clip_id):
    """Actualiza los datos de un clip (objeto, color, fecha)"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No se enviaron datos'}), 400
        
        session_db_path = get_session_db()
        if not session_db_path:
            return jsonify({'success': False, 'error': 'No hay sesión activa'}), 404
        
        conn = db.create_db_connection(session_db_path)
        cursor = conn.cursor()
        
        # Verificar que el clip existe
        cursor.execute("SELECT id FROM clips WHERE id = ?", (clip_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Clip no encontrado'}), 404
        
        # Construir UPDATE dinámico solo con campos enviados
        updates = []
        params = []
        
        if 'detected_object' in data:
            updates.append("objeto_detectado = ?")
            params.append(data['detected_object'])
        
        if 'color' in data:
            updates.append("color_detectado = ?")
            params.append(data['color'])
        
        if 'timestamp' in data:
            updates.append("fecha_evento = ?")
            params.append(data['timestamp'])
        
        if not updates:
            conn.close()
            return jsonify({'success': False, 'error': 'No hay campos para actualizar'}), 400
        
        params.append(clip_id)
        query = f"UPDATE clips SET {', '.join(updates)} WHERE id = ?"
        
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Clip {clip_id} actualizado: {data}")
        
        return jsonify({
            'success': True,
            'message': 'Clip actualizado correctamente'
        })
        
    except Exception as e:
        logger.error(f"Error al actualizar clip: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clip/<int:clip_id>', methods=['DELETE'])
def delete_clip(clip_id):
    """Elimina un clip de la base de datos y opcionalmente del disco"""
    try:
        data = request.json or {}
        delete_from_disk = data.get('delete_from_disk', False)
        
        session_db_path = get_session_db()
        if not session_db_path:
            return jsonify({'success': False, 'error': 'No hay sesión activa'}), 404
        
        conn = db.create_db_connection(session_db_path)
        cursor = conn.cursor()
        
        # Obtener ruta del clip
        cursor.execute("SELECT ruta_absoluta FROM clips WHERE id = ?", (clip_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'Clip no encontrado'}), 404
        
        clip_path = result[0]
        
        # Eliminar del disco si se solicitó y si existe ruta (puede ser None en modo sin clips)
        file_deleted = False
        if delete_from_disk and clip_path and os.path.exists(clip_path):
            try:
                os.remove(clip_path)
                logger.info(f"Clip eliminado del disco: {clip_path}")
                file_deleted = True
            except Exception as e:
                logger.error(f"Error al eliminar archivo {clip_path}: {e}")
        elif not clip_path:
            logger.info(f"Evento sin clip (no hay archivo para eliminar)")
        
        # Eliminar de la base de datos
        cursor.execute("DELETE FROM clips WHERE id = ?", (clip_id,))
        conn.commit()
        conn.close()
        
        # Actualizar el Excel de sesión después de eliminar el clip
        session_id = processing_status.get('session_id')
        if session_id:
            session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
            create_or_update_session_excel(session_db_path, session_folder)
        
        return jsonify({
            'success': True,
            'message': 'Evento/Clip eliminado correctamente',
            'deleted_from_disk': file_deleted,
            'had_clip': clip_path is not None
        })
    
    except Exception as e:
        logger.error(f"Error al eliminar clip: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/video/<int:video_id>', methods=['DELETE'])
def delete_video(video_id):
    """Elimina un video y todos sus clips de la sesión actual"""
    try:
        session_db_path = get_session_db()
        if not session_db_path:
            return jsonify({'success': False, 'error': 'No hay sesión activa'}), 404
        
        conn = db.create_db_connection(session_db_path)
        cursor = conn.cursor()
        
        # Obtener ruta del video original
        cursor.execute("SELECT ruta_absoluta FROM videos WHERE id = ?", (video_id,))
        video_result = cursor.fetchone()
        
        deleted_files = 0
        
        # Eliminar video original del disco (si está en uploads)
        if video_result:
            video_path = video_result[0]
            if os.path.exists(video_path) and 'uploads' in video_path:
                try:
                    os.remove(video_path)
                    deleted_files += 1
                    logger.info(f"✓ Video eliminado del disco: {video_path}")
                    
                    # Eliminar también el archivo _preview.mp4 de la carpeta temp si existe
                    video_filename = os.path.basename(video_path)
                    preview_filename = video_filename.rsplit('.', 1)[0] + '_preview.mp4'
                    temp_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
                    preview_path = os.path.join(temp_folder, preview_filename)
                    
                    if os.path.exists(preview_path):
                        os.remove(preview_path)
                        deleted_files += 1
                        logger.info(f"✓ Preview eliminado de temp: {preview_filename}")
                        
                except Exception as e:
                    logger.error(f"Error al eliminar video {video_path}: {e}")
        
        # Obtener todos los clips del video
        cursor.execute("SELECT ruta_absoluta FROM clips WHERE video_id = ?", (video_id,))
        clips = cursor.fetchall()
        
        # Eliminar clips del disco
        for clip in clips:
            clip_path = clip[0]
            if clip_path and os.path.exists(clip_path):
                try:
                    os.remove(clip_path)
                    deleted_files += 1
                    logger.info(f"✓ Clip eliminado: {clip_path}")
                except Exception as e:
                    logger.error(f"Error al eliminar clip {clip_path}: {e}")
        
        # Eliminar clips de la BD
        cursor.execute("DELETE FROM clips WHERE video_id = ?", (video_id,))
        
        # Eliminar video de la BD
        cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        
        conn.commit()
        conn.close()
        
        # Actualizar el Excel de sesión después de eliminar el video y sus clips
        session_id = processing_status.get('session_id')
        if session_id:
            session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
            create_or_update_session_excel(session_db_path, session_folder)
        
        return jsonify({
            'success': True,
            'message': 'Video eliminado correctamente',
            'deleted_files': deleted_files
        })
    
    except Exception as e:
        logger.error(f"Error al eliminar video: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/folder/<int:folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    """Elimina una carpeta y todos sus videos y clips de la sesión actual"""
    try:
        session_db_path = get_session_db()
        if not session_db_path:
            return jsonify({'success': False, 'error': 'No hay sesión activa'}), 404
        
        conn = db.create_db_connection(session_db_path)
        cursor = conn.cursor()
        
        # Obtener ruta de la carpeta y todos los videos
        cursor.execute("SELECT ruta FROM carpetas WHERE id = ?", (folder_id,))
        folder_result = cursor.fetchone()
        
        deleted_files = 0
        
        if folder_result:
            folder_path = folder_result[0]
            logger.info(f"🗑️ Eliminando carpeta: {folder_path}")
            
            # Obtener todos los videos de la carpeta
            cursor.execute("SELECT ruta_absoluta FROM videos WHERE carpeta_id = ?", (folder_id,))
            videos = cursor.fetchall()
            
            # Eliminar videos del disco (si están en uploads)
            for video in videos:
                video_path = video[0]
                if os.path.exists(video_path) and 'uploads' in video_path:
                    try:
                        os.remove(video_path)
                        deleted_files += 1
                        logger.info(f"✓ Video eliminado: {video_path}")
                        
                        # Eliminar también el archivo _preview.mp4 de la carpeta temp si existe
                        video_filename = os.path.basename(video_path)
                        preview_filename = video_filename.rsplit('.', 1)[0] + '_preview.mp4'
                        temp_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
                        preview_path = os.path.join(temp_folder, preview_filename)
                        
                        if os.path.exists(preview_path):
                            os.remove(preview_path)
                            deleted_files += 1
                            logger.info(f"✓ Preview eliminado de temp: {preview_filename}")
                            
                    except Exception as e:
                        logger.error(f"Error al eliminar video {video_path}: {e}")
        
        # Obtener todos los clips de la carpeta
        cursor.execute("""
            SELECT c.ruta_absoluta
            FROM clips c
            JOIN videos v ON c.video_id = v.id
            WHERE v.carpeta_id = ?
        """, (folder_id,))
        clips = cursor.fetchall()
        
        # Eliminar clips del disco
        for clip in clips:
            clip_path = clip[0]
            if clip_path and os.path.exists(clip_path):
                try:
                    os.remove(clip_path)
                    deleted_files += 1
                    logger.info(f"✓ Clip eliminado: {clip_path}")
                except Exception as e:
                    logger.error(f"Error al eliminar clip {clip_path}: {e}")
        
        # Eliminar carpeta física si está en uploads y está vacía
        if folder_result:
            folder_path = folder_result[0]
            if os.path.exists(folder_path) and 'uploads' in folder_path:
                try:
                    # Eliminar subcarpeta de clips si existe
                    clips_dir = os.path.join(folder_path, 'clips_analisis')
                    if os.path.exists(clips_dir):
                        import shutil
                        shutil.rmtree(clips_dir)
                        logger.info(f"✓ Carpeta de clips eliminada: {clips_dir}")
                    
                    # Verificar si la carpeta está vacía y eliminarla
                    if not os.listdir(folder_path):
                        os.rmdir(folder_path)
                        logger.info(f"✓ Carpeta eliminada: {folder_path}")
                    else:
                        logger.warning(f"⚠️ Carpeta no vacía, no se eliminó: {folder_path}")
                        
                except Exception as e:
                    logger.error(f"Error al eliminar carpeta {folder_path}: {e}")
        
        # Eliminar clips de la BD
        cursor.execute("""
            DELETE FROM clips WHERE video_id IN (
                SELECT id FROM videos WHERE carpeta_id = ?
            )
        """, (folder_id,))
        
        # Eliminar videos de la BD
        cursor.execute("DELETE FROM videos WHERE carpeta_id = ?", (folder_id,))
        
        # Eliminar carpeta de la BD
        cursor.execute("DELETE FROM carpetas WHERE id = ?", (folder_id,))
        
        conn.commit()
        conn.close()
        
        # Actualizar el Excel de sesión después de eliminar la carpeta y todos sus datos
        session_id = processing_status.get('session_id')
        if session_id:
            session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
            create_or_update_session_excel(session_db_path, session_folder)
        
        return jsonify({
            'success': True,
            'message': 'Carpeta eliminada correctamente',
            'deleted_files': deleted_files
        })
    
    except Exception as e:
        logger.error(f"Error al eliminar carpeta: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clear-completed-flag', methods=['POST'])
def clear_completed_flag():
    """Limpia el flag de procesamiento completado"""
    global processing_status
    processing_status['just_completed'] = False
    return jsonify({'success': True})

@app.route('/api/config/roi', methods=['POST'])
def save_roi_config():
    """Guarda la configuración del ROI"""
    try:
        data = request.json
        roi_config = {
            'x': data.get('x', 0),
            'y': data.get('y', 0),
            'w': data.get('w', 200),
            'h': data.get('h', 80)
        }
        
        # Guardar en un archivo de configuración
        # 🔥 USAR RUTA ABSOLUTA
        config_file = os.path.join(BASE_DIR, 'timestamp_roi_config.json')
        with open(config_file, 'w') as f:
            json.dump(roi_config, f)
        # Log físico del guardado de ROI
        logger.info(f"live_analysis | ROI guardado: {roi_config}")
        
        return jsonify({
            'success': True,
            'message': 'Configuración ROI guardada',
            'roi': roi_config
        })
    
    except Exception as e:
        logger.error(f"Error al guardar configuración ROI: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/roi/get', methods=['GET'])
def get_roi_config():
    """Obtiene la configuración del ROI guardada"""
    try:
        # 🔥 USAR RUTA ABSOLUTA
        config_file = os.path.join(BASE_DIR, 'timestamp_roi_config.json')
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                roi_config = json.load(f)
            return jsonify({
                'success': True,
                'roi': roi_config,
                'configured': True
            })
        else:
            return jsonify({
                'success': True,
                'roi': None,
                'configured': False
            })
    
    except Exception as e:
        logger.error(f"Error al obtener configuración ROI: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/roi/test', methods=['POST'])
def test_roi_config():
    """Prueba la configuración del ROI extrayendo timestamp de un video de muestra"""
    try:
        # Obtener archivo de video
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No se proporcionó archivo de video'}), 400
        
        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({'success': False, 'error': 'Archivo vacío'}), 400
        
        # Obtener coordenadas ROI (pueden venir del form o usar las guardadas)
        roi_data = request.form.get('roi')
        if roi_data:
            roi_config = json.loads(roi_data)
        else:
            # Usar configuración guardada
            # 🔥 USAR RUTA ABSOLUTA
            config_file = os.path.join(BASE_DIR, 'timestamp_roi_config.json')
            if not os.path.exists(config_file):
                return jsonify({
                    'success': False, 
                    'error': 'No hay configuración ROI guardada. Por favor configura primero la zona de hora.'
                }), 400
            
            with open(config_file, 'r') as f:
                roi_config = json.load(f)
        
        # Guardar video temporalmente
        upload_folder = app.config['UPLOAD_FOLDER']
        temp_dir = os.path.join(upload_folder, 'temp_roi_test')
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_video_path = os.path.join(temp_dir, 'test_' + secure_filename(video_file.filename))
        video_file.save(temp_video_path)
        
        try:
            # Extraer timestamp del primer frame con el ROI configurado
            timestamp = video_processing.extract_timestamp_from_video_at_ms(
                temp_video_path, 
                0,  # Frame inicial
                roi_override=(roi_config['x'], roi_config['y'], roi_config['w'], roi_config['h'])
            )
            
            if timestamp:
                return jsonify({
                    'success': True,
                    'timestamp': timestamp,
                    'roi': roi_config,
                    'message': f'✅ Timestamp detectado: {timestamp}'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'No se pudo extraer el timestamp con la configuración actual. Verifica que la zona seleccionada contenga la hora del video.',
                    'roi': roi_config
                })
        
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_video_path):
                try:
                    os.remove(temp_video_path)
                except:
                    pass
            
            # Limpiar directorio temporal si está vacío
            try:
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except:
                pass
    
    except Exception as e:
        logger.error(f"Error al probar configuración ROI: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Obtiene estadísticas generales de la sesión actual"""
    try:
        session_db_path = get_session_db()
        if not session_db_path:
            # Sin sesión activa, retornar stats en 0
            return jsonify({
                'success': True,
                'total_folders': 0,
                'total_videos': 0,
                'total_clips': 0,
                'total_motion_events': 0
            })
        
        conn = db.create_db_connection(session_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM carpetas")
        total_folders = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM videos")
        total_videos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clips")
        total_clips = cursor.fetchone()[0]
        
        # Estadísticas por objeto
        cursor.execute("""
            SELECT objeto_detectado, COUNT(*) as count
            FROM clips
            WHERE objeto_detectado IS NOT NULL
            GROUP BY objeto_detectado
            ORDER BY count DESC
        """)
        objects_stats = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_folders': total_folders,
                'total_videos': total_videos,
                'total_clips': total_clips,
                'objects': [{'type': obj[0], 'count': obj[1]} for obj in objects_stats]
            }
        })
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Obtiene los logs de la sesión actual"""
    try:
        max_lines = request.args.get('max_lines', 500, type=int)
        log_level = request.args.get('level', 'all').upper()
        
        log_file = app.config.get('LOG_FILE')
        session_id = app.config.get('SESSION_ID', 'unknown')
        
        if not log_file or not os.path.exists(log_file):
            return jsonify({
                'success': True,
                'logs': [],
                'session_id': session_id,
                'message': 'No hay archivo de logs disponible'
            })
        
        logs = []
        
        # Leer todas las líneas del archivo de log de la sesión
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Tomar las últimas max_lines líneas
        recent_lines = lines[-max_lines:] if len(lines) > max_lines else lines
        
        # Parsear cada línea con el nuevo formato
        # Formato: 2025-10-21 12:34:56.789 | INFO     | function_name        | mensaje
        for line in recent_lines:
            line = line.strip()
            if not line or line.startswith('='):
                continue
            
            try:
                # Dividir por pipes |
                if '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 4:
                        timestamp = parts[0]
                        level = parts[1].strip()
                        function = parts[2].strip()
                        message = parts[3]
                        
                        # Filtrar por nivel si se especifica
                        if log_level != 'ALL' and level != log_level:
                            continue
                        
                        logs.append({
                            'timestamp': timestamp,
                            'level': level,
                            'function': function,
                            'message': message
                        })
                    else:
                        # Línea con formato incompleto
                        logs.append({
                            'timestamp': '',
                            'level': 'INFO',
                            'function': '',
                            'message': line
                        })
                else:
                    # Línea sin pipes (puede ser mensaje multilínea)
                    logs.append({
                        'timestamp': '',
                        'level': 'INFO',
                        'function': '',
                        'message': line
                    })
            except Exception as e:
                # Si hay error parseando, agregar línea completa
                logs.append({
                    'timestamp': '',
                    'level': 'INFO',
                    'function': '',
                    'message': line
                })
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total': len(logs),
            'session_id': session_id,
            'log_file': os.path.basename(log_file)
        })
        
    except Exception as e:
        logger.error(f"Error al leer logs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logs/download', methods=['GET'])
def download_logs():
    """Descarga el archivo de logs de la sesión actual"""
    try:
        log_file = app.config.get('LOG_FILE')
        
        if not log_file or not os.path.exists(log_file):
            return jsonify({'success': False, 'error': 'No hay logs disponibles'}), 404
        
        log_folder = os.path.dirname(log_file)
        filename = os.path.basename(log_file)
        
        return send_from_directory(log_folder, filename, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Error al descargar logs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logs/clear', methods=['POST'])
def clear_logs():
    """Limpia el archivo de logs de la sesión actual"""
    try:
        log_file = app.config.get('LOG_FILE')
        
        if not log_file:
            return jsonify({'success': False, 'error': 'No hay archivo de logs configurado'}), 404
        
        if os.path.exists(log_file):
            # Limpiar el archivo (no eliminar, solo vaciar)
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write('')
            
            logger.info("🗑️ Logs limpiados por solicitud del usuario")
            
            return jsonify({
                'success': True,
                'message': 'Logs eliminados correctamente'
            })
        else:
            return jsonify({
                'success': True,
                'message': 'No había logs para eliminar'
            })
        
    except Exception as e:
        logger.error(f"Error al limpiar logs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/system/status', methods=['GET'])
def get_system_status():
    """Obtiene el estado de las dependencias del sistema"""
    try:
        dependencies = app.config.get('DEPENDENCIES_STATUS', {})
        
        return jsonify({
            'success': True,
            'session_id': processing_status.get('session_id'),
            'dependencies': dependencies
        })
        
    except Exception as e:
        logger.error(f"Error al obtener estado del sistema: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session/cleanup', methods=['POST'])
def cleanup_session():
    """Elimina todos los datos de la sesión actual (archivos, clips, BD)"""
    global processing_status, active_sessions
    
    try:
        logger.info("🧹 Solicitud de limpieza de sesión recibida")
        
        # Obtener session_id del body o usar el actual
        data = request.get_json(silent=True) or {}
        session_id = data.get('session_id') or processing_status.get('session_id')
        
        if not session_id:
            logger.warning("⚠️ No hay sesión activa para limpiar")
            return jsonify({'success': True, 'message': 'No hay sesión activa'})
        
        logger.info(f"🗑️ Limpiando sesión: {session_id}")
        
        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        
        if os.path.exists(session_folder):
            import shutil
            try:
                # Intentar eliminar toda la carpeta primero
                shutil.rmtree(session_folder)
                logger.info(f"   ✓ Carpeta eliminada: {session_folder}")
            except Exception as e:
                logger.warning(f"   ⚠️ No se pudo eliminar carpeta completa ({e}), intentando eliminar archivos individualmente...")
                # Si falla, intentar eliminar archivos uno por uno
                try:
                    for root, dirs, files in os.walk(session_folder, topdown=False):
                        for file in files:
                            try:
                                os.remove(os.path.join(root, file))
                            except:
                                pass
                        for dir_name in dirs:
                            try:
                                os.rmdir(os.path.join(root, dir_name))
                            except:
                                pass
                    # Intentar eliminar la carpeta raíz
                    try:
                        os.rmdir(session_folder)
                        logger.info(f"   ✓ Carpeta raíz eliminada: {session_folder}")
                    except:
                        logger.warning(f"   ⚠️ No se pudo eliminar completamente: {session_folder}")
                        
                except:
                    logger.warning(f"   ❌ Error al limpiar parcialmente {session_folder}")
        # Limpiar previews de temp (archivos relacionados con esta sesión)
        temp_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
        if os.path.exists(temp_folder):
            try:
                # Buscar y eliminar previews de videos de esta sesión
                for filename in os.listdir(temp_folder):
                    file_path = os.path.join(temp_folder, filename)
                    try:
                        os.remove(file_path)
                        logger.info(f"   ✓ Preview eliminado: {filename}")
                    except Exception as e:
                        logger.warning(f"   ⚠️ No se pudo eliminar preview {filename}: {e}")
            except Exception as e:
                logger.warning(f"   ⚠️ Error al limpiar temp: {e}")
        
        # Limpiar de active_sessions
        if session_id in active_sessions:
            del active_sessions[session_id]
            logger.info(f"   ✓ Sesión eliminada de active_sessions")
        
        # Resetear processing_status
        processing_status['session_id'] = None
        processing_status['session_db_path'] = None
        processing_status['is_processing'] = False
        processing_status['progress'] = 0
        processing_status['total_videos'] = 0
        processing_status['current_video'] = ''
        processing_status['status_message'] = ''
        processing_status['motion_events_detected'] = 0
        processing_status['clips_generated'] = 0
        processing_status['objects_detected'] = 0
        processing_status['just_completed'] = False
        processing_status['completed_tasks'] = []  # Limpiar historial de tareas completadas
        
        logger.info("✅ Sesión limpiada completamente")
        
        return jsonify({
            'success': True,
            'message': 'Sesión eliminada exitosamente'
        })
        
    except Exception as e:
        logger.error(f"Error al limpiar sesión: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/excel/list', methods=['GET'])
def list_excel_files():
    """Lista el archivo Excel de sesión actual"""
    try:
        session_db_path = get_session_db()
        if not session_db_path:
            return jsonify({'success': False, 'error': 'No hay sesión activa'}), 404

        # Obtener información de la sesión
        session_id = processing_status.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'error': 'No hay sesión activa'}), 404

        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        excel_file = os.path.join(session_folder, 'session_data.xlsx')

        if excel_file and os.path.exists(excel_file):
            file_size = os.path.getsize(excel_file)
            modified_time = os.path.getmtime(excel_file)

            excel_info = {
                'filename': 'session_data.xlsx',
                'path': excel_file,
                'size': file_size,
                'modified': datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S'),
                'relative_path': '/api/excel/download',
                'session_id': session_id,
                'description': 'Datos de Sesión Excel'
            }

            return jsonify({
                'success': True,
                'excel_files': [excel_info]
            })
        else:
            return jsonify({
                'success': True,
                'excel_files': [],
                'message': 'No hay Excel de sesión generado aún. Procesa algunos videos primero.'
            })

    except Exception as e:
        logger.error(f"Error al listar archivos Excel: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/excel/data', methods=['GET'])
def get_excel_data():
    """Obtiene los datos del archivo Excel de sesión"""
    try:
        session_db_path = get_session_db()
        if not session_db_path:
            return jsonify({'success': False, 'error': 'No hay sesión activa'}), 404

        # Obtener información de la sesión
        session_id = processing_status.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'error': 'No hay sesión activa'}), 404

        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        excel_file = os.path.join(session_folder, 'session_data.xlsx')

        if not excel_file or not os.path.exists(excel_file):
            return jsonify({'success': False, 'error': 'Archivo Excel de sesión no encontrado. Genera el análisis primero.'}), 404

        # Leer el Excel y convertir a formato JSON
        excel_data = {}
        
        # Usar context manager para asegurar que el archivo se cierre
        with pd.ExcelFile(excel_file) as xls:
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)

                # Convertir DataFrame a lista de listas (con headers)
                headers = df.columns.tolist()
                rows = df.values.tolist()

                # Convertir tipos de datos para JSON
                json_rows = []
                for row in rows:
                    json_row = []
                    for cell in row:
                        if pd.isna(cell):
                            json_row.append('')
                        elif isinstance(cell, (int, float)):
                            json_row.append(cell)
                        else:
                            json_row.append(str(cell))
                    json_rows.append(json_row)

                excel_data[sheet_name] = {
                    'headers': headers,
                    'rows': json_rows
                }

        return jsonify({
            'success': True,
            'filename': 'session_data.xlsx',
            'data': excel_data
        })

    except Exception as e:
        logger.error(f"Error al leer datos del Excel de sesión: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/excel/download', methods=['GET'])
def download_excel_file():
    """Descarga el archivo Excel de sesión"""
    try:
        session_db_path = get_session_db()
        if not session_db_path:
            return jsonify({'success': False, 'error': 'No hay sesión activa'}), 404

        # Obtener información de la sesión
        session_id = processing_status.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'error': 'No hay sesión activa'}), 404

        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        excel_file = os.path.join(session_folder, 'session_data.xlsx')

        if not excel_file or not os.path.exists(excel_file):
            return jsonify({'success': False, 'error': 'Archivo Excel de sesión no encontrado'}), 404

        # Enviar el archivo
        return send_file(excel_file, as_attachment=True, download_name='session_data.xlsx')

    except Exception as e:
        logger.error(f"Error al descargar Excel de sesión: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Nuevo endpoint para guardar el ROI de análisis en directo
@app.route('/api/config/roi/live', methods=['POST'])
def save_live_roi_config():
    """Guarda la configuración del ROI para análisis en directo"""
    try:
        data = request.json
        roi_config = {
            'x': data.get('x', 0),
            'y': data.get('y', 0),
            'w': data.get('w', 200),
            'h': data.get('h', 80)
        }
        # Guardar en archivo específico para directo
        config_file = os.path.join(os.path.dirname(__file__), '..', 'live_roi_config.json')
        with open(config_file, 'w') as f:
            json.dump(roi_config, f)
        # Log físico del guardado de ROI directo
        logger.info(f"live_analysis | ROI DIRECTO guardado: {roi_config}")
        return jsonify({
            'success': True,
            'message': 'Configuración ROI de directo guardada',
            'roi': roi_config
        })
    except Exception as e:
        logger.error(f"Error al guardar configuración ROI directo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/api/excel/save', methods=['POST'])
def save_excel_data():
    """Guarda cambios en el archivo Excel de sesión"""
    try:
        data = request.json
        if not data or 'sheet_data' not in data:
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400

        session_db_path = get_session_db()
        if not session_db_path:
            return jsonify({'success': False, 'error': 'No hay sesión activa'}), 404

        # Obtener información de la sesión
        session_id = processing_status.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'error': 'No hay sesión activa'}), 404

        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        excel_file = os.path.join(session_folder, 'session_data.xlsx')

        if not excel_file or not os.path.exists(excel_file):
            return jsonify({'success': False, 'error': 'Archivo Excel de sesión no encontrado'}), 404

        # Leer el Excel existente y actualizar con los nuevos datos
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            for sheet_name, sheet_info in data['sheet_data'].items():
                headers = sheet_info.get('headers', [])
                rows = sheet_info.get('rows', [])

                # Crear DataFrame
                if rows:
                    df = pd.DataFrame(rows, columns=headers)
                else:
                    df = pd.DataFrame(columns=headers)

                # Guardar la hoja
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        logger.info(f"✅ Excel de sesión actualizado: {excel_file}")

        return jsonify({
            'success': True,
            'message': 'Excel de sesión guardado correctamente'
        })

    except Exception as e:
        logger.error(f"Error al guardar Excel de sesión: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def cleanup_all_on_exit():
    """Limpia solo logs antiguos al cerrar - MANTIENE base de datos y uploads intactos"""
    logger.info("="*80)
    logger.info("🛑 Cerrando servidor - Limpiando solo logs antiguos...")
    
    # Solo limpiar logs antiguos (mantener últimos 10)
    try:
        log_files = [f for f in os.listdir(log_folder) if f.startswith('session_') and f.endswith('.log')]
        if len(log_files) > 10:
            log_paths = [os.path.join(log_folder, f) for f in log_files]
            log_paths.sort(key=os.path.getmtime, reverse=True)
            files_to_delete = log_paths[10:]  # Mantener solo los 10 más recientes
            
            deleted = 0
            for old_log in files_to_delete:
                try:
                    os.remove(old_log)
                    deleted += 1
                except:
                    pass
            
            if deleted > 0:
                logger.info(f"🧹 Logs antiguos eliminados: {deleted}")
    except Exception as e:
        logger.debug(f"Error al limpiar logs: {e}")
    
    # ✅ YA NO BORRAMOS uploads ni base de datos - se mantienen para historial
    logger.info("💾 Base de datos y archivos mantenidos para próxima sesión")
    logger.info("👋 Servidor cerrado correctamente")
    logger.info("="*80)

if __name__ == '__main__':
    # Registrar función de limpieza para cuando se cierre el servidor
    import atexit
    atexit.register(cleanup_all_on_exit)
    
    # Limpiar sesiones antiguas al iniciar
    cleanup_old_sessions()
    
    print("🚀 Iniciando servidor Flask...")
    print("📍 Accede a la aplicación en: http://localhost:5000")
    print("⚠️  Presiona Ctrl+C para detener el servidor")
    print("� Los datos se mantienen entre sesiones (historial persistente)")
    print("-" * 60)
    
    try:
        # Siempre modo producción sin debug ni reloader (evita logs duplicados)
        # use_reloader=False es CRÍTICO para evitar que Flask inicie 2 procesos
        app.run(debug=False, host='0.0.0.0', port=5000, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido por el usuario")
    finally:
        # La limpieza se ejecuta automáticamente por atexit
        pass


