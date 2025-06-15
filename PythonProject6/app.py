import os
import tempfile
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from groq import Groq
from gtts import gTTS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__,
            static_folder='frontend/static',
            template_folder='frontend/templates')
CORS(app)

# Supported languages for gTTS (Indian languages and fallback)
SUPPORTED_LANGUAGES = {'kn', 'hi', 'ta', 'te', 'ml', 'bn', 'gu', 'mr', 'pa', 'ur', 'en'}

class UserProcessor:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.conversation_history = []
        self.temp_files = []

    def transcribe_audio(self, audio_file):
        try:
            # Save audio file temporarily
            temp_path = os.path.join('temp', f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
            audio_file.save(temp_path)

            # Use Groq Whisper Large V3 for transcription with language detection
            with open(temp_path, "rb") as file:
                transcription_response = self.client.audio.transcriptions.create(
                    file=(temp_path, file.read()),
                    model="whisper-large-v3",
                    language=None,  # Auto-detect language
                    response_format="verbose_json"  # Get detailed response with language
                )
                transcription = transcription_response.text
                detected_language = transcription_response.language or "kn"  # Fallback to Kannada
                return transcription, detected_language

        except Exception as e:
            print(f"Transcription error details: {str(e)}")
            raise Exception(f"Transcription error: {str(e)}")

        finally:
            # Clean up temporary file
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass

    def extract_key_points(self, response_text):
        try:
            sentences = [s.strip() for s in response_text.split('. ') if s.strip()]
            key_points = []

            # Multilingual keywords for key points
            keywords = ["important", "note", "step", "must", "ಮುಖ್ಯ", "ಗಮನಿಸಿ", "ಹಂತ",  # Kannada
                        "महत्वपूर्ण", "नोट", "कदम", "जरूरी"]  # Hindi
            for sentence in sentences:
                if any(keyword.lower() in sentence.lower() for keyword in keywords):
                    key_points.append(f"• {sentence}")

            if not key_points and sentences:
                key_points = [f"• {s}" for s in sentences[:2]]

            return "\n".join(key_points) if key_points else "No key points available"

        except:
            return "Error extracting key points"

    def process_query(self, query, language="kn"):
        try:
            if language not in SUPPORTED_LANGUAGES:
                language = "kn"  # Fallback to Kannada if unsupported

            history_text = ""
            if self.conversation_history:
                history_text = "Previous conversation:\n" + "\n".join(
                    [f"Q: {entry['query']}\nA: {entry['response']}" for entry in self.conversation_history[-2:]]
                ) + "\n\n"

            prompt = f"""
            You are a legal aid assistant for general users. 
            Provide simple, easy-to-understand explanations in the language with ISO code '{language}' (e.g., 'kn' for Kannada, 'hi' for Hindi). 
            Avoid legal jargon. Use everyday language.

            {history_text}
            Current query: {query}

            Provide a simple response in the specified language (2-3 sentences maximum):
            """

            response = self.client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {"role": "system",
                     "content": f"You are a helpful legal aid assistant. Explain legal concepts in simple language with ISO code '{language}'."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )

            response_text = response.choices[0].message.content
            full_response = f"{response_text}\n\n"

            key_points = self.extract_key_points(full_response)

            self.conversation_history.append({
                'query': query,
                'response': response_text,
                'language': language,
                'timestamp': datetime.now().isoformat()
            })

            return full_response, key_points, language

        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            return error_msg, "No key points due to error", language

    def generate_audio(self, text, language="kn"):
        try:
            if not text or not text.strip():
                return None

            if language not in SUPPORTED_LANGUAGES:
                language = "kn"  # Fallback to Kannada if unsupported

            # Clean text for TTS (remove markdown and disclaimer)
            clean_text = text.replace('**', '').replace('*', '').split('**Disclaimer**')[0].strip()

            # Generate audio using gTTS
            tts = gTTS(text=clean_text, lang=language)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3", dir='temp')
            tts.save(temp_file.name)
            temp_file.close()

            self.temp_files.append(temp_file.name)
            return temp_file.name

        except Exception as e:
            print(f"TTS Error: {e}")
            return None

    def clear_history(self):
        self.conversation_history = []
        self.cleanup_temp_files()
        return "Conversation history cleared."

    def get_conversation_history(self):
        return self.conversation_history

    def cleanup_temp_files(self):
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        self.temp_files = []

    def __del__(self):
        self.cleanup_temp_files()

user_processor = UserProcessor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_file(os.path.join(app.static_folder, 'favicon.ico'), mimetype='image/vnd.microsoft.icon')

@app.route('/api/user/process_text', methods=['POST'])
def user_process_text():
    try:
        data = request.json
        query = data.get('query')
        language = data.get('language', 'kn')  # Default to Kannada if not specified

        response_text, key_points, used_language = user_processor.process_query(query, language)
        audio_path = None
        if data.get('generate_audio', True):
            audio_path = user_processor.generate_audio(response_text, used_language)

        return jsonify({
            'success': True,
            'response': response_text,
            'key_points': key_points,
            'language': used_language,
            'audio_path': audio_path,
            'history': user_processor.get_conversation_history()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user/transcribe_audio', methods=['POST'])
def user_transcribe_audio():
    try:
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': 'No audio part'}), 400

        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'success': False, 'error': 'No selected audio file'}), 400

        transcription, detected_language = user_processor.transcribe_audio(audio_file)

        return jsonify({
            'success': True,
            'transcription': transcription,
            'language': detected_language,
            'message': 'Audio transcribed successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user/clear_history', methods=['POST'])
def user_clear_history():
    try:
        message = user_processor.clear_history()
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    try:
        return send_file(filename, as_attachment=False)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'features': {
            'user_interface': True
        }
    })

if __name__ == '__main__':
    os.makedirs('temp', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5001)