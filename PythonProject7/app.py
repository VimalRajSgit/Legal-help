import os
import base64
import time
import logging
import re
from datetime import datetime
from groq import Groq, DefaultHttpxClient
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_file, flash, redirect, url_for, session
from flask_wtf import FlaskForm
from wtforms import TextAreaField, FileField, SubmitField
from wtforms.validators import DataRequired
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import json
import PyPDF2
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Replace with a secure key
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

load_dotenv()

# Initialize Groq client with a custom HTTP client
client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
    http_client=DefaultHttpxClient(
        timeout=20.0  # Set a reasonable timeout
    )
)

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png'}
ALLOWED_PDF_EXTENSIONS = {'pdf'}


# Flask-WTF Form
class LetterForm(FlaskForm):
    details_text = TextAreaField('Details / ವಿವರಗಳು / विवरण')
    details_file = FileField('Upload Details (Image or PDF) / ವಿವರಗಳನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ / विवरण अपलोड करें')
    submit = SubmitField('Generate Letter / ಪತ್ರ ರಚಿಸಿ / पत्र उत्पन्न करें')

    def validate(self):
        # Call the parent validation
        if not super(LetterForm, self).validate():
            return False

        # Custom validation: ensure at least one of details_text or details_file is provided
        if not self.details_text.data and not self.details_file.data:
            self.details_text.errors.append('Please provide either text details or upload a file.')
            self.details_file.errors.append('Please provide either text details or upload a file.')
            return False
        return True


def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def encode_image(file_path):
    try:
        file_size = os.path.getsize(file_path) / 1024  # Size in KB
        logger.debug(f"Image size: {file_size:.2f} KB")
        if file_size > 4096:  # 4MB limit for base64-encoded images
            raise Exception("Image size exceeds 4MB limit for base64-encoded images")

        with open(file_path, 'rb') as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        return base64_image
    except Exception as e:
        logger.error(f"Image encoding error: {str(e)}")
        raise Exception(f"Image encoding error: {str(e)}")


def extract_text_from_file(file_path, is_pdf=False):
    try:
        if is_pdf:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted
                if not text.strip():
                    raise Exception(
                        "No text could be extracted from the PDF. Please ensure the PDF contains readable text (e.g., Name: Anil Sharma, Location: Bengaluru, Subject: Water Issue).")
                logger.debug(f"Extracted text from PDF: {text}")
                return text.strip()
        else:
            base64_image = encode_image(file_path)
            logger.debug(f"Base64 encoded image length: {len(base64_image)}")  # Debug the encoded image
            try:
                response = client.chat.completions.create(
                    model="meta-llama/llama-4-maverick-17b-128e-instruct",  # Use a vision-capable model (update if needed)
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Extract all visible text from this image accurately, preserving the format as closely as possible (e.g., 'Name: Anil Sharma' or 'Name Anil Sharma'). Do not interpret or modify the text; return only the raw text."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=500,
                    temperature=0.5
                )
                extracted_text = response.choices[0].message.content.strip()
                logger.debug(f"Extracted text from image: {extracted_text}")
                if not extracted_text:
                    raise Exception(
                        "No text could be extracted from the image. Please ensure the image contains readable text (e.g., Name: Anil Sharma, Location: Bengaluru, Subject: Water Issue).")
                return extracted_text
            except Exception as api_error:
                logger.error(f"Groq API error: {str(api_error)}")
                raise Exception(f"Failed to extract text from image: {str(api_error)}")
    except Exception as e:
        logger.error(f"Text extraction error: {str(e)}")
        raise Exception(f"Text extraction error: {str(e)}")


def infer_department_and_designation(subject):
    subject = subject.lower()
    if "hand" in subject or "health" in subject:
        return "Health Officer", "Health Department"
    elif "water" in subject:
        return "Water Supply Officer", "Water Department"
    elif "land" in subject:
        return "Revenue Officer", "Revenue Department"
    else:
        return "Relevant Authority", "Relevant Department"


def infer_location_details(location):
    location = location.lower().strip()
    state = "Unknown"
    pin_code = "Unknown"
    city = "Unknown"
    if "bengaluru" in location or "bangalore" in location:
        state = "Karnataka"
        city = "Bengaluru"
        if "begur" in location:
            pin_code = "560068"
        elif "koramangala" in location:
            pin_code = "560034"
        elif "jayanagar" in location:
            pin_code = "560011"
        else:
            pin_code = "560001"
    return city, state, pin_code


def process_extracted_text(text):
    try:
        if not text.strip():
            logger.warning("Empty text provided, returning default fields")
            raise Exception(
                "Empty text provided. Please provide details in the text box or upload a file with readable text (e.g., Name: Anil Sharma, Location: Bengaluru, Subject: Water Issue).")
        prompt = f"""
        You are a text processor and translator. Your task is to analyze the following text, translate it to English if it's in another language (e.g., Kannada, Hindi), and structure it into a JSON object with the specified fields. Use placeholders for missing information.

        Fields to extract:
        {{
            "Full Name": "[Extracted or 'Unknown']",
            "Address": "[Extracted or 'Unknown']",
            "City, State, PIN Code": "[Extracted or 'Unknown']",
            "Mobile Number": "[Extracted or 'Unknown']",
            "Officer Designation": "[Extracted or 'Relevant Authority']",
            "Department Name": "[Extracted or 'Relevant Department']",
            "Office Address": "[Extracted or 'Office of Relevant Department']",
            "Office City, State, PIN Code": "[Extracted or 'Unknown']",
            "Subject": "[Extracted or 'Request for Assistance']",
            "Parent/Spouse Name": "[Extracted or 'Unknown']",
            "Enclosures": "[List of documents, comma-separated, or 'None']",
            "Raw Extracted Text": "[The raw input text]"
        }}

        The text may be in English or another language, and the format may vary (e.g., "Name: Ravi Kumar, Location: Bangalore", "Name Ravi Kumar Location Bangalore", or "Name - Ravi Kumar"). Extract the fields even if the format is inconsistent. Look for keywords like "Name", "Location", "Phone", "Subject" (case-insensitive), and handle variations in separators (e.g., ":", "-", or spaces). Also look for "S/o", "D/o", or "W/o" to extract "Parent/Spouse Name". If the mobile number is not 10 digits, mark it as "Invalid Mobile Number: [number]". Capitalize the first letter of each word in the "Subject" field. Look for keywords like "Enclosure", "Document", or "Attachment" to extract a list of documents. If the subject or content contains terms like "hand issue" that seem unrelated to legal matters, correct them to more appropriate terms like "land issue".

        Examples:
        - Input: "Name: Ravi Kumar, Location: Begur, Bengaluru, Phone: 9876543210, Subject: Land Issue, S/o Kumar, Enclosure: Aadhar Card, Land Deed"
          Output: {{"Full Name": "Ravi Kumar", "Address": "Begur, Bengaluru", "City, State, PIN Code": "Bengaluru, Karnataka, 560068", "Mobile Number": "9876543210", "Officer Designation": "Revenue Officer", "Department Name": "Revenue Department", "Office Address": "Office of Revenue Department", "Office City, State, PIN Code": "Bengaluru, Karnataka, 560068", "Subject": "Land Issue", "Parent/Spouse Name": "Kumar", "Enclosures": "Aadhar Card, Land Deed", "Raw Extracted Text": "Name: Ravi Kumar, Location: Begur, Bengaluru, Phone: 9876543210, Subject: Land Issue, S/o Kumar, Enclosure: Aadhar Card, Land Deed"}}
        - Input: "Name: Virat Kohli, Location: Bengaluru, Phone: 93358393, Subject: hand Problems"
          Output: {{"Full Name": "Virat Kohli", "Address": "Bengaluru", "City, State, PIN Code": "Bengaluru, Karnataka, 560001", "Mobile Number": "Invalid Mobile Number: 93358393", "Officer Designation": "Revenue Officer", "Department Name": "Revenue Department", "Office Address": "Office of Revenue Department", "Office City, State, PIN Code": "Bengaluru, Karnataka, 560001", "Subject": "Land Problems", "Parent/Spouse Name": "Unknown", "Enclosures": "None", "Raw Extracted Text": "Name: Virat Kohli, Location: Bengaluru, Phone: 93358393, Subject: hand Problems"}}

        Text: {text}

        **Important**: Return *only* a valid JSON string. Do not include any explanation, reasoning, or additional text before or after the JSON. Ensure the JSON is properly formatted and complete.
        """
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="meta-llama/llama-4-maverick-17b-128e-instruct",
                    messages=[
                        {"role": "system",
                         "content": "You are a text processor and translator. Return only a valid JSON string, with no additional text or explanation."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.5
                )
                raw_response = response.choices[0].message.content.strip()
                logger.debug(f"Raw API response: {raw_response}")
                if not raw_response:
                    raise Exception("Empty API response")
                try:
                    fields = json.loads(raw_response)
                    logger.debug(f"Processed fields: {fields}")
                    officer, dept = infer_department_and_designation(fields.get("Subject", ""))
                    fields["Officer Designation"] = officer
                    fields["Department Name"] = dept
                    location = fields.get("Address", "Unknown")
                    city, state, pin_code = infer_location_details(location)
                    if fields["City, State, PIN Code"] == "Unknown":
                        fields["City, State, PIN Code"] = f"{city}, {state}, {pin_code}"
                    if fields["Office City, State, PIN Code"] == "Unknown":
                        fields["Office City, State, PIN Code"] = f"{city}, {state}, {pin_code}"
                    fields["Office Address"] = f"Office of {dept}"
                    all_defaults = all(value in ["Unknown", "Relevant Authority", "Relevant Department",
                                                 "Office of Relevant Department", "Request for Assistance", "None"] for
                                       key, value in fields.items() if key != "Raw Extracted Text")
                    if all_defaults:
                        logger.warning("All fields are defaults, possible processing failure")
                    return fields
                except json.JSONDecodeError as je:
                    logger.error(f"JSON decode error: {str(je)}")
                    json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        logger.debug(f"Extracted JSON string from response: {json_str}")
                        try:
                            fields = json.loads(json_str)
                            officer, dept = infer_department_and_designation(fields.get("Subject", ""))
                            fields["Officer Designation"] = officer
                            fields["Department Name"] = dept
                            location = fields.get("Address", "Unknown")
                            city, state, pin_code = infer_location_details(location)
                            if fields["City, State, PIN Code"] == "Unknown":
                                fields["City, State, PIN Code"] = f"{city}, {state}, {pin_code}"
                            if fields["Office City, State, PIN Code"] == "Unknown":
                                fields["Office City, State, PIN Code"] = f"{city}, {state}, {pin_code}"
                            fields["Office Address"] = f"Office of {dept}"
                            logger.debug(f"Processed fields after regex: {fields}")
                            return fields
                        except json.JSONDecodeError as je2:
                            logger.error(f"Failed to parse extracted JSON: {str(je2)}")
                    return {
                        "Full Name": "Unknown",
                        "Address": "Unknown",
                        "City, State, PIN Code": "Unknown",
                        "Mobile Number": "Unknown",
                        "Officer Designation": "Relevant Authority",
                        "Department Name": "Relevant Department",
                        "Office Address": "Office of Relevant Department",
                        "Office City, State, PIN Code": "Unknown",
                        "Subject": "Request for Assistance",
                        "Parent/Spouse Name": "Unknown",
                        "Enclosures": "None",
                        "Raw Extracted Text": text
                    }
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if "rate_limit_exceeded" in str(e) or "413" in str(e):
                    if attempt < 2:
                        time.sleep(10)
                        continue
                raise e
        raise Exception("Processing failed after retries")
    except Exception as e:
        logger.error(f"Text processing error: {str(e)}")
        return {
            "Full Name": "Unknown",
            "Address": "Unknown",
            "City, State, PIN Code": "Unknown",
            "Mobile Number": "Unknown",
            "Officer Designation": "Relevant Authority",
            "Department Name": "Relevant Department",
            "Office Address": "Office of Relevant Department",
            "Office City, State, PIN Code": "Unknown",
            "Subject": "Request for Assistance",
            "Parent/Spouse Name": "Unknown",
            "Enclosures": "None",
            "Raw Extracted Text": text
        }


def generate_issue_description(full_name, subject):
    try:
        prompt = f"""
        You are an expert in drafting formal legal letters. Based on the provided Full Name and Subject, generate a 1–2 paragraph issue description for a legal letter. The description should be formal, concise, and relevant to a legal context. Ensure the tone is respectful and appropriate for addressing an authority. If the subject contains terms that seem unrelated to legal matters (e.g., "hand issue"), correct them to more appropriate terms (e.g., "land issue"). Do not include any additional explanations or text beyond the issue description.

        Full Name: {full_name}
        Subject: {subject}

        Example:
        - Full Name: Ravi Kumar, Subject: Land Issue
          Output: I am writing to seek your assistance regarding a land issue that has been affecting my property in recent months. There has been a dispute over the boundary lines of my land, which has led to conflicts with neighboring landowners, and I have been unable to resolve this matter independently. I kindly request your intervention to review the relevant documents and provide guidance on how to proceed with this issue.
        """
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="meta-llama/llama-4-maverick-17b-128e-instruct",
                    messages=[
                        {"role": "system",
                         "content": "You are an expert in drafting formal legal letters. Return only the issue description, with no additional text or explanation."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=150,
                    temperature=0.5
                )
                issue_description = response.choices[0].message.content.strip()
                logger.debug(f"Generated issue description: {issue_description}")
                if not issue_description:
                    raise Exception("Empty issue description generated")
                return issue_description
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if "rate_limit_exceeded" in str(e) or "413" in str(e):
                    if attempt < 2:
                        time.sleep(10)
                        continue
                raise e
        raise Exception("Issue description generation failed after retries")
    except Exception as e:
        logger.error(f"Issue description generation error: {str(e)}")
        return "I am writing to seek your assistance regarding the aforementioned matter, as I require guidance to resolve this issue promptly."


def generate_pdf(fields, output_path):
    try:
        logger.debug(f"Generating PDF with fields: {fields}")
        doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=1 * inch, rightMargin=1 * inch, topMargin=1 * inch,
                                bottomMargin=1 * inch)
        styles = getSampleStyleSheet()
        normal = styles['Normal']
        normal.fontName = 'Helvetica'
        heading = ParagraphStyle(name='Heading', parent=normal, fontSize=12, fontName='Helvetica-Bold')
        small = ParagraphStyle(name='Small', parent=normal, fontSize=8)
        story = []

        story.append(Paragraph(str(fields['Full Name']), normal))
        story.append(Paragraph(str(fields['Address']), normal))
        story.append(Paragraph(str(fields['City, State, PIN Code']), normal))
        story.append(Paragraph(f"Mobile Number: {str(fields['Mobile Number'])}", normal))
        story.append(Spacer(1, 0.5 * inch))

        current_date = datetime.now().strftime("%d/%m/%Y")
        story.append(Paragraph(f"Date: {current_date}", normal))
        story.append(Spacer(1, 0.5 * inch))

        story.append(Paragraph("To", normal))
        story.append(Paragraph(f"The {str(fields['Officer Designation'])}", normal))
        story.append(Paragraph(str(fields['Department Name']), normal))
        story.append(Paragraph(str(fields['Office Address']), normal))
        story.append(Paragraph(str(fields['Office City, State, PIN Code']), normal))
        story.append(Spacer(1, 0.5 * inch))

        story.append(Paragraph(f"Subject: {str(fields['Subject'])}", heading))
        story.append(Spacer(1, 0.5 * inch))

        story.append(Paragraph("Respected Sir/Madam,", normal))
        story.append(Spacer(1, 0.2 * inch))

        full_address = f"{fields['Address']}, {fields['City, State, PIN Code']}"
        story.append(Paragraph(
            f"I, {str(fields['Full Name'])}, son/daughter/wife of {str(fields['Parent/Spouse Name'])}, "
            f"residing at {full_address}, would like to bring to your kind notice the following:",
            normal
        ))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(str(fields['Issue Description']), normal))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(
            "I kindly request you to take necessary action on the above-mentioned matter at the earliest.",
            normal
        ))
        story.append(Spacer(1, 0.2 * inch))

        enclosures = fields.get("Enclosures", "None")
        if enclosures != "None":
            story.append(
                Paragraph("I am enclosing the following documents for your reference and further processing:", normal))
            story.append(Spacer(1, 0.1 * inch))
            for doc in enclosures.split(","):
                story.append(Paragraph(f"- {doc.strip()}", normal))
            story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(
            "I would be grateful for your prompt attention to this matter. "
            "Please feel free to contact me for any further clarification or additional documentation.",
            normal
        ))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph("Thanking you,", normal))
        story.append(Paragraph("Yours faithfully,", normal))
        story.append(Paragraph(str(fields['Full Name']), normal))
        story.append(Spacer(1, 0.5 * inch))

        story.append(Paragraph("--- Debug Info ---", small))
        story.append(Paragraph(f"Raw Extracted Text: {str(fields['Raw Extracted Text'])}", small))

        doc.build(story)
        logger.debug(f"PDF generated successfully at {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"PDF generation error: {str(e)}")
        raise Exception(f"PDF generation error: {str(e)}")


# Language-specific translations
translations = {
    'en': {
        'title': 'Legal Letter Generator',
        'subtitle': 'Generate formal letters to legal offices',
        'details_label': 'Enter Details (e.g., Name, Location, Phone, Subject)',
        'upload_label': 'Or Upload Details (Image or PDF)',
        'submit': 'Generate Letter',
        'samples': 'View Sample Letters',
        'success': 'Letter generated successfully! Click below to download.',
        'error': 'Error: {}'
    },
    'kn': {
        'title': 'ಕಾನೂನು ಪತ್ರ ಜನರೇಟರ್',
        'subtitle': 'ಕಾನೂನು ಕಚೇರಿಗಳಿಗೆ ಔಪಚಾರಿಕ ಪತ್ರಗಳನ್ನು ರಚಿಸಿ',
        'details_label': 'ವಿವರಗಳನ್ನು ನಮೂದಿಸಿ (ಉದಾ., ಹೆಸರು, ಸ್ಥಳ, ಫೋನ್, ವಿಷಯ)',
        'upload_label': 'ಅಥವಾ ವಿವರಗಳನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ (ಚಿತ್ರ ಅಥವಾ PDF)',
        'submit': 'ಪತ್ರ ರಚಿಸಿ',
        'samples': 'ಮಾದರಿ ಪತ್ರಗಳನ್ನು ನೋಡಿ',
        'success': 'ಪತ್ರವನ್ನು ಯಶಸ್ವಿಯಾಗಿ ರಚಿಸಲಾಗಿದೆ! ಡೌನ್‌ಲೋಡ್ ಮಾಡಲು ಕೆಳಗೆ ಕ್ಲಿಕ್ ಮಾಡಿ.',
        'error': 'ದೋಷ: {}'
    },
    'hi': {
        'title': 'कानूनी पत्र जेनरेटर',
        'subtitle': 'कानूनी कार्यालयों के लिए औपचारिक पत्र उत्पन्न करें',
        'details_label': 'विवरण दर्ज करें (उदा., नाम, स्थान, फोन, विषय)',
        'upload_label': 'या विवरण अपलोड करें (छवि या PDF)',
        'submit': 'पत्र उत्पन्न करें',
        'samples': 'नमूना पत्र देखें',
        'success': 'पत्र सफलतापूर्वक उत्पन्न हुआ! डाउनलोड करने के लिए नीचे क्लिक करें।',
        'error': 'त्रुटि: {}'
    }
}

# Instructions for the guidance section
instructions = {
    'en': {
        'how_to_provide': 'You can either type your details in the text box below or upload an image/PDF. Your details should include information like:',
        'example_name': 'Name (e.g., Name: Anil Sharma)',
        'example_location': 'Location (e.g., Location: Bengaluru)',
        'example_phone': 'Phone Number (e.g., Phone: 9876543210)',
        'example_subject': 'Subject (e.g., Subject: Water Issue)',
        'example_image_prompt': 'Here’s an example of what your uploaded image or PDF should look like:',
        'placeholder': 'e.g., Name: Ravi Kumar, Location: Bengaluru, Phone: 9876543210, Subject: Land Issue',
        'tooltip': 'Upload an image or PDF with details like: Name, Location, Phone, Subject'
    },
    'kn': {
        'how_to_provide': 'ನೀವು ಕೆಳಗಿನ ಟೆಕ್ಸ್ಟ್ ಬಾಕ್ಸ್‌ನಲ್ಲಿ ವಿವರಗಳನ್ನು ಟೈಪ್ ಮಾಡಬಹುದು ಅಥವಾ ಚಿತ್ರ/PDF ಅಪ್‌ಲೋಡ್ ಮಾಡಬಹುದು. ನಿಮ್ಮ ವಿವರಗಳಲ್ಲಿ ಈ ಮಾಹಿತಿ ಇರಬೇಕು:',
        'example_name': 'ಹೆಸರು (ಉದಾ., ಹೆಸರು: ಅನಿಲ್ ಶರ್ಮಾ)',
        'example_location': 'ಸ್ಥಳ (ಉದಾ., ಸ್ಥಳ: ಬೆಂಗಳೂರು)',
        'example_phone': 'ಫೋನ್ ಸಂಖ್ಯೆ (ಉದಾ., ಫೋನ್: 9876543210)',
        'example_subject': 'ವಿಷಯ (ಉದಾ., ವಿಷಯ: ನೀರಿನ ಸಮಸ್ಯೆ)',
        'example_image_prompt': 'ನೀವು ಅಪ್‌ಲೋಡ್ ಮಾಡುವ ಚಿತ್ರ ಅಥವಾ PDF ಹೀಗಿರಬೇಕು ಎಂಬ ಉದಾಹರಣೆ ಇಲ್ಲಿದೆ:',
        'placeholder': 'ಉದಾ., ಹೆಸರು: ರವಿ ಕುಮಾರ್, ಸ್ಥಳ: ಬೆಂಗಳೂರು, ಫೋನ್: 9876543210, ವಿಷಯ: ಭೂಮಿ ಸಮಸ್ಯೆ',
        'tooltip': 'ಹೆಸರು, ಸ್ಥಳ, ಫೋನ್, ವಿಷಯದಂತಹ ವಿವರಗಳೊಂದಿಗೆ ಚಿತ್ರ ಅಥವಾ PDF ಅಪ್‌ಲೋಡ್ ಮಾಡಿ'
    },
    'hi': {
        'how_to_provide': 'आप नीचे दिए गए टेक्स्ट बॉक्स में अपनी जानकारी टाइप कर सकते हैं या एक छवि/PDF अपलोड कर सकते हैं। आपकी जानकारी में निम्नलिखित शामिल होना चाहिए:',
        'example_name': 'नाम (उदा., नाम: अनिल शर्मा)',
        'example_location': 'स्थान (उदा., स्थान: बेंगलुरु)',
        'example_phone': 'फोन नंबर (उदा., फोन: 9876543210)',
        'example_subject': 'विषय (उदा., विषय: जल समस्या)',
        'example_image_prompt': 'यहां एक उदाहरण है कि आपकी अपलोड की गई छवि या PDF कैसी दिखनी चाहिए:',
        'placeholder': 'उदा., नाम: रवि कुमार, स्थान: बेंगलुरु, फोन: 9876543210, विषय: भूमि समस्या',
        'tooltip': 'नाम, स्थान, फोन, विषय जैसी जानकारी के साथ एक छवि या PDF अपलोड करें'
    }
}

# Sample page translations
sample_translations = {
    'en': {
        'title': 'Sample Letters',
        'subtitle': 'Open sample letters in different languages',
        'english': 'Open English Sample Letter',
        'kannada': 'Open Kannada Sample Letter',
        'hindi': 'Open Hindi Sample Letter',
        'back': 'Back to Home'
    },
    'kn': {
        'title': 'ಮಾದರಿ ಪತ್ರಗಳು',
        'subtitle': 'ವಿವಿಧ ಭಾಷೆಗಳಲ್ಲಿ ಮಾದರಿ ಪತ್ರಗಳನ್ನು ತೆರೆಯಿರಿ',
        'english': 'ಇಂಗ್ಲಿಷ್ ಮಾದರಿ ಪತ್ರವನ್ನು ತೆರೆಯಿರಿ',
        'kannada': 'ಕನ್ನಡ ಮಾದರಿ ಪತ್ರವನ್ನು ತೆರೆಯಿರಿ',
        'hindi': 'ಹಿಂದಿ ಮಾದರಿ ಪತ್ರವನ್ನು ತೆರೆಯಿರಿ',
        'back': 'ಮುಖಪುಟಕ್ಕೆ ಹಿಂತಿರುಗಿ'
    },
    'hi': {
        'title': 'नमूना पत्र',
        'subtitle': 'विभिन्न भाषाओं में नमूना पत्र खोलें',
        'english': 'अंग्रेजी नमूना पत्र खोलें',
        'kannada': 'कन्नड़ नमूना पत्र खोलें',
        'hindi': 'हिंदी नमूना पत्र खोलें',
        'back': 'होम पर वापस जाएं'
    }
}

# Language display names for the navbar dropdown
language_display_names = {
    'en': 'English',
    'kn': 'Kannada / ಕನ್ನಡ',
    'hi': 'Hindi / हिंदी'
}


@app.route('/set_language', methods=['POST'])
def set_language():
    language = request.form.get('language', 'en')
    if language in ['en', 'kn', 'hi']:
        session['language'] = language
    return redirect(request.referrer or url_for('index'))


@app.route('/', methods=['GET', 'POST'])
def index():
    form = LetterForm()
    # Get language from session, default to 'en' if not set
    language = session.get('language', 'en')

    # Update language display for the navbar
    language_display = language_display_names.get(language, 'English')

    if request.method == 'POST' and form.validate():
        try:
            details_text = form.details_text.data
            details_file = form.details_file.data

            # Process text input if provided
            if details_text and details_text.strip():
                extracted_text = details_text
            # Process file input if provided
            elif details_file:
                filename = secure_filename(details_file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                details_file.save(file_path)

                is_pdf = allowed_file(filename, ALLOWED_PDF_EXTENSIONS)
                if not (is_pdf or allowed_file(filename, ALLOWED_IMAGE_EXTENSIONS)):
                    flash(translations[language]['error'].format(
                        "Invalid file type. Please upload a .jpg, .png, or .pdf file."), 'danger')
                    return redirect(url_for('index'))

                extracted_text = extract_text_from_file(file_path, is_pdf)
                os.remove(file_path)  # Clean up uploaded file
            else:
                # This should not happen due to form validation, but included for safety
                flash(
                    translations[language]['error'].format("No details provided. Please enter text or upload a file."),
                    'danger')
                return redirect(url_for('index'))

            fields = process_extracted_text(extracted_text)
            issue_description = generate_issue_description(fields["Full Name"], fields["Subject"])
            fields["Issue Description"] = issue_description

            output_filename = f"letter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            pdf_path = generate_pdf(fields, output_path)

            flash(translations[language]['success'], 'success')
            return send_file(pdf_path, as_attachment=True, download_name=output_filename)

        except Exception as e:
            logger.error(f"Error generating letter: {str(e)}")
            # Customize error messages to be more user-friendly
            error_message = str(e)
            if "No text could be extracted" in error_message:
                error_message = f"{error_message} You can refer to the example image above for the correct format."
            elif "Image size exceeds" in error_message:
                error_message = "The uploaded file is too large (max 4MB). Please upload a smaller image or PDF."
            elif "Invalid file type" in error_message:
                error_message = "Invalid file type. Please upload a .jpg, .png, or .pdf file."
            flash(translations[language]['error'].format(error_message), 'danger')
            return redirect(url_for('index'))

    return render_template('index.html', form=form, translations=translations[language],
                           instructions=instructions[language], language=language, language_display=language_display)


@app.route('/samples')
def samples():
    # Get language from session, default to 'en' if not set
    language = session.get('language', 'en')

    # Update language display for the navbar
    language_display = language_display_names.get(language, 'English')

    return render_template('samples.html', translations=sample_translations[language], language=language,
                           language_display=language_display)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)