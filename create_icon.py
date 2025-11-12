"""
Script para generar un icono simple para la aplicación
Requiere: pip install pillow
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    # Crear imagen de 256x256 con fondo azul
    size = 256
    img = Image.new('RGB', (size, size), color='#2196F3')
    draw = ImageDraw.Draw(img)
    
    # Dibujar un círculo blanco
    margin = 30
    draw.ellipse([margin, margin, size-margin, size-margin], fill='white', outline='#1976D2', width=8)
    
    # Dibujar símbolo de cámara/video (rectángulo + círculo)
    cam_x = size // 2 - 40
    cam_y = size // 2 - 30
    cam_w = 80
    cam_h = 60
    
    # Cuerpo de la cámara
    draw.rectangle([cam_x, cam_y, cam_x + cam_w, cam_y + cam_h], fill='#2196F3', outline='#1976D2', width=4)
    
    # Lente (círculo en el centro)
    lens_x = cam_x + cam_w // 2
    lens_y = cam_y + cam_h // 2
    lens_r = 18
    draw.ellipse([lens_x - lens_r, lens_y - lens_r, lens_x + lens_r, lens_y + lens_r], 
                 fill='#1976D2', outline='#0D47A1', width=3)
    
    # Indicador de grabación (punto rojo arriba a la derecha)
    rec_x = cam_x + cam_w - 10
    rec_y = cam_y + 10
    draw.ellipse([rec_x - 5, rec_y - 5, rec_x + 5, rec_y + 5], fill='#F44336')
    
    # Guardar como PNG
    png_path = 'electron/icon.png'
    img.save(png_path, 'PNG')
    print(f"✅ PNG creado: {png_path}")
    
    # Convertir a ICO (múltiples tamaños)
    ico_path = 'electron/icon.ico'
    img.save(ico_path, format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
    print(f"✅ ICO creado: {ico_path}")
    
    print("\n✨ Iconos generados correctamente!")
    print(f"   PNG: {os.path.abspath(png_path)}")
    print(f"   ICO: {os.path.abspath(ico_path)}")

if __name__ == '__main__':
    try:
        create_icon()
    except ImportError:
        print("❌ Error: Pillow no está instalado")
        print("   Ejecuta: pip install pillow")
    except Exception as e:
        print(f"❌ Error al crear icono: {e}")
