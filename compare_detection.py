import sys
import os
import hashlib
import time
import cv2

# Import video_processing from project
import video_processing

# ROI fijo (tomado de la UI: X:323 Y:12 Ancho:217 Alto:171)
DEFAULT_ROI = (323, 12, 217, 171)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def file_info(path):
    info = {}
    info['exists'] = os.path.exists(path)
    info['size_bytes'] = os.path.getsize(path) if info['exists'] else 0
    cap = cv2.VideoCapture(path)
    info['cap_opened'] = cap.isOpened()
    if cap.isOpened():
        info['frames'] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        info['fps'] = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        info['duration_s'] = (info['frames'] / info['fps']) if info['fps'] > 0 else None
    else:
        info['frames'] = 0
        info['fps'] = 0.0
        info['duration_s'] = None
    try:
        cap.release()
    except:
        pass
    return info


def run_detection(path, roi=None):
    # Use advanced version to ensure consistent config
    config = video_processing.get_motion_detection_config()
    print(f"Using motion config: {config}")
    start = time.time()
    events = video_processing.process_video_for_motion_advanced(path, tuple(roi) if roi else None, config)
    elapsed = time.time() - start
    return events, elapsed


def select_roi_from_video(video_path):
    """
    Muestra el primer frame del video y permite seleccionar un ROI usando OpenCV GUI.
    Devuelve una tupla (x, y, w, h) o None si el usuario cancela.
    """
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"No se pudo abrir el video para seleccionar ROI: {video_path}")
            return None

        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            print("No se pudo leer el primer frame para seleccionar ROI")
            return None

        print("Se abrirá una ventana para seleccionar el ROI. Usa el mouse para dibujar el rectángulo y presiona Enter o Space para confirmar. Presiona Esc para cancelar.")
        # Mostrar la ventana y permitir la selección
        roi = cv2.selectROI('Seleccionar ROI', frame, showCrosshair=True, fromCenter=False)
        cv2.destroyAllWindows()

        x, y, w, h = roi
        if w <= 0 or h <= 0:
            print('Selección cancelada o ROI inválido')
            return None
        print(f'ROI seleccionado: x={x}, y={y}, w={w}, h={h}')
        return (int(x), int(y), int(w), int(h))
    except Exception as e:
        print(f'Error al seleccionar ROI: {e}')
        try:
            cv2.destroyAllWindows()
        except:
            pass
        return None


if __name__ == '__main__':
    # Simplified flow: only ask for two video files (CLI args or file dialog).
    # No ROI prompts — DEFAULT_ROI will be used when no ROI is provided.
    orig = None
    assembled = None
    roi = None

    if len(sys.argv) >= 3:
        orig = sys.argv[1]
        assembled = sys.argv[2]
    else:
        # Try to open a file dialog for interactive selection of the two videos
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            print('Seleccione el archivo ORIGINAL')
            orig = filedialog.askopenfilename(title='Seleccionar archivo original', filetypes=[('Video files', '*.mp4;*.avi;*.mov;*.dav;*.mkv'), ('All files', '*.*')])
            if not orig:
                print('No se seleccionó archivo original. Abortando.')
                sys.exit(1)

            print('Seleccione el archivo ENSAMBLADO')
            assembled = filedialog.askopenfilename(title='Seleccionar archivo ensamblado', filetypes=[('Video files', '*.mp4;*.avi;*.mov;*.dav;*.mkv'), ('All files', '*.*')])
            if not assembled:
                print('No se seleccionó archivo ensamblado. Abortando.')
                sys.exit(1)

        except Exception:
            # Fallback to CLI usage
            print('No se pudo abrir diálogo gráfico (tkinter). Usa argumentos en la línea de comandos.')
            print('Usage: python compare_detection.py <original_video> <assembled_video>')
            sys.exit(1)

    print("Comparing:\n  original:\t", orig, "\n  assembled:\t", assembled)

    for label, path in [('original', orig), ('assembled', assembled)]:
        print('\n---', label.upper(), '---')
        print('Path:', path)
        print('Exists:', os.path.exists(path))
        if not os.path.exists(path):
            continue
        print('Size (bytes):', os.path.getsize(path))
        print('SHA256:', sha256(path))
        info = file_info(path)
        print('OpenCV opened:', info['cap_opened'])
        print('Frames:', info['frames'])
        print('FPS:', info['fps'])
        print('Duration (s):', info['duration_s'])

    # Run detection on both
    if not os.path.exists(orig) or not os.path.exists(assembled):
        print('\nOne of the files does not exist, cannot run detection')
        sys.exit(1)

    # Usar ROI fijo por defecto (no se pedirá al usuario)
    if roi is None:
        roi = DEFAULT_ROI
    print(f'Usando ROI fijo: x={roi[0]}, y={roi[1]}, w={roi[2]}, h={roi[3]}')

    print('\nRunning detection on original...')
    events_orig, t1 = run_detection(orig, roi=roi)
    print(f'Original events: {len(events_orig)}  (times ms sample: {events_orig[:10]})  duration: {t1:.2f}s')

    print('\nRunning detection on assembled...')
    events_asm, t2 = run_detection(assembled, roi=roi)
    print(f'Assembled events: {len(events_asm)}  (times ms sample: {events_asm[:10]})  duration: {t2:.2f}s')

    # Summary
    print('\n=== SUMMARY ===')
    print('Original events:', len(events_orig))
    print('Assembled events:', len(events_asm))
    if len(events_orig) != len(events_asm):
        print('Mismatch detected. Possible causes: truncated/corrupt assembled file, different FPS/frames, or parameter differences in detection config.')
    else:
        print('Event counts match. The difference may come from other processing steps (ROI applied differently, DB inserts, or post-filters).')
