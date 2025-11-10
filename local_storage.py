"""
Gestor de almacenamiento local para la aplicación de escritorio
Sin sesiones temporales - todo es permanente
"""
import os
import json
import sqlite3
from datetime import datetime

# Cargar configuración
CONFIG_FILE = 'config_local.json'

def load_config():
    """Carga la configuración local"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Configuración por defecto
    return {
        'app_mode': 'local',
        'data_folder': 'datos_aplicacion',
        'videos_folder': 'videos',
        'database_name': 'detector_movimiento.db',
        'loose_videos_folder': 'Videos Sueltos',
        'auto_create_folders': True
    }

class LocalStorage:
    """Gestiona el almacenamiento local permanente"""
    
    def __init__(self, base_dir=None):
        self.config = load_config()
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        
        # Rutas principales
        self.data_folder = os.path.join(self.base_dir, self.config['data_folder'])
        self.videos_folder = os.path.join(self.data_folder, self.config['videos_folder'])
        self.db_path = os.path.join(self.data_folder, self.config['database_name'])
        self.loose_videos_folder = os.path.join(
            self.videos_folder, 
            self.config['loose_videos_folder']
        )
        
        # Crear estructura de carpetas
        if self.config['auto_create_folders']:
            self._create_folders()
            self._init_database()
    
    def _create_folders(self):
        """Crea la estructura de carpetas si no existe"""
        os.makedirs(self.data_folder, exist_ok=True)
        os.makedirs(self.videos_folder, exist_ok=True)
        os.makedirs(self.loose_videos_folder, exist_ok=True)
        os.makedirs(os.path.join(self.data_folder, 'logs'), exist_ok=True)
        os.makedirs(os.path.join(self.data_folder, 'temp'), exist_ok=True)
    
    def _init_database(self):
        """Inicializa la base de datos si no existe"""
        if not os.path.exists(self.db_path):
            import db
            conn = sqlite3.connect(self.db_path)
            db.create_tables(conn)
            conn.close()
    
    def get_all_folders(self):
        """Obtiene todas las carpetas de videos"""
        folders = []
        
        if os.path.exists(self.videos_folder):
            for item in os.listdir(self.videos_folder):
                folder_path = os.path.join(self.videos_folder, item)
                if os.path.isdir(folder_path):
                    # Contar videos en la carpeta
                    video_count = len([
                        f for f in os.listdir(folder_path) 
                        if f.lower().endswith(('.mp4', '.avi', '.mov', '.dav', '.mkv'))
                    ])
                    
                    # Contar clips
                    clips_folder = os.path.join(folder_path, 'clips_analisis')
                    clip_count = 0
                    if os.path.exists(clips_folder):
                        clip_count = len([
                            f for f in os.listdir(clips_folder)
                            if f.lower().endswith('.mp4')
                        ])
                    
                    folders.append({
                        'name': item,
                        'path': folder_path,
                        'video_count': video_count,
                        'clip_count': clip_count,
                        'is_loose': item == self.config['loose_videos_folder']
                    })
        
        return folders
    
    def add_folder_reference(self, folder_path):
        """
        Agrega una referencia a una carpeta externa del sistema
        No copia los archivos, solo registra la ubicación
        """
        folder_name = os.path.basename(folder_path)
        
        # Verificar que la carpeta existe
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"La carpeta no existe: {folder_path}")
        
        # Crear enlace simbólico o registrar en BD
        link_path = os.path.join(self.videos_folder, folder_name)
        
        # Si ya existe, agregar sufijo numérico
        counter = 1
        original_name = folder_name
        while os.path.exists(link_path):
            folder_name = f"{original_name}_{counter}"
            link_path = os.path.join(self.videos_folder, folder_name)
            counter += 1
        
        try:
            # Intentar crear enlace simbólico (requiere permisos admin en Windows)
            os.symlink(folder_path, link_path, target_is_directory=True)
        except (OSError, NotImplementedError):
            # Si falla, copiar referencia a un archivo de texto
            with open(link_path + '.link', 'w', encoding='utf-8') as f:
                json.dump({
                    'type': 'folder_reference',
                    'original_path': folder_path,
                    'created': datetime.now().isoformat()
                }, f, indent=2)
        
        return folder_name, link_path
    
    def copy_files_to_loose(self, file_paths):
        """Copia archivos individuales a la carpeta 'Videos Sueltos'"""
        copied = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                continue
            
            filename = os.path.basename(file_path)
            dest_path = os.path.join(self.loose_videos_folder, filename)
            
            # Si ya existe, agregar timestamp
            if os.path.exists(dest_path):
                name, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{name}_{timestamp}{ext}"
                dest_path = os.path.join(self.loose_videos_folder, filename)
            
            # Copiar archivo
            import shutil
            shutil.copy2(file_path, dest_path)
            copied.append(dest_path)
        
        return copied
    
    def get_database_connection(self):
        """Obtiene una conexión a la base de datos"""
        return sqlite3.connect(self.db_path)


# Instancia global
_storage = None

def get_storage():
    """Obtiene la instancia global de LocalStorage"""
    global _storage
    if _storage is None:
        _storage = LocalStorage()
    return _storage
