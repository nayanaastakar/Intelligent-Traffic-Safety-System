from flask import Flask, render_template, jsonify, request
import subprocess
import threading
import os
import uuid
import sys
import time

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 256 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
LOG_FOLDER = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_FOLDER, exist_ok=True)

processes = {}

# Expected uploads: video1/video4/video6 for traffic modules, video5 for drowsiness.
VIDEO_ASSIGNMENTS = {
    'traffic': {
        'video': 'video1.mp4',
        'fallbacks': ['video4.mp4'],
        'label': 'Traffic density',
        'description': 'Road footage for vehicle counting and density',
    },
    'accident': {
        'video': 'video6.mp4',
        'fallbacks': ['video4.mp4', 'video1.mp4'],
        'label': 'Accident detection',
        'description': 'Accident or collision-prone footage',
    },
    'vehicle': {
        'video': 'video1.mp4',
        'fallbacks': ['video4.mp4', 'video6.mp4'],
        'label': 'Vehicle classification',
        'description': 'Mixed traffic for YOLO class labels',
    },
    'overspeed': {
        'video': 'video4.mp4',
        'fallbacks': ['video1.mp4', 'video6.mp4'],
        'label': 'Overspeed alert',
        'description': 'Highway or speed-limited road footage',
    },
    'drowsiness': {
        'video': 'video5.mp4',
        'fallbacks': [],
        'label': 'Driver drowsiness',
        'description': 'In-cab or face-visible driver footage',
    },
}

EXPECTED_VIDEOS = sorted({cfg['video'] for cfg in VIDEO_ASSIGNMENTS.values()})


@app.route('/')
def index():
    return render_template('index.html')


def is_usable_file(path):
    return os.path.isfile(path) and os.path.getsize(path) > 0


def resolve_input_file(filename):
    safe_name = os.path.basename(filename)
    candidates = [
        os.path.join(app.config['UPLOAD_FOLDER'], safe_name),
        os.path.join(BASE_DIR, safe_name),
    ]
    for candidate in candidates:
        if is_usable_file(candidate):
            return candidate
    return None


def file_info(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(filename))
    if not os.path.isfile(path):
        return None
    return {
        'name': os.path.basename(filename),
        'usable': os.path.getsize(path) > 0,
        'path': path,
    }


def best_module_video(module):
    cfg = VIDEO_ASSIGNMENTS.get(module)
    if not cfg:
        return None
    for filename in [cfg['video']] + cfg.get('fallbacks', []):
        info = file_info(filename)
        if info and info['usable']:
            return info['name']
    return None


def log_path_for(process_id, module):
    return os.path.join(LOG_FOLDER, f'{module}-{process_id}.log')


def tail_file(path, max_chars=4000):
    if not path or not os.path.exists(path):
        return ''
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    return content[-max_chars:]


@app.route('/api/uploads', methods=['GET'])
def get_uploads():
    files = []
    for filename in sorted(os.listdir(app.config['UPLOAD_FOLDER'])):
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.isfile(path):
            continue
        size = os.path.getsize(path)
        assigned_to = [
            module for module, cfg in VIDEO_ASSIGNMENTS.items()
            if cfg['video'].lower() == filename.lower()
        ]
        files.append({
            'name': filename,
            'size': size,
            'usable': size > 0,
            'kind': 'video' if os.path.splitext(filename)[1].lower() in {'.mp4', '.avi', '.mov', '.mkv', '.webm'} else 'file',
            'assigned_to': assigned_to,
        })
    return jsonify(files)


@app.route('/api/assignments', methods=['GET'])
def get_assignments():
    uploads = {}
    if os.path.isdir(app.config['UPLOAD_FOLDER']):
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(path):
                uploads[filename.lower()] = {
                    'name': filename,
                    'usable': os.path.getsize(path) > 0,
                }

    modules = {}
    for module, cfg in VIDEO_ASSIGNMENTS.items():
        expected = cfg['video']
        entry = uploads.get(expected.lower())
        modules[module] = {
            'module': module,
            'video': expected,
            'fallbacks': cfg.get('fallbacks', []),
            'label': cfg['label'],
            'description': cfg['description'],
            'ready': bool(entry and entry['usable']),
            'actual_name': entry['name'] if entry else None,
            'selected_video': best_module_video(module),
        }

    return jsonify({
        'modules': modules,
        'expected_videos': EXPECTED_VIDEOS,
        'upload_folder': app.config['UPLOAD_FOLDER'],
    })


@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        # Generate unique filename to avoid conflicts
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        file.save(file_path)
        
        return jsonify({'status': 'success', 'filename': unique_filename})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/modules', methods=['GET'])
def get_modules():
    modules = {
        'traffic': {'name': 'Traffic Density Detection', 'input': 'video', 'description': 'Detect traffic density using YOLO (video required)'},
        'accident': {'name': 'Accident Detection', 'input': 'video', 'description': 'Detect potential accidents by object proximity (video required)'},
        'vehicle': {'name': 'Vehicle Detection', 'input': 'image/video', 'description': 'Detect vehicles and display their class names'},
        'overspeed': {'name': 'Overspeed Alert', 'input': 'image/video', 'description': 'Overlay speed alerts on images/videos'},
        'drowsiness': {'name': 'Drowsiness Detection', 'input': 'camera/video', 'description': 'Detect driver drowsiness using face landmarks from camera or uploaded video'},
    }
    return jsonify(modules)


@app.route('/api/run/<module>', methods=['POST'])
def run_module(module):
    try:
        data = request.get_json()

        if module == 'traffic':
            cmd = [sys.executable, 'traffic.py']
            requested_video = data.get('video') or best_module_video(module)
            if not requested_video:
                return jsonify({'status': 'error', 'message': 'Usable video file required'}), 400
            video_path = resolve_input_file(requested_video)
            if not video_path:
                return jsonify({'status': 'error', 'message': f"Video is missing or empty: {requested_video}"}), 400
            cmd.extend(['--video', video_path])

        elif module == 'accident':
            cmd = [sys.executable, 'accident.py']
            requested_video = data.get('video') or best_module_video(module)
            if not requested_video:
                return jsonify({'status': 'error', 'message': 'Usable video file required'}), 400
            video_path = resolve_input_file(requested_video)
            if not video_path:
                return jsonify({'status': 'error', 'message': f"Video is missing or empty: {requested_video}"}), 400
            cmd.extend(['--video', video_path])

        elif module == 'vehicle':
            cmd = [sys.executable, 'vehicle_name.py']
            if data.get('image'):
                image_path = resolve_input_file(data['image'])
                if not image_path:
                    return jsonify({'status': 'error', 'message': f"Image is missing or empty: {data['image']}"}), 400
                cmd.extend(['--image', image_path])
            elif data.get('video'):
                video_path = resolve_input_file(data['video'])
                if not video_path:
                    return jsonify({'status': 'error', 'message': f"Video is missing or empty: {data['video']}"}), 400
                cmd.extend(['--video', video_path])
            else:
                requested_video = best_module_video(module)
                if not requested_video:
                    return jsonify({'status': 'error', 'message': 'Image or usable video required'}), 400
                video_path = resolve_input_file(requested_video)
                cmd.extend(['--video', video_path])

        elif module == 'overspeed':
            cmd = [sys.executable, 'overspeed.py']
            speed = data.get('speed', 0)
            if data.get('image'):
                image_path = resolve_input_file(data['image'])
                if not image_path:
                    return jsonify({'status': 'error', 'message': f"Image is missing or empty: {data['image']}"}), 400
                cmd.extend(['--image', image_path, '--speed', str(speed)])
            elif data.get('video'):
                video_path = resolve_input_file(data['video'])
                if not video_path:
                    return jsonify({'status': 'error', 'message': f"Video is missing or empty: {data['video']}"}), 400
                cmd.extend(['--video', video_path, '--speed', str(speed)])
            else:
                requested_video = best_module_video(module)
                if not requested_video:
                    return jsonify({'status': 'error', 'message': 'Image or usable video required'}), 400
                video_path = resolve_input_file(requested_video)
                cmd.extend(['--video', video_path, '--speed', str(speed)])

        elif module == 'drowsiness':
            cmd = [sys.executable, 'drowsiness.py']
            if data.get('video'):
                video_path = resolve_input_file(data['video'])
                if not video_path:
                    return jsonify({'status': 'error', 'message': f"Video is missing or empty: {data['video']}"}), 400
                cmd.extend(['--video', video_path])
            else:
                camera = data.get('camera', 0)
                cmd.extend(['--camera', str(camera)])

        else:
            return jsonify({'status': 'error', 'message': 'Unknown module'}), 400

        # Run modules separately so OpenCV windows stay responsive.
        process_id = str(uuid.uuid4().hex)
        log_path = log_path_for(process_id, module)
        log_file = open(log_path, 'w', encoding='utf-8', errors='replace')
        process = subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
        processes[process_id] = {'process': process, 'module': module, 'log_path': log_path}

        time.sleep(0.75)
        if process.poll() is not None:
            log_file.close()
            processes.pop(process_id, None)
            details = tail_file(log_path).strip()
            message = f'{module} exited immediately.'
            if details:
                message = f'{message} {details.splitlines()[-1]}'
            return jsonify({'status': 'error', 'message': message, 'log': details}), 500
        
        # Start a thread to monitor the process
        def monitor_process():
            process.wait()
            log_file.close()
            if process_id in processes:
                del processes[process_id]
        
        monitor_thread = threading.Thread(target=monitor_process)
        monitor_thread.daemon = True
        monitor_thread.start()

        return jsonify({'status': 'success', 'message': f'{module} module started', 'process_id': process_id, 'log': log_path})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'running',
        'modules': [
            {'id': process_id, 'module': info['module']}
            for process_id, info in processes.items()
        ]
    })


@app.route('/api/stop-all', methods=['POST'])
def stop_all():
    stopped = []
    for process_id, info in list(processes.items()):
        process = info['process']
        if process.poll() is None:
            process.terminate()
            stopped.append({'id': process_id, 'module': info['module']})
        processes.pop(process_id, None)
    return jsonify({'status': 'success', 'stopped': stopped})


if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)

