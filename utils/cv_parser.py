# utils/cv_parser.py
"""
CV Parsing & Text Extraction Utilities
"""

import re
import io
import docx
from PyPDF2 import PdfReader

def extract_text_from_pdf(file_io):
    """Ekstrak teks dari PDF"""
    try:
        reader = PdfReader(file_io)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        raise Exception(f"Error extracting PDF: {e}")

def extract_text_from_docx(file_io):
    """Ekstrak teks dari DOCX"""
    try:
        doc = docx.Document(file_io)
        text = "\n".join([p.text for p in doc.paragraphs if p.text])
        return text
    except Exception as e:
        raise Exception(f"Error extracting DOCX: {e}")

def parse_cv_data(cv_text):
    """
    Parse CV text untuk ekstrak informasi penting
    Returns: dict dengan email, nama, linkedin, lokasi, cv_text
    """
    data = {
        "email": "",
        "nama": "",
        "linkedin": "",
        "lokasi": "",
        "cv_text": cv_text
    }
    
    # Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', cv_text)
    if email_match:
        data["email"] = email_match.group(0)
    
    # LinkedIn
    linkedin_match = re.search(
        r'linkedin\.com/in/([\w-]+)', 
        cv_text, 
        re.IGNORECASE
    )
    if linkedin_match:
        data["linkedin"] = f"https://www.linkedin.com/in/{linkedin_match.group(1)}"
    
    # Nama (heuristik: baris pertama)
    lines = cv_text.split('\n')
    for line in lines:
        line = line.strip()
        if line and '@' not in line and len(line.split()) < 5:
            data["nama"] = line.title()
            break
    
    # Lokasi
    cities = [
        'Jakarta', 'Bandung', 'Surabaya', 'Yogyakarta', 'Jogja',
        'Medan', 'Semarang', 'Makassar', 'Denpasar', 'Palembang',
        'Tangerang', 'Bekasi', 'Depok', 'Bogor'
    ]
    
    for city in cities:
        if re.search(city, cv_text, re.IGNORECASE):
            data["lokasi"] = city if city != "Jogja" else "Yogyakarta"
            break
    
    return data

def extract_skill_tokens(text: str) -> list:
    """
    Ekstrak skill tokens dari text
    Split by comma, slash, pipe, semicolon
    """
    if not isinstance(text, str):
        return []
    
    text = text.lower().strip()
    
    # Split by common delimiters
    parts = re.split(r'[,;/\\|]+', text)
    
    # Clean and deduplicate
    tokens = []
    seen = set()
    for part in parts:
        part = part.strip()
        if part and part not in seen:
            tokens.append(part)
            seen.add(part)
    
    return tokens

def normalize_text(text: str) -> str:
    """Normalize text untuk matching"""
    if not isinstance(text, str):
        return ""
    
    # Remove non-breaking spaces
    text = text.replace('\xa0', ' ')
    
    # Remove control characters
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
    
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    
    return text