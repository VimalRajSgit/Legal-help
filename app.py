import os
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import sys
from flask_cors import CORS
import json

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Import backend components
from backend.lawyer import LawyerProcessor
from backend.legal_aid_locator import LegalAidLocator
from backend.offline_pwa_mode import OfflinePWAMode

app = Flask(__name__, 
            static_folder='frontend/static',
            template_folder='frontend/templates')

# Enable CORS for API endpoints
CORS(app)

# Initialize processors
lawyer_processor = LawyerProcessor()
legal_aid_locator = LegalAidLocator()
offline_pwa_mode = OfflinePWAMode()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/lawyer')
def lawyer():
    return render_template('lawyer.html')

@app.route('/legal-aid-locator')
def legal_aid_locator_page():
    return render_template('legal_aid_locator.html')

@app.route('/offline')
def offline():
    return render_template('offline.html')

# PWA Routes
@app.route('/manifest.json')
def manifest():
    return send_from_directory('frontend/static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('frontend/static', 'sw.js')

@app.route('/offline.html')
def offline_page():
    return render_template('offline.html')

# API endpoints for lawyer interface
@app.route('/api/lawyer/process_text', methods=['POST'])
def lawyer_process_text():
    try:
        data = request.json
        query = data.get('query')
        uploaded_file = data.get('file_path')
        
        # Process query
        response_text = lawyer_processor.process_query(query, uploaded_file)
        
        return jsonify({
            'success': True,
            'response': response_text,
            'history': lawyer_processor.get_conversation_history()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/lawyer/upload_file', methods=['POST'])
def lawyer_upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400
        
        # Save and process the file
        file_path = lawyer_processor.save_uploaded_file(file)
        
        return jsonify({
            'success': True,
            'file_path': file_path,
            'message': 'File uploaded successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/lawyer/transcribe_audio', methods=['POST'])
def lawyer_transcribe_audio():
    try:
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': 'No audio part'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'success': False, 'error': 'No selected audio file'}), 400
        
        # Transcribe the audio
        transcription = lawyer_processor.transcribe_audio(audio_file)
        
        return jsonify({
            'success': True,
            'transcription': transcription,
            'message': 'Audio transcribed successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/lawyer/clear_history', methods=['POST'])
def lawyer_clear_history():
    try:
        message = lawyer_processor.clear_history()
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/lawyer/generate_summary', methods=['POST'])
def lawyer_generate_summary():
    try:
        file_path = lawyer_processor.generate_summary_report()
        return jsonify({
            'success': True,
            'file_path': file_path,
            'message': 'Summary report generated successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# API endpoints for legal aid locator
@app.route('/api/legal-aid/search', methods=['POST'])
def search_legal_aid():
    try:
        data = request.json
        location = data.get('location')
        legal_type = data.get('legal_type', 'general')
        radius = data.get('radius', 10)
        
        results = legal_aid_locator.search_nearby_legal_aid(location, legal_type, radius)
        
        return jsonify({
            'success': True,
            'results': results,
            'total_found': len(results)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/legal-aid/get-coordinates', methods=['POST'])
def get_coordinates():
    try:
        data = request.json
        location = data.get('location')
        
        coordinates = legal_aid_locator.get_coordinates(location)
        
        return jsonify({
            'success': True,
            'coordinates': coordinates
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/legal-aid/get-directions', methods=['POST'])
def get_directions():
    try:
        data = request.json
        start_location = data.get('start_location')
        end_location = data.get('end_location')
        
        directions = legal_aid_locator.get_directions(start_location, end_location)
        
        return jsonify({
            'success': True,
            'directions': directions
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# API endpoints for offline PWA mode
@app.route('/api/offline/cache-data', methods=['POST'])
def cache_offline_data():
    try:
        data = request.json
        conversation_data = data.get('conversation_data')
        user_preferences = data.get('user_preferences')
        
        result = offline_pwa_mode.cache_conversation_data(conversation_data, user_preferences)
        
        return jsonify({
            'success': True,
            'message': 'Data cached successfully',
            'cache_size': result.get('cache_size', 0)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/offline/get-cached-data', methods=['GET'])
def get_cached_data():
    try:
        cached_data = offline_pwa_mode.get_cached_data()
        
        return jsonify({
            'success': True,
            'data': cached_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/offline/process-offline-query', methods=['POST'])
def process_offline_query():
    try:
        data = request.json
        query = data.get('query')
        
        response = offline_pwa_mode.process_offline_query(query)
        
        return jsonify({
            'success': True,
            'response': response,
            'is_offline': True
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/offline/sync-data', methods=['POST'])
def sync_offline_data():
    try:
        data = request.json
        offline_conversations = data.get('offline_conversations', [])
        
        result = offline_pwa_mode.sync_offline_data(offline_conversations)
        
        return jsonify({
            'success': True,
            'synced_count': result.get('synced_count', 0),
            'message': 'Data synced successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# File serving routes
@app.route('/audio/<path:filename>')
def serve_audio(filename):
    try:
        return send_file(filename, as_attachment=False)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# Health check endpoint
@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'features': {
            'lawyer_interface': True,
            'legal_aid_locator': True,
            'offline_pwa': True
        }
    })

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('temp', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('cache', exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)