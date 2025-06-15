import os
import tempfile
import PyPDF2
from datetime import datetime
from groq import Groq
import speech_recognition as sr
from dotenv import load_dotenv

load_dotenv()

class LawyerProcessor:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.conversation_history = []
        self.recognizer = sr.Recognizer()
        self.temp_files = []

    def extract_text_from_file(self, file_path):
        """Extract text from uploaded file (PDF or text)."""
        try:
            if not file_path or not os.path.exists(file_path):
                return "File not found."
            
            if file_path.endswith('.pdf'):
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() or ""
                    return text if text.strip() else "No text could be extracted from PDF."
            
            elif file_path.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            
            else:
                return "Unsupported file format."
        
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def save_uploaded_file(self, file):
        """Save uploaded file and return path."""
        try:
            filename = file.filename
            file_path = os.path.join('uploads', filename)
            file.save(file_path)
            return file_path
        except Exception as e:
            raise Exception(f"File upload failed: {str(e)}")

    def transcribe_audio(self, audio_file):
        """Transcribe audio using Google Speech Recognition."""
        try:
            # Save audio file temporarily
            temp_path = os.path.join('temp', f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
            audio_file.save(temp_path)
            
            # Transcribe using speech_recognition
            with sr.AudioFile(temp_path) as source:
                audio_data = self.recognizer.record(source)
                
            # Try Google Speech Recognition with English first
            try:
                transcription = self.recognizer.recognize_google(audio_data, language='en-IN')
                return transcription
            except sr.UnknownValueError:
                raise Exception("Could not understand audio")
            
        except Exception as e:
            raise Exception(f"Transcription error: {str(e)}")
        
        finally:
            # Clean up temporary files
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass

    def process_query(self, query, uploaded_file=None):
        """Process legal query for lawyers."""
        try:
            # Extract file content if provided
            file_content = ""
            if uploaded_file:
                file_content = self.extract_text_from_file(uploaded_file)
            
            # Format conversation history
            history_text = ""
            if self.conversation_history:
                history_text = "Previous conversation:\n" + "\n".join(
                    [f"Q: {entry['query']}\nA: {entry['response']}" for entry in self.conversation_history[-3:]]
                ) + "\n\n"
            
            # Create prompt
            prompt = f"""
            You are a legal aid assistant for English-speaking lawyers. Provide professional, 
            clear responses in English. Include relevant legal information and procedures.
            
            {history_text}
            Document content: {file_content[:1000] if file_content else "None"}
            
            Current query: {query}
            
            Provide a comprehensive response in English:
            """
            
            # Get response from Groq
            response = self.client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {"role": "system", "content": "You are a legal aid assistant for lawyers. Respond in English with professional legal guidance., keep the repsonses short as posiible be precise and if eexplantion is need in long then give it "},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            english_response = response.choices[0].message.content
            
            # Add disclaimer and follow-up
            full_response = (
                f"{english_response}\n\n"
                "**Disclaimer**: This information is for general guidance only. Please verify before using for legal proceedings.\n"
                "Do you have more questions?"
            )
            
            # Save to history
            self.conversation_history.append({
                'query': query,
                'response': english_response,
                'timestamp': datetime.now().isoformat()
            })
            
            return full_response
            
        except Exception as e:
            return f"Error processing query: {str(e)}"

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        self.cleanup_temp_files()
        return "Conversation history cleared."

    def get_conversation_history(self):
        """Get conversation history."""
        return self.conversation_history

    def generate_summary_report(self):
        """Generate summary report."""
        try:
            if not self.conversation_history:
                raise Exception("No conversation history")
            
            # Create summary
            summary_content = f"""
Legal Aid Assistant - Summary Report
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Conversation Summary:
{'='*50}

"""
            
            for i, entry in enumerate(self.conversation_history, 1):
                summary_content += f"""
{i}. Question:
{entry['query']}

Answer:
{entry['response']}

Time: {entry['timestamp']}
{'-'*30}
"""
            
            summary_content += f"""

**Disclaimer:**
This report is for general information only. Consult a lawyer for legal advice.
"""
            
            # Save to file
            filename = f"legal_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            file_path = os.path.join('temp', filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(summary_content)
            
            return file_path
            
        except Exception as e:
            raise Exception(f"Error generating summary: {str(e)}")

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