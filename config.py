"""
Configuration File untuk Digital Talent Platform
Versi Simplified - Course dari Excel, Job search pakai Google CSE Embed
"""

import os

# ========================================
# DATABASE CONFIGURATION
# ========================================
EXCEL_PATH = os.path.join("data", "DTP_Database.xlsx")

# Pastikan folder data ada saat aplikasi dijalankan
os.makedirs(os.path.dirname(EXCEL_PATH), exist_ok=True)

# Nama-nama sheet di Excel
SHEET_TALENTA = "Talenta"
SHEET_PENDIDIKAN = "Riwayat_Pendidikan"
SHEET_PEKERJAAN = "Riwayat_Pekerjaan"
SHEET_SKILL = "Keterampilan_Sertifikasi"
SHEET_PON = "PON_TIK_Master"
SHEET_LOWONGAN = "Lowongan_Industri"
SHEET_HASIL = "Hasil_Pemetaan_Asesmen"
SHEET_COURSE = "Course_Maxy"  # Sheet untuk course manual

# ========================================
# 🤖 KONFIGURASI GEMINI API
# ========================================
GEMINI_API_KEY = "AIzaSyAkYKjimWX4iRbsmPpNz9FayGf-0XJ6eAY"
GEMINI_MODEL = "gemini-flash-latest"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key=API_KEY"

def get_gemini_url():
    return f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

# ========================================
# GOOGLE CUSTOM SEARCH ENGINE (untuk Job Search)
# ========================================
GOOGLE_CSE_ID = "154c28487f39940d8"  # Ganti dengan CX Anda

# Job sites yang akan di-search (opsional - untuk info saja)
JOB_SEARCH_SITES = [
    'linkedin.com/jobs',
    'jobstreet.co.id',
    'glints.com',
    'kalibrr.com',
    'indeed.com'
]

# ========================================
# MODEL CONFIGURATION
# ========================================
SEMANTIC_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Reinforcement Learning Parameters
RL_LEARNING_RATE = 0.1
RL_DISCOUNT_FACTOR = 0.9
RL_EPSILON = 0.2

# ========================================
# UI CONFIGURATION
# ========================================
APP_TITLE = "Digital Talent Platform"
APP_ICON = "🎓"
PAGE_LAYOUT = "wide"

PRIMARY_COLOR = "#667eea"
SECONDARY_COLOR = "#764ba2"

# ========================================
# FEATURE FLAGS
# ========================================
ENABLE_COURSE_RECOMMENDATION = True  # Course dari Excel
ENABLE_JOB_SEARCH_EMBED = True       # Google CSE Embed
ENABLE_SKKNI_MAPPING = True          
ENABLE_CAREER_ASSISTANT = True       
ENABLE_RL_RECOMMENDATION = True      

# ========================================
# CACHE CONFIGURATION
# ========================================
CACHE_TTL_COURSES = 3600   # 1 jam
CACHE_TTL_SKKNI = 86400    # 24 jam

# ========================================
# VALIDATION & STATUS FUNCTIONS
# ========================================
def validate_config():
    """Validasi konfigurasi saat aplikasi startup"""
    errors = []
    warnings = []
    
    # Check database
    if not os.path.exists(EXCEL_PATH):
        errors.append(f"❌ Database file tidak ditemukan di path: {EXCEL_PATH}")
    
    # Check API keys
    # Periksa apakah API key masih default atau kosong
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        warnings.append("⚠️ Gemini API key belum di-set atau masih default. Fitur Career Assistant Chat tidak akan berfungsi.")
    
    if not GOOGLE_CSE_ID or GOOGLE_CSE_ID == "YOUR_GOOGLE_CSE_ID_HERE":
        warnings.append("⚠️ Google CSE ID belum di-set atau masih default. Fitur Job Search mungkin tidak berfungsi.")
    
    return errors, warnings

def get_api_status() -> dict:
    """Check status semua service penting"""
    return {
        'database': os.path.exists(EXCEL_PATH),
        'gemini': bool(GEMINI_API_KEY) and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE",
        'google_cse': bool(GOOGLE_CSE_ID) and GOOGLE_CSE_ID != "YOUR_GOOGLE_CSE_ID_HERE"
    }
