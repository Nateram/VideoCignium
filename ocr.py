import cv2
import random
import easyocr
from PIL import Image
import logging
logger = logging.getLogger("OCR")

# Importaciones de tkinter solo cuando se ejecuta como aplicación independiente
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    from PIL import ImageTk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    # No imprimir nada aquí para evitar problemas de codificación
    pass

# Definimos las dimensiones para mostrar la imagen en la ventana
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 600

# Solo definir la clase GUI si tkinter está disponible
if TKINTER_AVAILABLE:
    class VideoOCRApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Extractor de Fechas con Tkinter")
            self.geometry("850x750")

            # --- Variables de estado ---
            self.video_path = None
            self.cap = None
            self.original_frame = None  # Frame original de OpenCV sin redimensionar
            self.display_image = None   # Imagen redimensionada para mostrar en el canvas
            self.scale_factor_x = 1.0
            self.scale_factor_y = 1.0
            self.roi_start_x = None
            self.roi_start_y = None
            self.roi_rect = None

            # --- Cargar el modelo de OCR al inicio ---
            self.status_text = tk.StringVar(value="Cargando modelo OCR... Por favor, espera.")
            self.update() # Forzar actualización de la GUI para mostrar el mensaje
            try:
                self.reader = easyocr.Reader(['en'], gpu=False)
                self.status_text.set("Modelo OCR cargado. Por favor, selecciona un video.")
            except Exception as e:
                messagebox.showerror("Error de OCR", f"No se pudo cargar EasyOCR. Asegúrate de tener conexión a internet la primera vez.\nError: {e}")
                self.destroy()
                return

            # --- Creación de la Interfaz Gráfica (Widgets) ---
            self.create_widgets()

        def create_widgets(self):
            # Frame para los botones
            button_frame = tk.Frame(self)
            button_frame.pack(pady=10)

            # Botones de control
            tk.Button(button_frame, text="Cargar Video", command=self.load_video).pack(side=tk.LEFT, padx=5)
            self.btn_get_frame = tk.Button(button_frame, text="Obtener Frame Aleatorio", command=self.show_random_frame, state=tk.DISABLED)
            self.btn_get_frame.pack(side=tk.LEFT, padx=5)
            self.btn_extract = tk.Button(button_frame, text="Extraer Texto de la Selección", command=self.extract_text, state=tk.DISABLED)
            self.btn_extract.pack(side=tk.LEFT, padx=5)

            # Canvas para mostrar el video
            self.canvas = tk.Canvas(self, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, bg="gray")
            self.canvas.pack(pady=10)

            # Vincular eventos del ratón al canvas para la selección
            self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
            self.canvas.bind("<B1-Motion>", self.on_mouse_drag)

            # Label para mostrar el estado y los resultados
            lbl_status = tk.Label(self, textvariable=self.status_text, font=("Helvetica", 12))
            lbl_status.pack(pady=10)

        def load_video(self):
            """Abre un diálogo para seleccionar un archivo de video."""
            path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mov *.dav")])
            if not path:
                return

            self.video_path = path
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                messagebox.showerror("Error", "No se pudo abrir el archivo de video.")
                self.video_path = None
                return

            self.btn_get_frame.config(state=tk.NORMAL)
            self.status_text.set(f"Video cargado: {self.video_path.split('/')[-1]}")

        def show_random_frame(self):
            """Selecciona un frame aleatorio, lo redimensiona y lo muestra en el canvas."""
            if not self.cap:
                return

            total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames <= 0:
                # Intentar leer el primer frame manualmente para videos .dav
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    messagebox.showwarning("Advertencia", "No se pudo leer ningún frame del video. Puede que el formato .dav no sea compatible o el archivo esté dañado.")
                    self.status_text.set("No se pudo leer ningún frame. Formato .dav puede no ser compatible.")
                    return
                self.status_text.set("Advertencia: No se pudo obtener el número de frames. Mostrando el primer frame.")
            else:
                random_pos = random.randint(0, total_frames - 1)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, random_pos)
                ret, frame = self.cap.read()
                if not ret:
                    messagebox.showwarning("Advertencia", "No se pudo leer el frame. Intenta de nuevo.")
                    return

            self.original_frame = frame.copy()

            # Convertir imagen de OpenCV (BGR) a formato compatible con Tkinter (RGB)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(frame_rgb)

            # Calcular el factor de escala para ajustar la imagen al canvas
            orig_w, orig_h = img_pil.size
            self.scale_factor_x = orig_w / DISPLAY_WIDTH
            self.scale_factor_y = orig_h / DISPLAY_HEIGHT

            # Redimensionar la imagen para mostrarla
            img_pil.thumbnail((DISPLAY_WIDTH, DISPLAY_HEIGHT), Image.Resampling.LANCZOS)
            self.display_image = ImageTk.PhotoImage(image=img_pil)

            # Mostrar la imagen en el canvas
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.display_image)
            self.status_text.set("Frame cargado. Arrastra el ratón sobre la imagen para seleccionar una zona.")
            self.btn_extract.config(state=tk.NORMAL)

        def on_mouse_press(self, event):
            """Inicia la selección del rectángulo (ROI)."""
            self.roi_start_x = event.x
            self.roi_start_y = event.y

            # Eliminar rectángulo anterior si existe
            if self.roi_rect:
                self.canvas.delete(self.roi_rect)

            self.roi_rect = self.canvas.create_rectangle(self.roi_start_x, self.roi_start_y, self.roi_start_x, self.roi_start_y, outline="green", width=2)

        def on_mouse_drag(self, event):
            """Actualiza el tamaño del rectángulo mientras se arrastra el ratón."""
            if not self.roi_rect:
                return

            self.canvas.coords(self.roi_rect, self.roi_start_x, self.roi_start_y, event.x, event.y)

        def extract_text(self):
            """Recorta la zona seleccionada del frame original y extrae el texto."""
            if not self.roi_rect or self.original_frame is None:
                messagebox.showwarning("Advertencia", "Primero debes seleccionar una zona en un frame.")
                return

            # Obtener coordenadas del rectángulo en el canvas
            x1, y1, x2, y2 = self.canvas.coords(self.roi_rect)

            # Convertir coordenadas del canvas a coordenadas del frame original
            orig_x1 = int(min(x1, x2) * self.scale_factor_x)
            orig_y1 = int(min(y1, y2) * self.scale_factor_y)
            orig_x2 = int(max(x1, x2) * self.scale_factor_x)
            orig_y2 = int(max(y1, y2) * self.scale_factor_y)

            if orig_x1 >= orig_x2 or orig_y1 >= orig_y2:
                self.status_text.set("Selección no válida. Inténtalo de nuevo.")
                return

            # Recortar el frame original de OpenCV
            roi = self.original_frame[orig_y1:orig_y2, orig_x1:orig_x2]

            self.status_text.set("Procesando la selección con OCR...")
            self.update() # Forzar actualización del mensaje

            # Realizar OCR
            resultado = self.reader.readtext(roi)

            if not resultado:
                self.status_text.set("Resultado: No se detectó texto en la selección.")
            else:
                texto_extraido = " ".join([res[1] for res in resultado])
                self.status_text.set(f"Texto Extraído: {texto_extraido}")

            # Opcional: Mostrar la imagen recortada en una nueva ventana
            try:
                cv2.imshow("Zona Seleccionada (ROI)", roi)
            except:
                print("No se pudo mostrar la imagen del ROI.")
else:
    # Si no hay tkinter, definir una clase dummy para evitar errores
    class VideoOCRApp:
        def __init__(self):
            raise ImportError("tkinter no está disponible. Esta aplicación requiere una interfaz gráfica.")

def extract_timestamp_from_roi(frame, roi_coords):
    """
    Recorta el ROI del frame y extrae el texto usando EasyOCR.
    """
    try:
        reader = easyocr.Reader(['en'], gpu=False)
        x, y, w, h = roi_coords
        roi = frame[y:y+h, x:x+w]
        resultado = reader.readtext(roi)
        if not resultado:
            return None
        texto_extraido = " ".join([res[1] for res in resultado])
        logger.info(f"Texto extraído de ROI: {texto_extraido}")
        return texto_extraido
    except Exception as e:
        logger.error(f"Error en OCR: {e}")
        return None


# Solo ejecutar la aplicación GUI si se ejecuta directamente y tkinter está disponible
if __name__ == "__main__" and TKINTER_AVAILABLE:
    app = VideoOCRApp()
    app.mainloop()
elif __name__ == "__main__" and not TKINTER_AVAILABLE:
    print("❌ No se puede ejecutar la aplicación GUI: tkinter no está disponible")
    print("💡 Esta aplicación requiere una interfaz gráfica para funcionar")


