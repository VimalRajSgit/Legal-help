import os
import tempfile
import re
from datetime import datetime
from groq import Groq
import speech_recognition as sr
import dwani
from pydub import AudioSegment
from dotenv import load_dotenv

load_dotenv()

# Configure dwani for TTS only
dwani.api_key = 'kirannskl100@gmail.com_dwani'
dwani.api_base = 'https://dwani-dwani-api.hf.space'

class UserProcessor:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.conversation_history = []
        self.recognizer = sr.Recognizer()
        self.temp_files = []

    def transcribe_audio(self, audio_file):
        """Transcribe audio using Google Speech Recognition."""
        try:
            # Save audio file temporarily
            temp_path = os.path.join('temp', f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
            audio_file.save(temp_path)
            
            # Convert to WAV if needed
            try:
                audio = AudioSegment.from_file(temp_path)
                wav_path = temp_path.replace('.wav', '_converted.wav')
                audio.export(wav_path, format="wav")
                temp_path = wav_path
            except:
                pass  # If conversion fails, try with original file
            
            # Transcribe using speech_recognition
            with sr.AudioFile(temp_path) as source:
                audio_data = self.recognizer.record(source)
                
            # Try Google Speech Recognition first
            try:
                transcription = self.recognizer.recognize_google(audio_data, language='kn-IN')
                return transcription
            except sr.UnknownValueError:
                # Fallback to English if Kannada fails
                try:
                    transcription = self.recognizer.recognize_google(audio_data, language='en-IN')
                    return transcription
                except:
                    raise Exception("ಆಡಿಯೋ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲಾಗಲಿಲ್ಲ / Could not understand audio")
            
        except Exception as e:
            raise Exception(f"ಲಿಪ್ಯಂತರದಲ್ಲಿ ದೋಷ: {str(e)} / Transcription error: {str(e)}")
        
        finally:
            # Clean up temporary files
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass

    def extract_key_points(self, response_text):
        """Extract key points from response."""
        try:
            # Remove disclaimer section
            response_clean = response_text.split("**ನಿರಾಕರಣೆ**")[0].strip()
            
            # Split into sentences
            sentences = re.split(r'[.!?।॥]\s*', response_clean)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            # Look for numbered steps or important phrases
            key_points = []
            for sentence in sentences:
                # Check for numbered steps
                if re.match(r'^\d+\.\s', sentence):
                    key_points.append(f"• {sentence}")
                # Check for important keywords
                elif any(keyword in sentence for keyword in ["ಮುಖ್ಯ", "ಪ್ರಮುಖ", "ಗಮನಿಸಿ", "ಹಂತ", "ಮಾಡಿ"]):
                    key_points.append(f"• {sentence}")
            
            # If no specific points found, take first 2-3 sentences
            if not key_points and sentences:
                key_points = [f"• {s}" for s in sentences[:3]]
            
            return "\n".join(key_points) if key_points else "ಯಾವುದೇ ಪ್ರಮುಖ ಹಂತಗಳಿಲ್ಲ / No key points available"
            
        except Exception as e:
            return f"ಪ್ರಮುಖ ಹಂತಗಳನ್ನು ಹೊರತೆಗೆಯುವಲ್ಲಿ ದೋಷ / Error extracting key points"

    def process_query(self, query):
        """Process legal query for general users."""
        try:
            # Format conversation history
            history_text = ""
            if self.conversation_history:
                history_text = "Previous conversation:\n" + "\n".join(
                    [f"Q: {entry['query']}\nA: {entry['response']}" for entry in self.conversation_history[-2:]]
                ) + "\n\n"
            
            # Create prompt for simple explanations
            prompt = f"""
            You are a legal aid assistant for general users in Karnataka, India. 
            Provide very simple, easy-to-understand explanations in Kannada. 
            Avoid legal jargon. Use everyday language that common people can understand.
            
            {history_text}
            Current query: {query}
            
            Provide a simple, clear response in Kannada (2-3 sentences maximum):
            """
            
            # Get response from Groq
            response = self.client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {"role": "system", "content": "You are a helpful legal aid assistant. Explain legal concepts in very simple Kannada language for common people."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            
            kannada_response = response.choices[0].message.content
            
            # Add disclaimer and follow-up
            full_response = (
                f"{kannada_response}\n\n"
                "**ನಿರಾಕರಣೆ**: ಈ ಮಾಹಿತಿಯು ಸಾಮಾನ್ಯ ಜ್ಞಾನಕ್ಕಾಗಿ ಮಾತ್ರ. ಕಾನೂನು ಸಲಹೆಗಾಗಿ ವಕೀಲರನ್ನು ಸಂಪರ್ಕಿಸಿ.\n"
                "ಇನ್ನಷ್ಟು ಪ್ರಶ್ನೆಗಳಿವೆಯೇ?"
            )
            
            # Extract key points
            key_points = self.extract_key_points(full_response)
            
            # Save to history
            self.conversation_history.append({
                'query': query,
                'response': kannada_response,
                'timestamp': datetime.now().isoformat()
            })
            
            return full_response, key_points
            
        except Exception as e:
            error_msg = f"ಪ್ರಶ್ನೆ ಪ್ರಕ್ರಿಯೆಗೊಳಿಸುವಲ್ಲಿ ದೋಷ: {str(e)} / Error processing query: {str(e)}"
            return error_msg, "ದೋಷದಿಂದಾಗಿ ಪ್ರಮುಖ ಹಂತಗಳಿಲ್ಲ / No key points due to error"

    def generate_audio(self, text):
        """Generate audio using dwani TTS."""
        try:
            if not text or not text.strip():
                return None
            
            # Clean text for TTS (remove markdown and special characters)
            clean_text = text.replace('**', '').replace('*', '').split('**ನಿರಾಕರಣೆ**')[0].strip()
            
            # Generate audio using dwani
            response = dwani.Audio.speech(input=clean_text[:300], response_format="wav")
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir='temp')
            temp_file.write(response)
            temp_file.close()
            
            self.temp_files.append(temp_file.name)
            return temp_file.name
            
        except Exception as e:
            print(f"TTS Error: {e}")
            return None

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        self.cleanup_temp_files()
        return "ಸಂಭಾಷಣೆ ಇತಿಹಾಸ ತೆರವುಗೊಳಿಸಲಾಗಿದೆ / Conversation history cleared."

    def get_conversation_history(self):
        """Get conversation history."""
        return self.conversation_history

    def cleanup_temp_files(self):
        """Clean up temporary files."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        self.temp_files = []

    def __del__(self):
        self.cleanup_temp_files()
