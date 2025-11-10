import sqlite3

conn = sqlite3.connect('C:/Users/pabli/Desktop/web_app/data_local/detector_movimiento.db')
cursor = conn.cursor()

# Ver SQL de creación
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='videos'")
result = cursor.fetchone()

print("SQL de creación:")
print(result[0] if result else 'No existe')
print("\n" + "="*80 + "\n")

# Ver columnas
cursor.execute("PRAGMA table_info(videos)")
print("Columnas:")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

conn.close()
