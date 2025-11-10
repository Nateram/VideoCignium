import sqlite3
import os

db_path = 'C:/Users/pabli/Desktop/web_app/data_local/detector_movimiento.db'

if os.path.exists(db_path):
    print(f"Eliminando BD antigua: {db_path}")
    try:
        os.remove(db_path)
        print("✅ BD eliminada")
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("La BD no existe")
