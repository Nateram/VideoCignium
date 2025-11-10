# db.py

import sqlite3
from datetime import datetime
import threading
import os
import sys
import tempfile
import logging

# ====================================================================
# 🔥 DEFINIR RUTA BASE DEL PROYECTO
# ====================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Crear un bloqueo global para operaciones de base de datos
db_lock = threading.Lock()

# Variable global para almacenar la ruta de la BD usada actualmente
_CURRENT_DB_PATH = None

# Logger simple que usa la configuración del módulo principal
logger = logging.getLogger(__name__)

def get_db_path():
    """Devuelve la ruta actual de la base de datos"""
    global _CURRENT_DB_PATH
    return _CURRENT_DB_PATH

def get_app_path():
    """
    Devuelve la ruta base de la aplicación.
    En Windows usa %APPDATA%\\DetectorMovimiento
    En Docker/Linux usa /app/data
    """
    # Detectar si estamos en Docker (Linux) o Windows
    if os.name == 'posix':  # Linux/Docker
        app_data_dir = "/app/data"
        logger.info(f"Usando directorio de datos en Docker: {app_data_dir}")
    else:  # Windows
        app_data_dir = os.path.join(os.environ['APPDATA'], "DetectorMovimiento")
        logger.info(f"Usando directorio de datos en AppData: {app_data_dir}")

    os.makedirs(app_data_dir, exist_ok=True)
    return app_data_dir

def create_db_connection(db_path=None):
    """
    Crea y devuelve una conexión a la base de datos SQLite.
    
    Args:
        db_path: Ruta específica de la BD. Si es None, usa BD por sesión temporal.
    """
    global _CURRENT_DB_PATH
    
    try:
        # Si no se especifica ruta, usar BD temporal por sesión
        if db_path is None:
            # Detectar si estamos en Docker (Linux) o Windows
            if os.name == 'posix':  # Linux/Docker
                app_data_dir = "/app/data"
            else:  # Windows
                app_data_dir = os.path.join(os.environ['APPDATA'], "DetectorMovimiento")

            db_path = os.path.join(app_data_dir, "video_analisis.db")
            os.makedirs(app_data_dir, exist_ok=True)
        else:
            # Usar la ruta específica proporcionada (para sesiones temporales)
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
        
        _CURRENT_DB_PATH = db_path
        
        # Verificar permisos de escritura
        try:
            with open(db_path, 'a'):
                pass
        except PermissionError:
            logger.error(f"Sin permisos de escritura en {db_path}")
            raise Exception(f"No se pueden obtener permisos de escritura en {db_path}")
        
        return sqlite3.connect(db_path)
        
    except Exception as e:
        logger.critical(f"Error al conectar a la base de datos: {e}")
        raise Exception(f"No se pudo crear la conexión a la base de datos: {e}")

def create_tables(db_path=None):
    """
    Crea las tablas de la base de datos si no existen.
    
    Args:
        db_path: Ruta específica de la BD. Si es None, usa BD por defecto.
    """
    conn = create_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS carpetas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ruta TEXT NOT NULL UNIQUE,
            fecha_subida TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            carpeta_id INTEGER NOT NULL,
            nombre_archivo TEXT NOT NULL,
            ruta_absoluta TEXT NOT NULL UNIQUE,
            fecha_creacion TEXT NOT NULL,
            roi_x INTEGER,
            roi_y INTEGER,
            roi_w INTEGER,
            roi_h INTEGER,
            FOREIGN KEY (carpeta_id) REFERENCES carpetas (id)
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL,
            nombre_archivo TEXT NOT NULL,
            ruta_absoluta TEXT,
            tiempo_evento_ms INTEGER NOT NULL,
            fecha_evento TEXT NOT NULL,
            objeto_detectado TEXT,
            color_detectado TEXT,
            FOREIGN KEY (video_id) REFERENCES videos (id)
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion_deteccion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            threshold_percentage REAL NOT NULL DEFAULT 1.0,
            var_threshold INTEGER NOT NULL DEFAULT 16,
            cooldown_ms INTEGER NOT NULL DEFAULT 2000,
            fecha_actualizacion TEXT NOT NULL,
            activa INTEGER NOT NULL DEFAULT 1
        );
    """)
    conn.commit()
    conn.close()

def insert_folder(conn, folder_path):
    """
    Inserta una carpeta en la base de datos o devuelve su ID si ya existe.
    """
    cursor = conn.cursor()
    fecha_subida = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("INSERT INTO carpetas (ruta, fecha_subida) VALUES (?, ?)", (folder_path, fecha_subida))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        cursor.execute("SELECT id FROM carpetas WHERE ruta = ?", (folder_path,))
        return cursor.fetchone()[0]

def insert_video(conn, carpeta_id, video_file, video_path, creation_date, roi_coords=None):
    """
    Inserta un video en la base de datos o devuelve su ID si ya existe.
    """
    with db_lock:  # Agregar bloqueo también para videos
        cursor = conn.cursor()
        roi_x, roi_y, roi_w, roi_h = roi_coords if roi_coords else (None, None, None, None)
        try:
            cursor.execute(
                "INSERT INTO videos (carpeta_id, nombre_archivo, ruta_absoluta, fecha_creacion, roi_x, roi_y, roi_w, roi_h) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (carpeta_id, video_file, video_path, creation_date, roi_x, roi_y, roi_w, roi_h)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            cursor.execute("SELECT id FROM videos WHERE ruta_absoluta = ?", (video_path,))
            return cursor.fetchone()[0]

def insert_clip(conn, video_id, clip_filename, clip_path, event_ms, fecha_evento, object_type, object_color):
    """
    Inserta un clip en la base de datos, permitiendo fecha_evento None.
    Soporta modo sin clips (clip_path=None para eventos de movimiento sin archivo MP4).
    Maneja mejor los errores de integridad para evitar problemas en procesamiento paralelo.
    """
    with db_lock:  # Usar bloqueo para evitar conflictos de concurrencia
        cursor = conn.cursor()
        try:
            # Verificar que el video_id existe - con más información de depuración
            cursor.execute("SELECT id FROM videos WHERE id = ?", (video_id,))
            video_result = cursor.fetchone()
            if not video_result:
                logger.error(f"Error: Se intentó insertar un clip para un video_id inexistente: {video_id}")
                # Buscar todos los videos para ayudar en la depuración
                cursor.execute("SELECT id, nombre_archivo FROM videos")
                videos = cursor.fetchall()
                logger.debug(f"Videos disponibles en la BD: {videos}")
                return None
            
            # Si la fecha está vacía o es None, usar un valor predeterminado
            if not fecha_evento:
                fecha_evento = "Fecha inválida"
                logger.warning(f"Usando fecha predeterminada 'Fecha inválida' para el clip {clip_filename}")
                
            try:
                cursor.execute(
                    "INSERT INTO clips (video_id, nombre_archivo, ruta_absoluta, tiempo_evento_ms, fecha_evento, objeto_detectado, color_detectado) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (video_id, clip_filename, clip_path, event_ms, fecha_evento, object_type, object_color)
                )
                conn.commit()
                
                # Log diferenciado según si hay clip o solo evento
                if clip_path:
                    logger.info(f"Clip insertado: {clip_filename} para video_id {video_id}")
                else:
                    logger.info(f"Evento insertado (sin clip): {clip_filename} para video_id {video_id}")
                
                return cursor.lastrowid
            except sqlite3.IntegrityError as ie:
                # Mejorar mensaje de error para clarificar el problema
                error_msg = str(ie)
                if "NOT NULL constraint failed: clips.ruta_absoluta" in error_msg:
                    logger.error(f"❌ ERROR: La base de datos requiere actualización. La tabla 'clips' necesita permitir NULL en ruta_absoluta.")
                    logger.error(f"   Solución: Eliminar sesión actual y crear una nueva (la nueva BD ya tiene el fix).")
                    logger.error(f"   O ejecutar: ALTER TABLE clips MODIFY COLUMN ruta_absoluta TEXT NULL;")
                else:
                    logger.error(f"Error de integridad al insertar clip {clip_filename}: {ie}")
                
                # Verificar si el clip ya existe (solo si tiene ruta)
                if clip_path:
                    cursor.execute("SELECT id, video_id FROM clips WHERE ruta_absoluta = ?", (clip_path,))
                    existing = cursor.fetchone()
                    if existing:
                        existing_id, existing_video_id = existing
                        # Si el clip existe pero con un video_id diferente, loguear advertencia
                        if existing_video_id != video_id:
                            logger.warning(f"El clip {clip_path} ya existe pero está asociado al video_id {existing_video_id} en lugar de {video_id}")
                        return existing_id
                return None
        except Exception as e:
            logger.error(f"Error al insertar clip {clip_filename}: {e}")
            logger.error(f"Detalles: video_id={video_id}, clip_path={clip_path}, db_path={_CURRENT_DB_PATH}")
            # Imprimir la traza de la excepción para depuración
            import traceback
            logger.error(f"Traza: {traceback.format_exc()}")
            return None

def save_motion_detection_config(threshold_percentage, var_threshold, cooldown_ms):
    """
    Guarda la configuración de detección de movimiento en la base de datos.
    """
    with db_lock:
        try:
            conn = create_db_connection()
            cursor = conn.cursor()
            fecha_actualizacion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Marcar todas las configuraciones anteriores como inactivas
            cursor.execute("UPDATE configuracion_deteccion SET activa = 0")
            
            # Insertar nueva configuración activa
            cursor.execute(
                "INSERT INTO configuracion_deteccion (threshold_percentage, var_threshold, cooldown_ms, fecha_actualizacion, activa) VALUES (?, ?, ?, ?, 1)",
                (threshold_percentage, var_threshold, cooldown_ms, fecha_actualizacion)
            )
            
            conn.commit()
            conn.close()
            logger.info(f"Configuración guardada: threshold_percentage={threshold_percentage}, var_threshold={var_threshold}, cooldown_ms={cooldown_ms}")
            return True
        except Exception as e:
            logger.error(f"Error al guardar configuración: {e}")
            return False

def load_motion_detection_config():
    """
    Carga la configuración de detección de movimiento desde la base de datos.
    Si no existe configuración, devuelve valores por defecto.
    """
    try:
        conn = create_db_connection()
        cursor = conn.cursor()
        
        # Buscar la configuración activa más reciente
        cursor.execute(
            "SELECT threshold_percentage, var_threshold, cooldown_ms FROM configuracion_deteccion WHERE activa = 1 ORDER BY id DESC LIMIT 1"
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            threshold_percentage, var_threshold, cooldown_ms = result
            logger.info(f"Configuración cargada desde BD: threshold_percentage={threshold_percentage}, var_threshold={var_threshold}, cooldown_ms={cooldown_ms}")
            return {
                'threshold_percentage': float(threshold_percentage),
                'var_threshold': int(var_threshold),
                'cooldown_ms': int(cooldown_ms),
                'gaussian_blur': (5, 5),              # Siempre incluir parámetros técnicos
                'morph_kernel_size': (3, 3),          # Siempre incluir parámetros técnicos
                'binary_threshold': 127                # Siempre incluir parámetros técnicos
            }
        else:
            logger.info("No se encontró configuración en BD, usando valores por defecto")
            return None
    except Exception as e:
        logger.error(f"Error al cargar configuración: {e}")
        return None

def update_clip_classification(clip_id, new_object_type, new_color=None):
    """
    Actualiza la clasificación de un clip específico.
    Permite corregir errores de detección automática.
    """
    with db_lock:
        try:
            conn = create_db_connection()
            cursor = conn.cursor()
            
            if new_color is not None:
                cursor.execute(
                    "UPDATE clips SET objeto_detectado = ?, color_detectado = ? WHERE id = ?",
                    (new_object_type, new_color, clip_id)
                )
            else:
                cursor.execute(
                    "UPDATE clips SET objeto_detectado = ? WHERE id = ?",
                    (new_object_type, clip_id)
                )
            
            conn.commit()
            conn.close()
            
            if cursor.rowcount > 0:
                logger.info(f"Clasificación actualizada para clip ID {clip_id}: {new_object_type}")
                return True
            else:
                logger.warning(f"No se encontró clip con ID {clip_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error al actualizar clasificación del clip {clip_id}: {e}")
            return False

def get_available_object_types():
    """
    Devuelve las categorías de objetos disponibles para clasificación.
    Enfocado en objetos comunes en videos de cámaras de seguridad.
    Basado en las clases que YOLO puede detectar realmente.
    """
    return [
        "persona",
        "coche", 
        "furgoneta",
        "camión",
        "autobús",
        "moto",
        "bicicleta",
        "otro"
    ]

def get_clips_for_editing():
    """
    Obtiene todos los clips con su información para permitir edición de clasificaciones.
    """
    try:
        conn = create_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                c.id,
                c.nombre_archivo,
                c.fecha_evento,
                c.objeto_detectado,
                c.color_detectado,
                v.nombre_archivo as video_origen
            FROM clips c
            JOIN videos v ON c.video_id = v.id
            ORDER BY c.fecha_evento DESC
        """)
        
        clips = cursor.fetchall()
        conn.close()
        
        return clips
        
    except Exception as e:
        logger.error(f"Error al obtener clips para edición: {e}")
        return []