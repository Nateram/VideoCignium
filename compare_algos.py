import time
import importlib.util
import sys
import os

# Video paths taken from your previous run
VIDEO_ORIG = r"C:\Users\pabli\Desktop\videos\XVR 1_ch1_main_20240717143000_20240717144000.dav"
VIDEO_ASM = r"C:\Users\pabli\Desktop\web_app\static\uploads\session_20251108_191617\XVR_1_ch1_main_20240717143000_20240717144000.dav"

# ROI fixed as requested
DEFAULT_ROI = (323, 12, 217, 171)

OUTPUT_SEPARATOR = "\n" + ("-" * 60) + "\n"


def load_module_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_for_module(mod, video_path, roi):
    """Run motion detection using the best available function in the module.
    Returns (function_used, events_list, elapsed_seconds)
    """
    # choose config function if available
    config = None
    try:
        if hasattr(mod, 'get_motion_detection_config'):
            config = mod.get_motion_detection_config()
    except Exception as e:
        print(f"Warning: error getting config from module: {e}")

    # pick the preferred function
    func = None
    if hasattr(mod, 'process_video_for_motion_advanced'):
        func = mod.process_video_for_motion_advanced
        func_name = 'process_video_for_motion_advanced'
    elif hasattr(mod, 'process_video_for_motion'):
        func = mod.process_video_for_motion
        func_name = 'process_video_for_motion'
    else:
        raise RuntimeError('Module has no recognized processing function')

    start = time.time()
    try:
        if config is None:
            events = func(video_path, tuple(roi) if roi else None)
        else:
            events = func(video_path, tuple(roi) if roi else None, config)
    except TypeError:
        # fallback: if signature doesn't match (some versions may not accept config), call without it
        events = func(video_path, tuple(roi) if roi else None)
    elapsed = time.time() - start
    return func_name, events, elapsed


if __name__ == '__main__':
    # Paths for the two versions of video_processing.py
    cur_mod_path = os.path.join(os.path.dirname(__file__), 'video_processing.py')
    orig_mod_path = os.path.join(os.path.dirname(__file__), 'web_app_original', 'video_processing.py')

    print('Using videos:')
    print(' ORIGINAL:', VIDEO_ORIG)
    print(' ASSEMBLED:', VIDEO_ASM)
    print('\nUsing ROI fixed:', DEFAULT_ROI)
    print(OUTPUT_SEPARATOR)

    # Load current module (should be importable directly as well)
    try:
        import video_processing as vp_current
        print('Loaded current video_processing via package import')
    except Exception:
        print('Import fallback: loading current video_processing from file')
        vp_current = load_module_from_path('video_processing_current', cur_mod_path)

    # Load original module from web_app_original
    if os.path.exists(orig_mod_path):
        vp_orig = load_module_from_path('video_processing_orig', orig_mod_path)
        print('Loaded original video_processing from web_app_original')
    else:
        print(f'Original module not found at {orig_mod_path}, exiting')
        sys.exit(1)

    modules = [
        ('current', vp_current),
        ('original', vp_orig)
    ]

    results = {}

    for mod_name, mod in modules:
        print(f"\nRunning module: {mod_name}")
        results[mod_name] = {}
        for vid_label, vid_path in [('original_video', VIDEO_ORIG), ('assembled_video', VIDEO_ASM)]:
            print(f"\n  Video: {vid_label} -> {vid_path}")
            if not os.path.exists(vid_path):
                print('   -> File not found, skipping')
                results[mod_name][vid_label] = None
                continue
            try:
                func_name, events, elapsed = run_for_module(mod, vid_path, DEFAULT_ROI)
                print(f"   -> Function: {func_name}")
                print(f"   -> Events detected: {len(events)}")
                print(f"   -> Sample times (ms): {events[:10]}")
                print(f"   -> Elapsed: {elapsed:.2f}s")
                results[mod_name][vid_label] = {'func': func_name, 'events': events, 'elapsed': elapsed}
            except Exception as e:
                print(f"   -> Error running detection: {e}")
                results[mod_name][vid_label] = {'error': str(e)}

    print(OUTPUT_SEPARATOR)
    print('SUMMARY:')
    for mod_name in results:
        print(f"\nModule: {mod_name}")
        for vid_label in ['original_video', 'assembled_video']:
            info = results[mod_name].get(vid_label)
            if info is None:
                print(f"  {vid_label}: missing")
            elif 'error' in info:
                print(f"  {vid_label}: ERROR: {info['error']}")
            else:
                print(f"  {vid_label}: {len(info['events'])} events, func={info['func']}, time={info['elapsed']:.2f}s")

    # Cross-compare: current vs original for each video
    print(OUTPUT_SEPARATOR)
    for vid_label in ['original_video', 'assembled_video']:
        cur = results['current'].get(vid_label)
        orig = results['original'].get(vid_label)
        print(f"Comparing results for {vid_label}:")
        if not cur or not orig or 'error' in (cur or {}) or 'error' in (orig or {}):
            print('  -> One version failed, cannot compare')
            continue
        print(f"  current: {len(cur['events'])} events; original: {len(orig['events'])} events")
        if len(cur['events']) == len(orig['events']):
            print('  -> Event counts match')
        else:
            print('  -> Event counts differ')
        # Optionally compare timestamps roughly
        print('  -> current sample:', cur['events'][:6])
        print('  -> original sample:', orig['events'][:6])

    print('\nDone')
