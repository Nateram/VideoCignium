# excel_report.py

import os
import pandas as pd
from datetime import datetime
import db # Importamos nuestro módulo de base de datos

def create_excel_report(carpeta_id, carpeta_path):
    """
    Crea un informe Excel detallado de la carpeta analizada con todos sus videos y clips.
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = os.path.basename(carpeta_path)
        excel_filename = f"Análisis_{folder_name}_{timestamp}.xlsx"
        excel_path = os.path.join(carpeta_path, excel_filename)
        
        conn = db.create_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT fecha_subida FROM carpetas WHERE id = ?", (carpeta_id,))
        fecha_subida = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT id, nombre_archivo, fecha_creacion, roi_x, roi_y, roi_w, roi_h 
            FROM videos WHERE carpeta_id = ? ORDER BY fecha_creacion
        """, (carpeta_id,))
        videos = cursor.fetchall()
        
        videos_df = pd.DataFrame(videos, columns=[
            'ID', 'Nombre del Video', 'Fecha de Creación', 
            'ROI X', 'ROI Y', 'ROI Ancho', 'ROI Alto'
        ])
        
        all_clips_data = []
        for video_id, video_name, _, _, _, _, _ in videos:
            cursor.execute("""
                SELECT nombre_archivo, fecha_evento, objeto_detectado, color_detectado, tiempo_evento_ms
                FROM clips WHERE video_id = ? ORDER BY fecha_evento
            """, (video_id,))
            clips = cursor.fetchall()
            
            for clip_name, fecha, objeto, color, tiempo_ms in clips:
                all_clips_data.append([
                    video_name, fecha, objeto, color, 
                    f"{tiempo_ms/1000:.2f}s en el video original"
                ])
        
        clips_df = pd.DataFrame(all_clips_data, columns=[
            'Video de Origen', 'Fecha y Hora', 
            'Objeto Detectado', 'Color', 'Posición del Evento'
        ])
        
        stats_data = {}
        for _, _, objeto, color, _ in all_clips_data:
            if objeto not in stats_data:
                stats_data[objeto] = {'total': 0, 'colores': {}}
            stats_data[objeto]['total'] += 1
            if color not in stats_data[objeto]['colores']:
                stats_data[objeto]['colores'][color] = 0
            stats_data[objeto]['colores'][color] += 1
        
        stats_rows = []
        for objeto, data in stats_data.items():
            color_info = ", ".join([f"{color}: {count}" for color, count in data['colores'].items()])
            stats_rows.append([objeto, data['total'], color_info])
        
        stats_df = pd.DataFrame(stats_rows, columns=['Objeto', 'Total Detectados', 'Distribución por Color'])
        
        with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
            info_df = pd.DataFrame([
                ['Nombre de Carpeta', folder_name],
                ['Ruta', carpeta_path],
                ['Fecha de Análisis', fecha_subida],
                ['Total de Videos', len(videos)],
                ['Total de Clips', len(all_clips_data)]
            ], columns=['Parámetro', 'Valor'])
            
            info_df.to_excel(writer, sheet_name='Información General', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['Información General']
            header_format = workbook.add_format({'bold': True, 'fg_color': '#D7E4BC', 'border': 1, 'align': 'center'})
            
            for col_num, value in enumerate(info_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 25)
            
            videos_df.to_excel(writer, sheet_name='Videos', index=False)
            clips_df.to_excel(writer, sheet_name='Clips Detectados', index=False)
            stats_df.to_excel(writer, sheet_name='Estadísticas', index=False)
            
            # Ajustar ancho de columnas para todas las hojas
            for sheet_name in ['Información General', 'Videos', 'Clips Detectados', 'Estadísticas']:
                worksheet = writer.sheets[sheet_name]
                if sheet_name == 'Información General':
                    for i, col in enumerate(info_df.columns):
                        col_width = max(25, len(str(col)) + 2)
                        worksheet.set_column(i, i, col_width)
                elif sheet_name == 'Videos':
                    for i, col in enumerate(videos_df.columns):
                        col_width = max(15, len(str(col)) + 2)
                        worksheet.set_column(i, i, col_width)
                elif sheet_name == 'Clips Detectados':
                    for i, col in enumerate(clips_df.columns):
                        col_width = max(15, len(str(col)) + 2)
                        worksheet.set_column(i, i, col_width)
                elif sheet_name == 'Estadísticas':
                    for i, col in enumerate(stats_df.columns):
                        col_width = max(20, len(str(col)) + 2)
                        worksheet.set_column(i, i, col_width)
        
        conn.close()
        return excel_path
        
    except Exception as e:
        print(f"Error al crear el informe Excel: {e}")
        return None

def create_session_excel_report(session_db_path, session_folder_path):
    """
    Crea un informe Excel consolidado de TODA la sesión con todas las carpetas procesadas.
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_name = os.path.basename(session_folder_path)
        excel_filename = f"Análisis_Sesión_Completa_{timestamp}.xlsx"
        excel_path = os.path.join(session_folder_path, excel_filename)

        conn = db.create_db_connection(session_db_path)
        cursor = conn.cursor()

        # Obtener todas las carpetas de la sesión
        cursor.execute("SELECT id, ruta, fecha_subida FROM carpetas ORDER BY fecha_subida")
        folders = cursor.fetchall()

        # Información general de la sesión
        session_info = [
            ['Nombre de Sesión', session_name],
            ['Ruta de Sesión', session_folder_path],
            ['Fecha de Creación', timestamp],
            ['Total de Carpetas', len(folders)]
        ]

        # Obtener todos los videos de todas las carpetas
        all_videos_data = []
        all_clips_data = []

        total_videos = 0
        total_clips = 0

        for folder_id, folder_path, fecha_subida in folders:
            folder_name = os.path.basename(folder_path)

            cursor.execute("""
                SELECT id, nombre_archivo, fecha_creacion, roi_x, roi_y, roi_w, roi_h
                FROM videos WHERE carpeta_id = ? ORDER BY fecha_creacion
            """, (folder_id,))
            videos = cursor.fetchall()

            total_videos += len(videos)

            for video_id, video_name, fecha_creacion, roi_x, roi_y, roi_w, roi_h in videos:
                all_videos_data.append([
                    folder_name, video_name, fecha_creacion,
                    roi_x or 0, roi_y or 0, roi_w or 0, roi_h or 0
                ])

                # Obtener clips de este video
                cursor.execute("""
                    SELECT nombre_archivo, fecha_evento, objeto_detectado, color_detectado, tiempo_evento_ms
                    FROM clips WHERE video_id = ? ORDER BY fecha_evento
                """, (video_id,))
                clips = cursor.fetchall()

                total_clips += len(clips)

                for clip_name, fecha, objeto, color, tiempo_ms in clips:
                    all_clips_data.append([
                        folder_name, video_name, fecha, objeto or 'Sin clasificar', color or 'No detectado',
                        f"{tiempo_ms/1000:.2f}s" if tiempo_ms else "N/A"
                    ])

        # Actualizar información de la sesión
        session_info.extend([
            ['Total de Videos', total_videos],
            ['Total de Clips', total_clips]
        ])

        # Crear DataFrames
        info_df = pd.DataFrame(session_info, columns=['Parámetro', 'Valor'])

        videos_df = pd.DataFrame(all_videos_data, columns=[
            'Carpeta', 'Nombre del Video', 'Fecha de Creación',
            'ROI X', 'ROI Y', 'ROI Ancho', 'ROI Alto'
        ])

        clips_df = pd.DataFrame(all_clips_data, columns=[
            'Carpeta', 'Video de Origen', 'Fecha y Hora',
            'Objeto Detectado', 'Color', 'Posición del Evento'
        ])

        # Estadísticas consolidadas
        stats_data = {}
        for _, _, _, objeto, color, _ in all_clips_data:
            if objeto not in stats_data:
                stats_data[objeto] = {'total': 0, 'colores': {}}
            stats_data[objeto]['total'] += 1
            if color not in stats_data[objeto]['colores']:
                stats_data[objeto]['colores'][color] = 0
            stats_data[objeto]['colores'][color] += 1

        stats_rows = []
        for objeto, data in stats_data.items():
            color_info = ", ".join([f"{color}: {count}" for color, count in data['colores'].items()])
            stats_rows.append([objeto, data['total'], color_info])

        stats_df = pd.DataFrame(stats_rows, columns=['Objeto', 'Total Detectados', 'Distribución por Color'])

        # Estadísticas por carpeta
        folder_stats = {}
        for folder_name, _, _, objeto, _, _ in all_clips_data:
            if folder_name not in folder_stats:
                folder_stats[folder_name] = {}
            if objeto not in folder_stats[folder_name]:
                folder_stats[folder_name][objeto] = 0
            folder_stats[folder_name][objeto] += 1

        folder_stats_rows = []
        for folder_name, objects in folder_stats.items():
            for objeto, count in objects.items():
                folder_stats_rows.append([folder_name, objeto, count])

        folder_stats_df = pd.DataFrame(folder_stats_rows, columns=['Carpeta', 'Objeto', 'Cantidad'])

        # Crear Excel con múltiples hojas
        with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
            workbook = writer.book

            # Información General
            info_df.to_excel(writer, sheet_name='Información General', index=False)
            worksheet = writer.sheets['Información General']
            header_format = workbook.add_format({'bold': True, 'fg_color': '#D7E4BC', 'border': 1, 'align': 'center'})
            for col_num, value in enumerate(info_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 25)

            # Videos
            videos_df.to_excel(writer, sheet_name='Videos', index=False)
            worksheet = writer.sheets['Videos']
            for i, col in enumerate(videos_df.columns):
                col_width = max(15, len(str(col)) + 2)
                worksheet.set_column(i, i, col_width)

            # Clips Detectados
            clips_df.to_excel(writer, sheet_name='Clips Detectados', index=False)
            worksheet = writer.sheets['Clips Detectados']
            for i, col in enumerate(clips_df.columns):
                col_width = max(15, len(str(col)) + 2)
                worksheet.set_column(i, i, col_width)

            # Estadísticas Generales
            stats_df.to_excel(writer, sheet_name='Estadísticas', index=False)
            worksheet = writer.sheets['Estadísticas']
            for i, col in enumerate(stats_df.columns):
                col_width = max(20, len(str(col)) + 2)
                worksheet.set_column(i, i, col_width)

            # Estadísticas por Carpeta
            folder_stats_df.to_excel(writer, sheet_name='Estadísticas por Carpeta', index=False)
            worksheet = writer.sheets['Estadísticas por Carpeta']
            for i, col in enumerate(folder_stats_df.columns):
                col_width = max(20, len(str(col)) + 2)
                worksheet.set_column(i, i, col_width)

        conn.close()
        print(f"✅ Excel consolidado de sesión creado: {excel_path}")
        return excel_path

    except Exception as e:
        print(f"❌ Error al crear el informe Excel consolidado: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_or_update_session_excel(session_db_path, session_folder_path):
    """
    Crea o actualiza el Excel único de la sesión.
    Si no existe, lo crea vacío. Si existe, lo actualiza con los datos actuales.
    """
    try:
        # Nombre fijo para el Excel de sesión
        excel_filename = "session_data.xlsx"
        excel_path = os.path.join(session_folder_path, excel_filename)

        conn = db.create_db_connection(session_db_path)
        cursor = conn.cursor()

        # Obtener todas las carpetas de la sesión
        cursor.execute("SELECT id, ruta, fecha_subida FROM carpetas ORDER BY fecha_subida")
        folders = cursor.fetchall()

        # Información general de la sesión
        session_name = os.path.basename(session_folder_path)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        session_info = [
            ['Nombre de Sesión', session_name],
            ['Ruta de Sesión', session_folder_path],
            ['Última Actualización', timestamp],
            ['Total de Carpetas', len(folders)]
        ]

        # Obtener todos los videos de todas las carpetas
        all_videos_data = []
        all_clips_data = []

        total_videos = 0
        total_clips = 0

        for folder_id, folder_path, fecha_subida in folders:
            folder_name = os.path.basename(folder_path)

            cursor.execute("""
                SELECT id, nombre_archivo, fecha_creacion, roi_x, roi_y, roi_w, roi_h
                FROM videos WHERE carpeta_id = ? ORDER BY fecha_creacion
            """, (folder_id,))
            videos = cursor.fetchall()

            total_videos += len(videos)

            for video_id, video_name, fecha_creacion, roi_x, roi_y, roi_w, roi_h in videos:
                all_videos_data.append([
                    folder_name, video_name, fecha_creacion,
                    roi_x or 0, roi_y or 0, roi_w or 0, roi_h or 0
                ])

                # Obtener clips de este video
                cursor.execute("""
                    SELECT nombre_archivo, fecha_evento, objeto_detectado, color_detectado, tiempo_evento_ms
                    FROM clips WHERE video_id = ? ORDER BY fecha_evento
                """, (video_id,))
                clips = cursor.fetchall()

                total_clips += len(clips)

                for clip_name, fecha, objeto, color, tiempo_ms in clips:
                    all_clips_data.append([
                        folder_name, video_name, fecha, objeto or 'Sin clasificar', color or 'No detectado',
                        f"{tiempo_ms/1000:.2f}s" if tiempo_ms else "N/A"
                    ])

        # Actualizar información de la sesión
        session_info.extend([
            ['Total de Videos', total_videos],
            ['Total de Clips', total_clips]
        ])

        # Crear DataFrames (vacíos si no hay datos)
        info_df = pd.DataFrame(session_info, columns=['Parámetro', 'Valor'])

        if all_videos_data:
            videos_df = pd.DataFrame(all_videos_data, columns=[
                'Carpeta', 'Nombre del Video', 'Fecha de Creación',
                'ROI X', 'ROI Y', 'ROI Ancho', 'ROI Alto'
            ])
        else:
            videos_df = pd.DataFrame(columns=[
                'Carpeta', 'Nombre del Video', 'Fecha de Creación',
                'ROI X', 'ROI Y', 'ROI Ancho', 'ROI Alto'
            ])

        if all_clips_data:
            clips_df = pd.DataFrame(all_clips_data, columns=[
                'Carpeta', 'Video de Origen', 'Fecha y Hora',
                'Objeto Detectado', 'Color', 'Posición del Evento'
            ])
        else:
            clips_df = pd.DataFrame(columns=[
                'Carpeta', 'Video de Origen', 'Fecha y Hora',
                'Objeto Detectado', 'Color', 'Posición del Evento'
            ])

        # Estadísticas consolidadas (vacías si no hay datos)
        if all_clips_data:
            stats_data = {}
            for _, _, _, objeto, color, _ in all_clips_data:
                if objeto not in stats_data:
                    stats_data[objeto] = {'total': 0, 'colores': {}}
                stats_data[objeto]['total'] += 1
                if color not in stats_data[objeto]['colores']:
                    stats_data[objeto]['colores'][color] = 0
                stats_data[objeto]['colores'][color] += 1

            stats_rows = []
            for objeto, data in stats_data.items():
                color_info = ", ".join([f"{color}: {count}" for color, count in data['colores'].items()])
                stats_rows.append([objeto, data['total'], color_info])

            stats_df = pd.DataFrame(stats_rows, columns=['Objeto', 'Total Detectados', 'Distribución por Color'])
        else:
            stats_df = pd.DataFrame(columns=['Objeto', 'Total Detectados', 'Distribución por Color'])

        # Crear Excel con múltiples hojas
        with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
            # Información General
            info_df.to_excel(writer, sheet_name='Información General', index=False)

            # Videos
            videos_df.to_excel(writer, sheet_name='Videos', index=False)

            # Clips Detectados
            clips_df.to_excel(writer, sheet_name='Clips Detectados', index=False)

            # Estadísticas Generales
            stats_df.to_excel(writer, sheet_name='Estadísticas', index=False)

        conn.close()
        print(f"✅ Excel de sesión {'creado' if not os.path.exists(excel_path) else 'actualizado'}: {excel_path}")
        return excel_path

    except Exception as e:
        print(f"❌ Error al crear/actualizar el Excel de sesión: {e}")
        import traceback
        traceback.print_exc()
        return None