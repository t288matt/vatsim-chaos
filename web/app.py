from flask import Flask, render_template, request, jsonify, send_file
import os
import subprocess
import json
import shutil
from werkzeug.utils import secure_filename
import threading
import time
import sys
import logging
from datetime import datetime
import psutil
import tempfile

# Add parent directory to path to import shared types
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_types import FlightPlan, Waypoint

# Import configuration
from config import get_config

# Get configuration based on environment
config = get_config()

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_FILE_SIZE

# Global processing state
processing_status = {
    'is_processing': False,
    'current_step': 0,
    'total_steps': 6,
    'completed': False,
    'failed': False,
    'error': None,
    'start_time': None,
    'end_time': None
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        logger.warning("Upload attempt with no files")
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    uploaded_files = []
    
    # Edge case: Check disk space before upload
    if not check_disk_space():
        logger.error("Insufficient disk space for upload")
        return jsonify({'error': 'Insufficient disk space on server'}), 507
    
    # Edge case: Check memory usage
    if not check_memory_usage():
        logger.error("High memory usage detected")
        return jsonify({'error': 'Server is under high load. Please try again later.'}), 503
    
    for file in files:
        if file and file.filename:
            # Validate file extension
            if not file.filename.lower().endswith('.xml'):
                logger.warning(f"Invalid file type attempted: {file.filename}")
                continue
                
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Edge case: Check for filename conflicts
            if os.path.exists(filepath):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(filepath):
                    filename = f"{base}_{counter}{ext}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    counter += 1
                logger.info(f"Renamed duplicate file to: {filename}")
            
            # Ensure upload directory exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            # Validate file size
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            
            if file_size > config.MAX_FILE_SIZE:
                logger.error(f"File {filename} exceeds size limit: {file_size} bytes")
                return jsonify({'error': f'File {filename} exceeds maximum size limit'}), 413
            
            # Edge case: Check if file is empty
            if file_size == 0:
                logger.warning(f"Empty file skipped: {filename}")
                continue
            
            try:
                file.save(filepath)
                logger.info(f"File uploaded successfully: {filename} ({file_size} bytes)")
                uploaded_files.append({
                    'name': filename,
                    'size': os.path.getsize(filepath),
                    'upload_date': time.time()
                })
            except Exception as e:
                logger.error(f"Failed to save file {filename}: {str(e)}")
                return jsonify({'error': f'Failed to save file {filename}'}), 500
    
    logger.info(f"Upload completed: {len(uploaded_files)} files")
    return jsonify({'uploaded': uploaded_files})

def check_disk_space(min_space_gb=1):
    """Check if there's sufficient disk space"""
    try:
        stat = os.statvfs(app.config['UPLOAD_FOLDER'])
        free_space_gb = (stat.f_frsize * stat.f_bavail) / (1024**3)
        return free_space_gb >= min_space_gb
    except Exception as e:
        logger.warning(f"Could not check disk space: {e}")
        return True  # Assume OK if we can't check

def check_memory_usage(max_percent=90):
    """Check if memory usage is acceptable"""
    try:
        memory_percent = psutil.virtual_memory().percent
        return memory_percent < max_percent
    except Exception as e:
        logger.warning(f"Could not check memory usage: {e}")
        return True  # Assume OK if we can't check

@app.route('/files', methods=['GET'])
def list_files():
    # Get absolute path to xml_files directory
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    upload_dir = os.path.join(parent_dir, 'xml_files')
    files = []
    
    if os.path.exists(upload_dir):
        try:
            for filename in os.listdir(upload_dir):
                if filename.endswith('.xml'):
                    filepath = os.path.join(upload_dir, filename)
                    try:
                        files.append({
                            'id': filename,
                            'name': filename,
                            'size': os.path.getsize(filepath),
                            'upload_date': os.path.getmtime(filepath)
                        })
                    except OSError as e:
                        logger.warning(f"Could not read file {filename}: {e}")
                        continue
        except OSError as e:
            logger.error(f"Error reading upload directory: {e}")
            return jsonify({'error': 'Could not read file directory'}), 500
    
    return jsonify(files)

@app.route('/validate/<filename>', methods=['GET'])
def validate_file(filename):
    """Validate XML file structure using shared types"""
    logger.debug(f"[VALIDATE] Requested validation for file: {filename}")
    try:
        # Get absolute path to xml_files directory
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.join(parent_dir, 'xml_files', filename)
        logger.debug(f"[VALIDATE] Full file path: {filepath}")
        
        if not os.path.exists(filepath):
            logger.warning(f"Validation requested for non-existent file: {filename}")
            return jsonify({'error': 'File not found'}), 404
        
        # Edge case: Check file size for validation
        file_size = os.path.getsize(filepath)
        logger.debug(f"[VALIDATE] File size: {file_size} bytes")
        if file_size > 50 * 1024 * 1024:  # 50MB limit for validation
            logger.warning(f"File too large for validation: {filename} ({file_size} bytes)")
            return jsonify({
                'valid': False,
                'error': 'File too large for validation (max 50MB)'
            }), 413
            
        # Import the extraction module to validate
        from extract_simbrief_xml_flightplan import extract_flight_plan_from_xml
        
        with open(filepath, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        logger.debug(f"[VALIDATE] Read XML content length: {len(xml_content)}")
        
        # Edge case: Check for malformed XML
        if not xml_content.strip():
            logger.warning(f"[VALIDATE] File is empty: {filename}")
            return jsonify({
                'valid': False,
                'error': 'File is empty'
            }), 400
        
        # Try to parse with shared types
        try:
            flight_plan = extract_flight_plan_from_xml(filepath)
            logger.debug(f"[VALIDATE] extract_flight_plan_from_xml returned: {flight_plan}")
        except Exception as parse_exc:
            logger.error(f"[VALIDATE] Exception in extract_flight_plan_from_xml: {parse_exc}")
            return jsonify({
                'valid': False,
                'error': f'Parse error: {parse_exc}'
            }), 400
        flight_plans = [flight_plan] if flight_plan else []
        
        validation_result = {
            'valid': True,
            'flight_count': len(flight_plans),
            'flights': []
        }
        
        for fp in flight_plans:
            validation_result['flights'].append({
                'origin': fp.origin,
                'destination': fp.destination,
                'aircraft_type': fp.aircraft_type,
                'waypoint_count': len(fp.waypoints)
            })
        
        logger.info(f"File validation successful: {filename} - {len(flight_plans)} flights")
        return jsonify(validation_result)
        
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error for {filename}: {e}")
        return jsonify({
            'valid': False,
            'error': 'File contains invalid characters'
        }), 400
    except Exception as e:
        logger.error(f"File validation failed: {filename} - {str(e)}", exc_info=True)
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 400

@app.route('/validate-same-routes', methods=['POST'])
def validate_same_routes():
    """Check if selected files contain same origin-destination pairs"""
    try:
        data = request.get_json()
        selected_files = data.get('files', [])
        
        if not selected_files:
            return jsonify({'error': 'No files selected'}), 400
        
        # Collect all routes from selected files
        all_routes = []
        route_details = {}
        
        for filename in selected_files:
            # Get absolute path to xml_files directory
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            filepath = os.path.join(parent_dir, 'xml_files', filename)
            
            if not os.path.exists(filepath):
                continue
                
            try:
                from extract_simbrief_xml_flightplan import extract_flight_plan_from_xml
                flight_plan = extract_flight_plan_from_xml(filepath)
                
                if flight_plan:
                    route_key = f"{flight_plan.origin}-{flight_plan.destination}"
                    all_routes.append(route_key)
                    route_details[route_key] = {
                        'origin': flight_plan.origin,
                        'destination': flight_plan.destination,
                        'aircraft_type': flight_plan.aircraft_type,
                        'filename': filename
                    }
            except Exception as e:
                logger.warning(f"Could not validate route for {filename}: {e}")
                continue
        
        # Check for duplicate routes
        route_counts = {}
        duplicate_routes = []
        
        for route in all_routes:
            route_counts[route] = route_counts.get(route, 0) + 1
            if route_counts[route] > 1:
                duplicate_routes.append(route)
        
        # Remove duplicates from duplicate_routes list
        duplicate_routes = list(set(duplicate_routes))
        
        validation_result = {
            'has_duplicates': len(duplicate_routes) > 0,
            'duplicate_routes': [],
            'total_routes': len(all_routes),
            'unique_routes': len(set(all_routes))
        }
        
        # Add details for duplicate routes
        for route in duplicate_routes:
            files_with_route = [details for key, details in route_details.items() if key == route]
            validation_result['duplicate_routes'].append({
                'route': route,
                'origin': route_details[route]['origin'],
                'destination': route_details[route]['destination'],
                'aircraft_type': route_details[route]['aircraft_type'],
                'files': [f['filename'] for f in files_with_route],
                'count': route_counts[route]
            })
        
        logger.info(f"Route validation completed: {len(duplicate_routes)} duplicate routes found")
        return jsonify(validation_result)
        
    except Exception as e:
        logger.error(f"Route validation failed: {str(e)}")
        return jsonify({
            'error': f'Route validation failed: {str(e)}'
        }), 500

@app.route('/process', methods=['POST'])
def process_files():
    if processing_status['is_processing']:
        logger.warning("Processing already in progress")
        return jsonify({'error': 'Processing already in progress'}), 409
    
    data = request.get_json()
    selected_files = data.get('files', [])
    
    if not selected_files:
        logger.warning("Processing requested with no files selected")
        return jsonify({'error': 'No files selected'}), 400
    
    # Edge case: Check if too many files selected
    if len(selected_files) > 100:
        logger.warning(f"Too many files selected for processing: {len(selected_files)}")
        return jsonify({'error': 'Too many files selected (max 100)'}), 400
    
    # Edge case: Check disk space before processing
    if not check_disk_space(min_space_gb=2):
        logger.error("Insufficient disk space for processing")
        return jsonify({'error': 'Insufficient disk space for processing'}), 507
    
    logger.info(f"Starting processing for {len(selected_files)} files: {selected_files}")
    
    # Start processing in background thread
    thread = threading.Thread(target=run_processing, args=(selected_files,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Processing started'})

def run_processing(selected_files):
    global processing_status
    
    processing_status = {
        'is_processing': True,
        'current_step': 0,
        'total_steps': 6,
        'completed': False,
        'failed': False,
        'error': None,
        'start_time': datetime.now().isoformat(),
        'end_time': None
    }
    
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    original_dir = os.getcwd()
    
    try:
        # Copy selected files to parent directory for processing
        logger.info("Copying files to processing directory")
        for filename in selected_files:
            # Get absolute path to xml_files directory
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            src = os.path.join(parent_dir, 'xml_files', filename)
            dst = os.path.join(parent_dir, filename)
            
            # Edge case: Check if source file exists
            if not os.path.exists(src):
                raise FileNotFoundError(f"Source file not found: {filename}")
            
            shutil.copy2(src, dst)
            logger.info(f"Copied {filename} to processing directory")
        
        # Change to parent directory for processing
        os.chdir(parent_dir)
        logger.info(f"Changed to processing directory: {parent_dir}")
        
        # Step 1: Extract flight plan data
        logger.info("Step 1: Extracting flight plan data")
        processing_status['current_step'] = 0
        
        # Build command with selected files
        extract_cmd = ['python', 'extract_simbrief_xml_flightplan.py', '--files'] + selected_files
        result = subprocess.run(extract_cmd, check=True, timeout=300, capture_output=True, text=True)
        logger.info(f"Step 1 completed: {result.returncode}")
        
        # Step 2: Analyze conflicts
        logger.info("Step 2: Analyzing conflicts")
        processing_status['current_step'] = 1
        result = subprocess.run(['python', 'find_potential_conflicts.py'], check=True, timeout=600, capture_output=True, text=True)
        logger.info(f"Step 2 completed: {result.returncode}")
        
        # Step 3: Merge KML files
        logger.info("Step 3: Merging KML files")
        processing_status['current_step'] = 2
        result = subprocess.run(['python', 'merge_kml_flightplans.py'], check=True, timeout=300, capture_output=True, text=True)
        logger.info(f"Step 3 completed: {result.returncode}")
        
        # Step 4: Schedule conflicts
        logger.info("Step 4: Scheduling conflicts")
        processing_status['current_step'] = 3
        result = subprocess.run(['python', 'generate_schedule_conflicts.py', '--start', '14:00', '--end', '18:00'], check=True, timeout=300, capture_output=True, text=True)
        logger.info(f"Step 4 completed: {result.returncode}")
        
        # Step 5: Export animation data
        logger.info("Step 5: Exporting animation data")
        processing_status['current_step'] = 4
        result = subprocess.run(['python', 'generate_animation.py'], check=True, timeout=300, capture_output=True, text=True)
        logger.info(f"Step 5 completed: {result.returncode}")
        
        # Step 6: Audit conflict data
        logger.info("Step 6: Auditing conflict data")
        processing_status['current_step'] = 5
        result = subprocess.run(['python', 'audit_conflict.py'], check=True, timeout=300, capture_output=True, text=True)
        logger.info(f"Step 6 completed: {result.returncode}")
        
        processing_status['completed'] = True
        processing_status['end_time'] = datetime.now().isoformat()
        logger.info("Processing completed successfully")
        
    except subprocess.TimeoutExpired as e:
        processing_status['failed'] = True
        processing_status['error'] = f'Processing timed out at step {processing_status["current_step"]}: {str(e)}'
        processing_status['end_time'] = datetime.now().isoformat()
        logger.error(f"Processing timed out at step {processing_status['current_step']}: {str(e)}")
        
        if config.CLEANUP_ON_FAILURE:
            cleanup_processing_files(selected_files, parent_dir)
            
    except subprocess.CalledProcessError as e:
        processing_status['failed'] = True
        processing_status['error'] = f'Processing failed at step {processing_status["current_step"]}: {str(e)}'
        processing_status['end_time'] = datetime.now().isoformat()
        logger.error(f"Processing failed at step {processing_status['current_step']}: {str(e)}")
        
        if config.CLEANUP_ON_FAILURE:
            cleanup_processing_files(selected_files, parent_dir)
            
    except FileNotFoundError as e:
        processing_status['failed'] = True
        processing_status['error'] = f'File not found: {str(e)}'
        processing_status['end_time'] = datetime.now().isoformat()
        logger.error(f"File not found during processing: {str(e)}")
        
        if config.CLEANUP_ON_FAILURE:
            cleanup_processing_files(selected_files, parent_dir)
            
    except Exception as e:
        processing_status['failed'] = True
        processing_status['error'] = f'Unexpected error: {str(e)}'
        processing_status['end_time'] = datetime.now().isoformat()
        logger.error(f"Unexpected processing error: {str(e)}")
        
        if config.CLEANUP_ON_FAILURE:
            cleanup_processing_files(selected_files, parent_dir)
    finally:
        processing_status['is_processing'] = False
        os.chdir(original_dir)  # Restore original directory

def cleanup_processing_files(selected_files, parent_dir):
    """Clean up files copied to processing directory on failure"""
    try:
        for filename in selected_files:
            filepath = os.path.join(parent_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cleaned up {filename}")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(processing_status)

@app.route('/briefing', methods=['GET'])
def get_briefing():
    try:
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        briefing_path = os.path.join(parent_dir, 'pilot_briefing.txt')
        
        if not os.path.exists(briefing_path):
            logger.warning("Pilot briefing file not found")
            return jsonify({'error': 'Pilot briefing not found'}), 404
        
        with open(briefing_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            return jsonify({'error': 'Pilot briefing file is empty'}), 404
            
        return jsonify({'content': content})
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error reading briefing: {e}")
        return jsonify({'error': 'Pilot briefing file contains invalid characters'}), 500
    except Exception as e:
        logger.error(f"Error reading briefing: {e}")
        return jsonify({'error': 'Error reading pilot briefing'}), 500

@app.route('/animation/<path:filename>')
def serve_animation(filename):
    try:
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        animation_path = os.path.join(parent_dir, 'animation', filename)
        
        if not os.path.exists(animation_path):
            logger.warning(f"Animation file not found: {filename}")
            return jsonify({'error': 'Animation file not found'}), 404
            
        return send_file(animation_path)
    except Exception as e:
        logger.error(f"Error serving animation file {filename}: {e}")
        return jsonify({'error': 'Error serving animation file'}), 500

@app.route('/temp/<path:filename>')
def serve_temp(filename):
    try:
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        temp_path = os.path.join(parent_dir, 'temp', filename)
        
        if not os.path.exists(temp_path):
            logger.warning(f"Temp file not found: {filename}")
            return jsonify({'error': 'File not found'}), 404
            
        return send_file(temp_path)
    except Exception as e:
        logger.error(f"Error serving temp file {filename}: {e}")
        return jsonify({'error': 'Error serving file'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 