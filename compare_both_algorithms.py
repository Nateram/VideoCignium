"""
Script para comparar ambos video_processing.py (original vs actual)
Ejecuta la detección sobre el MISMO video con el MISMO ROI
"""
import sys
import os
import time
import importlib.util

# ROI fijo (tomado de la UI: X:323 Y:12 Ancho:217 Alto:171)
DEFAULT_ROI = (323, 12, 217, 171)

# Rutas a los dos video_processing.py
ORIGINAL_VP = r"c:\Users\pabli\Desktop\web_app\web_app_original\video_processing.py"
ACTUAL_VP = r"c:\Users\pabli\Desktop\web_app\video_processing.py"

# Video de prueba (usa la ruta que ya probamos)
TEST_VIDEO = r"C:/Users/pabli/Desktop/videos/XVR 1_ch1_main_20240717143000_20240717144000.dav"


def load_module_from_path(module_name, file_path):
    """Carga un módulo Python desde una ruta específica"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_detection_with_module(module, video_path, roi):
    """Ejecuta la detección usando un módulo específico"""
    print(f"\n{'='*80}")
    print(f"Ejecutando detección con: {module.__name__}")
    print(f"{'='*80}")
    
    # Obtener configuración
    config = module.get_motion_detection_config()
    print(f"Config: {config}")
    
    # Ejecutar detección
    start = time.time()
    events = module.process_video_for_motion_advanced(video_path, roi, config)
    elapsed = time.time() - start
    
    print(f"\n✅ Detección completada en {elapsed:.2f}s")
    print(f"📊 Eventos detectados: {len(events)}")
    print(f"⏱️  Timestamps (primeros 15): {events[:15]}")
    
    return events, elapsed, config


if __name__ == '__main__':
    print("="*80)
    print("🔬 COMPARACIÓN DE ALGORITMOS: ORIGINAL vs ACTUAL")
    print("="*80)
    
    # Verificar que el video existe
    if not os.path.exists(TEST_VIDEO):
        print(f"❌ ERROR: Video no encontrado: {TEST_VIDEO}")
        sys.exit(1)
    
    print(f"\n📹 Video de prueba: {TEST_VIDEO}")
    print(f"📐 ROI: x={DEFAULT_ROI[0]}, y={DEFAULT_ROI[1]}, w={DEFAULT_ROI[2]}, h={DEFAULT_ROI[3]}")
    
    # Cargar módulo ORIGINAL
    print(f"\n🔵 Cargando video_processing.py ORIGINAL...")
    vp_original = load_module_from_path("video_processing_original", ORIGINAL_VP)
    
    # Cargar módulo ACTUAL
    print(f"🟢 Cargando video_processing.py ACTUAL...")
    vp_actual = load_module_from_path("video_processing_actual", ACTUAL_VP)
    
    # Ejecutar detección con módulo ORIGINAL
    events_original, time_original, config_original = run_detection_with_module(
        vp_original, TEST_VIDEO, DEFAULT_ROI
    )
    
    # Ejecutar detección con módulo ACTUAL
    events_actual, time_actual, config_actual = run_detection_with_module(
        vp_actual, TEST_VIDEO, DEFAULT_ROI
    )
    
    # COMPARAR RESULTADOS
    print("\n" + "="*80)
    print("📊 RESUMEN DE COMPARACIÓN")
    print("="*80)
    
    print(f"\n🔵 ORIGINAL:")
    print(f"   • Config: {config_original}")
    print(f"   • Eventos: {len(events_original)}")
    print(f"   • Tiempo: {time_original:.2f}s")
    print(f"   • Timestamps: {events_original[:10]}")
    
    print(f"\n🟢 ACTUAL:")
    print(f"   • Config: {config_actual}")
    print(f"   • Eventos: {len(events_actual)}")
    print(f"   • Tiempo: {time_actual:.2f}s")
    print(f"   • Timestamps: {events_actual[:10]}")
    
    print(f"\n{'='*80}")
    print("🎯 RESULTADO:")
    print("="*80)
    
    # Comparar configuraciones
    if config_original != config_actual:
        print("⚠️  CONFIGURACIONES DIFERENTES:")
        for key in config_original.keys():
            if config_original[key] != config_actual.get(key):
                print(f"   • {key}: original={config_original[key]}, actual={config_actual.get(key)}")
    else:
        print("✅ Configuraciones IDÉNTICAS")
    
    # Comparar número de eventos
    if len(events_original) == len(events_actual):
        print(f"✅ Mismo número de eventos detectados: {len(events_original)}")
    else:
        print(f"❌ DIFERENCIA en eventos detectados:")
        print(f"   • Original: {len(events_original)} eventos")
        print(f"   • Actual:   {len(events_actual)} eventos")
        print(f"   • Delta:    {abs(len(events_original) - len(events_actual))} eventos de diferencia")
    
    # Comparar timestamps exactos
    if events_original == events_actual:
        print("✅ Timestamps IDÉNTICOS (hasta el milisegundo)")
    else:
        print("⚠️  Timestamps diferentes:")
        # Mostrar eventos que están en uno pero no en el otro
        set_original = set(events_original)
        set_actual = set(events_actual)
        
        only_in_original = set_original - set_actual
        only_in_actual = set_actual - set_original
        
        if only_in_original:
            print(f"\n   🔵 Solo en ORIGINAL ({len(only_in_original)} eventos):")
            for ts in sorted(only_in_original)[:10]:
                print(f"      • {ts:.1f}ms")
        
        if only_in_actual:
            print(f"\n   🟢 Solo en ACTUAL ({len(only_in_actual)} eventos):")
            for ts in sorted(only_in_actual)[:10]:
                print(f"      • {ts:.1f}ms")
    
    print("\n" + "="*80)
    
    # Conclusión
    if len(events_original) == len(events_actual) and events_original == events_actual:
        print("✅ CONCLUSIÓN: Ambos algoritmos son IDÉNTICOS")
        print("   → El problema de 12 vs 2 clips NO está en el algoritmo de detección")
        print("   → Revisar: ROI usado en las pruebas, archivos de video, sesiones/estado")
    else:
        print("❌ CONCLUSIÓN: Los algoritmos producen resultados DIFERENTES")
        print("   → Hay una diferencia real en el código o configuración")
        print("   → Revisar diferencias específicas arriba")
