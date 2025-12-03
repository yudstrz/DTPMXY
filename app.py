import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import re
import pickle
import traceback
from datetime import datetime

# Document processing
from PyPDF2 import PdfReader
import docx

# AI & ML
import faiss
from sentence_transformers import SentenceTransformer

# ========================================
# IMPORT CONFIGURATION
# ========================================
try:
    from config import (
        EXCEL_PATH, SHEET_PON, SHEET_TALENTA, SHEET_COURSE,
        GOOGLE_CSE_ID, GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL,
        validate_config, get_api_status
    )
    CONFIG_LOADED = True
except ImportError as e:
    st.error(f"❌ File `config.py` tidak ditemukan atau ada error: {e}")
    st.error("Aplikasi tidak dapat berjalan tanpa file konfigurasi.")
    st.stop()

# ========================================
# IMPORT UTILS
# ========================================
UTILS_LOADED = False
try:
    from utils.skkni_matcher import (
        create_skkni_matcher,
        display_learning_path,
        display_skill_gap_chart
    )
    UTILS_LOADED = True
except ImportError:
    st.warning("⚠️ Modul `utils` tidak ditemukan. Beberapa fitur lanjutan mungkin tidak tersedia.")

# ========================================
# IMPORT CHATBOT
# ========================================
CHATBOT_LOADED = False
try:
    from chatbot_assistant import render_career_chatbot
    CHATBOT_LOADED = True
except ImportError:
    st.warning("⚠️ Modul chatbot tidak ditemukan. Fitur Career Assistant AI tidak tersedia.")

# ========================================
# PAGE CONFIG
# ========================================
st.set_page_config(
    page_title="Digital Talent Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================================
# CSS STYLING
# ========================================
st.markdown("""
<style>
/* Global Dark Theme */
body, .stApp {
    background-color: #0f1117 !important;
    color: #e4e6eb !important;
}

/* Cards */
.job-card, .course-card {
    background-color: #1c1f2b;
    border: 1px solid #2e3244;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 14px;
    box-shadow: 0 6px 16px rgba(0,0,0,0.2);
    transition: transform 0.2s;
}

.job-card:hover, .course-card:hover {
    transform: translateY(-2px);
}

/* Okupasi Card */
.okupasi-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 30px;
    border-radius: 15px;
    text-align: center;
    color: white;
    margin: 20px 0;
}

/* Google CSE */
.gsc-control-cse {
    background-color: transparent !important;
    border: none !important;
}

.gsc-input-box {
    background-color: #1c1f2b !important;
    border: 1px solid #2e3244 !important;
}
</style>
""", unsafe_allow_html=True)

# ========================================
# VALIDATION AT STARTUP
# ========================================
errors, warnings = validate_config()
if errors:
    for error in errors:
        st.error(error)
    st.stop()
if warnings:
    for warning in warnings:
        st.warning(warning)

# ========================================
# SESSION STATE INITIALIZATION
# ========================================
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'current_page': "Profil Talenta",
        'form_email': "",
        'form_nama': "",
        'form_lokasi': "",
        'form_linkedin': "",
        'form_cv_text': "",
        'mapped_okupasi_id': None,
        'mapped_okupasi_nama': None,
        'okupasi_info': {},
        'skill_gap': "",
        'profil_teks': "",
        'learning_path': []
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ========================================
# CONTINUE TO PART 2/5
# Part 2 akan berisi Helper Functions & CV Processing
# ========================================
# ========================================
# HELPER FUNCTIONS
# ========================================

def normalize_text(text: str) -> str:
    """Normalize text by removing special characters and extra whitespace"""
    if not isinstance(text, str):
        return ""
    text = text.replace('\xa0', ' ')
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_skill_tokens(text: str) -> list:
    """Extract skill tokens from text"""
    text = normalize_text(text).lower()
    parts = re.split(r"[,;/\\|]+", text)
    tokens = [p.strip() for p in parts if p.strip() and len(p.strip()) >= 2]
    return list(dict.fromkeys(tokens))

def display_learning_path_fallback(learning_path):
    """Fallback display for learning path"""
    for i, phase in enumerate(learning_path):
        with st.expander(f"Phase {i+1}: {phase.get('title', 'N/A')}"):
            skills = phase.get('skills', [])
            if skills:
                st.markdown(f"**Skills:** {', '.join(skills)}")

def display_skill_gap_chart_fallback(gap_analysis):
    """Fallback display for skill gap"""
    st.markdown("#### 📊 Skill Gap Analysis")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Skills Dimiliki", len(gap_analysis.get('owned_skills', [])))
    with col2:
        st.metric("Skills yang Hilang", len(gap_analysis.get('missing_skills', [])))

# ========================================
# CV PROCESSING FUNCTIONS
# ========================================

def extract_text_from_pdf(file_io) -> str:
    """Extract text from PDF file"""
    try:
        reader = PdfReader(file_io)
        return "".join([page.extract_text() or "" for page in reader.pages])
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

def extract_text_from_docx(file_io) -> str:
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(file_io)
        return "\n".join([p.text for p in doc.paragraphs if p.text])
    except Exception as e:
        st.error(f"Error reading DOCX: {e}")
        return ""

def parse_cv_data(cv_text: str) -> dict:
    """Parse CV data using regex patterns"""
    data = {
        "email": "",
        "nama": "",
        "linkedin": "",
        "lokasi": "",
        "cv_text": cv_text
    }
    
    # Extract email
    if match := re.search(r'[\w\.-]+@[\w\.-]+\.\w+', cv_text):
        data["email"] = match.group(0)
    
    # Extract LinkedIn
    if match := re.search(r'linkedin\.com/in/([\w-]+)', cv_text, re.IGNORECASE):
        data["linkedin"] = f"https://www.linkedin.com/in/{match.group(1)}"
    
    # Extract name (first line heuristic)
    lines = cv_text.split('\n')
    for line in lines[:5]:
        line = line.strip()
        if line and '@' not in line and len(line.split()) <= 4 and len(line) > 5:
            data["nama"] = line.title()
            break
    
    # Extract location
    if match := re.search(
        r'(Jakarta|Bandung|Surabaya|Yogyakarta|Jogja|Medan|Semarang|Makassar|Denpasar|Palembang)',
        cv_text, re.IGNORECASE
    ):
        lokasi = match.group(0).title()
        if lokasi == "Jogja":
            lokasi = "Yogyakarta"
        data["lokasi"] = lokasi
    
    return data

# ========================================
# SEMANTIC SEARCH FUNCTIONS
# ========================================

@st.cache_resource
def initialize_semantic_search(excel_path: str, sheet_name: str):
    """Initialize AI Semantic Search Engine with FAISS"""
    INDEX_FILE = "data/pon_index.faiss"
    DATA_FILE = "data/pon_data.pkl"
    MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
    
    try:
        model = SentenceTransformer(MODEL_NAME)
    except Exception as e:
        st.error(f"Gagal load model Sentence Transformer: {e}")
        return None, None, None
    
    # Load existing index
    if os.path.exists(INDEX_FILE) and os.path.exists(DATA_FILE):
        try:
            index = faiss.read_index(INDEX_FILE)
            with open(DATA_FILE, 'rb') as f:
                df_pon = pickle.load(f)
            return model, index, df_pon
        except Exception as e:
            st.warning(f"Gagal memuat cache: {e}. Membangun ulang...")
    
    # Build new index
    with st.spinner("Membangun semantic search index..."):
        try:
            df_pon = pd.read_excel(excel_path, sheet_name=sheet_name, engine='openpyxl')
            
            if df_pon is None or df_pon.empty:
                st.error(f"Data PON di sheet '{sheet_name}' kosong.")
                return None, None, None
            
            # Create corpus
            pon_corpus = (
                "Okupasi: " + df_pon['Okupasi'].astype(str) + ". " +
                "Unit Kompetensi: " + df_pon['Unit_Kompetensi'].astype(str) + ". " +
                "Keterampilan: " + df_pon['Kuk_Keywords'].astype(str)
            )
            
            # Encode
            pon_vectors = model.encode(pon_corpus.tolist(), show_progress_bar=True)
            
            # Create FAISS index
            d = pon_vectors.shape[1]
            index = faiss.IndexFlatIP(d)
            faiss.normalize_L2(pon_vectors)
            index.add(pon_vectors)
            
            # Save
            os.makedirs("data", exist_ok=True)
            faiss.write_index(index, INDEX_FILE)
            with open(DATA_FILE, 'wb') as f:
                pickle.dump(df_pon, f)
            
            return model, index, df_pon
        except Exception as e:
            st.error(f"Error saat membangun semantic index: {e}")
            traceback.print_exc()
            return None, None, None

def map_profile_semantically(profile_text: str) -> tuple:
    """Map profile to SKKNI using semantic search"""
    model, index, df_pon = initialize_semantic_search(EXCEL_PATH, SHEET_PON)
    
    if model is None or index is None:
        return None, None, 0, "Gagal memuat semantic engine."
    
    try:
        # Encode query
        query_vector = model.encode([profile_text])
        faiss.normalize_L2(query_vector)
        
        # Search
        scores, indices = index.search(query_vector, k=1)
        
        idx = indices[0][0]
        best_score = scores[0][0]
        
        data = df_pon.iloc[idx]
        
        # Calculate skill gap
        required_keywords_raw = str(data.get('Kuk_Keywords', '')).lower().split()
        required_keywords = set(k for k in required_keywords_raw if k and len(k) > 2)
        
        user_keywords = set(extract_skill_tokens(profile_text))
        
        missing_skills = [s.title() for s in required_keywords if s not in user_keywords]
        
        skill_gap_text = ", ".join(sorted(missing_skills)[:5]) if missing_skills else "Tidak ada gap signifikan"
        
        return (
            data.get('OkupasiID', 'N/A'),
            data.get('Okupasi', 'N/A'),
            best_score,
            skill_gap_text
        )
    
    except Exception as e:
        st.error(f"Error saat mapping profil: {e}")
        traceback.print_exc()
        return None, None, 0, "Terjadi kesalahan internal."

# ========================================
# MATCHER INITIALIZATION
# ========================================

@st.cache_resource
def init_matcher():
    """Initialize SKKNI matcher"""
    if not UTILS_LOADED:
        return None
        
    try:
        return create_skkni_matcher(EXCEL_PATH, SHEET_PON, SHEET_COURSE)
    except Exception as e:
        st.error(f"Error menginisialisasi matcher: {e}")
        return None

# ========================================
# CONTINUE TO PART 3/5
# Part 3 akan berisi Sidebar & Profil Talenta Page
# ========================================
# ========================================
# SIDEBAR NAVIGATION
# ========================================

def render_sidebar():
    """Render sidebar navigation and status"""
    with st.sidebar:
        st.title("🎓 Digital Talent Platform")
        
        # Navigation
        st.markdown("### 📑 Menu")
        
        pages = ["📄 Profil Talenta", "💡 Career Assistant"]
        
        for page in pages:
            if st.button(page, use_container_width=True, key=f"nav_{page}"):
                st.session_state.current_page = page.split(" ", 1)[1]
                st.rerun()
        
        st.markdown("---")
        
        # System Status
        st.markdown("### ⚙️ Status Sistem")
        api_status = get_api_status()
        
        st.markdown(f"{'✅' if api_status.get('database', False) else '❌'} Database Excel")
        st.markdown(f"{'✅' if api_status.get('gemini', False) else '⚠️'} Gemini AI")
        st.markdown(f"{'✅' if api_status.get('google_cse', False) else '⚠️'} Google CSE")
        
        # Okupasi Info
        if st.session_state.mapped_okupasi_id:
            st.markdown("---")
            st.markdown("### 🎯 Okupasi Aktif")
            st.success(f"**{st.session_state.mapped_okupasi_nama}**")
            st.caption(f"ID: {st.session_state.mapped_okupasi_id}")

# ========================================
# PAGE 1: PROFIL TALENTA
# ========================================

def page_profil_talenta():
    """Profile page with CV upload and SKKNI mapping"""
    st.title("📄 Profil Talenta")
    st.markdown("Unggah CV Anda untuk dianalisis dan dipetakan ke standar **PON TIK**.")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Unggah CV (PDF, DOCX, atau TXT)",
        type=["pdf", "docx", "txt"],
        help="Upload CV Anda untuk parsing otomatis"
    )
    
    if uploaded_file:
        with st.spinner("Memproses CV..."):
            try:
                if uploaded_file.type == "application/pdf":
                    raw_text = extract_text_from_pdf(io.BytesIO(uploaded_file.getvalue()))
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    raw_text = extract_text_from_docx(io.BytesIO(uploaded_file.getvalue()))
                else:
                    raw_text = uploaded_file.getvalue().decode("utf-8", errors='ignore')
                
                if raw_text:
                    parsed = parse_cv_data(raw_text)
                    for k, v in parsed.items():
                        st.session_state[f"form_{k}"] = v
                    
                    st.success("✅ CV berhasil diproses dan data otomatis diisi!")
                else:
                    st.warning("⚠️ Tidak ada teks yang dapat diekstrak dari file.")
            
            except Exception as e:
                st.error(f"Gagal memproses file: {e}")
    
    st.markdown("---")
    
    # Form input
    st.markdown("### 📝 Lengkapi Profil Anda")
    
    with st.form("profil_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            email = st.text_input("Email*", value=st.session_state.form_email)
            nama = st.text_input("Nama Lengkap*", value=st.session_state.form_nama)
        
        with col2:
            lokasi = st.text_input("Lokasi", value=st.session_state.form_lokasi)
            linkedin = st.text_input("URL LinkedIn", value=st.session_state.form_linkedin)
        
        raw_cv = st.text_area(
            "CV atau Deskripsi Diri*",
            value=st.session_state.form_cv_text,
            height=250,
            help="AI akan menganalisis makna dari teks ini untuk memetakan ke okupasi yang paling cocok."
        )
        
        submitted = st.form_submit_button("💾 Simpan & Petakan ke SKKNI", use_container_width=True)
    
    if submitted:
        if not email or not nama or not raw_cv:
            st.warning("⚠️ Mohon isi semua field yang wajib (Email, Nama, CV/Deskripsi)")
        else:
            # Update session
            st.session_state.form_email = email
            st.session_state.form_nama = nama
            st.session_state.form_lokasi = lokasi
            st.session_state.form_linkedin = linkedin
            st.session_state.form_cv_text = raw_cv
            st.session_state.profil_teks = raw_cv
            
            with st.spinner("🔍 Mapping ke SKKNI..."):
                okupasi_id, okupasi_nama, skor, gap = map_profile_semantically(raw_cv)
                
                if okupasi_id:
                    st.session_state.mapped_okupasi_id = okupasi_id
                    st.session_state.mapped_okupasi_nama = okupasi_nama
                    st.session_state.skill_gap = gap
                    
                    # Get full info
                    matcher = init_matcher()
                    if matcher:
                        st.session_state.okupasi_info = matcher.get_okupasi_details(okupasi_id)
                    
                    st.success("✅ Profil berhasil dipetakan!")
                    
                    col1, col2 = st.columns(2)
                    col1.metric("Okupasi", okupasi_nama)
                    col2.metric("Tingkat Kecocokan", f"{skor*100:.1f}%")
                    
                    st.warning(f"**Skill Gap:** {gap}")
                    st.info("💡 Lanjut ke **Career Assistant** untuk rekomendasi pelatihan & lowongan.")
                else:
                    st.error("❌ Gagal memetakan profil. Pastikan data PON sudah benar.")

# ========================================
# PAGE 2: CAREER ASSISTANT
# ========================================

def page_career_assistant():
    """Career assistant with learning path, courses, and job search"""
    st.title("💡 Career Assistant")
    st.caption("Learning Path → Courses → Job Search → AI Chat")
    
    if not st.session_state.mapped_okupasi_id:
        st.warning("⚠️ Silakan lengkapi profil terlebih dahulu.")
        
        if st.button("🔙 Kembali ke Profil Talenta"):
            st.session_state.current_page = "Profil Talenta"
            st.rerun()
        return
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 SKKNI Info",
        "📚 Learning Path & Courses",
        "💼 Job Search",
        "💬 AI Career Chat"
    ])
    
    # TAB 1: SKKNI Info
    with tab1:
        render_skkni_info()
    
    # TAB 2: Learning Path & Courses
    with tab2:
        render_learning_path_courses()
    
    # TAB 3: Job Search
    with tab3:
        render_job_search()
    
    # TAB 4: AI Chat
    with tab4:
        render_ai_career_chat()

def render_skkni_info():
    """Render SKKNI information and skill gap analysis"""
    st.markdown("### 🎯 Okupasi Anda")
    
    matcher = init_matcher()
    if matcher and st.session_state.okupasi_info:
        okupasi_details = st.session_state.okupasi_info
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown(f"""
            <div class='okupasi-card'>
                <div style='font-size: 3em;'>👔</div>
                <div style='font-size: 1.5em; font-weight: bold; margin-top: 10px;'>
                    {okupasi_details.get('okupasi_nama', 'N/A')}
                </div>
                <div style='font-size: 0.9em; margin-top: 5px; opacity: 0.9;'>
                    {okupasi_details.get('okupasi_id', 'N/A')}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"**Area:** {okupasi_details.get('area_fungsi', 'N/A')}")
            st.markdown(f"**Unit:** {okupasi_details.get('unit_kompetensi', 'N/A')}")
            st.markdown(f"**Level:** {okupasi_details.get('level', 'N/A')}")
            
            with st.expander("📋 Keterampilan yang Dibutuhkan"):
                skills = okupasi_details.get('kuk_keywords', [])
                if skills:
                    for i, skill in enumerate(skills, 1):
                        st.markdown(f"{i}. {skill.title()}")
                else:
                    st.info("Tidak ada data keterampilan.")
        
        # Skill Gap Analysis
        st.markdown("---")
        st.markdown("### 📊 Skill Gap Analysis")
        
        user_skills = extract_skill_tokens(st.session_state.profil_teks)
        gap_analysis = matcher.calculate_skill_gap(user_skills, st.session_state.mapped_okupasi_id)
        
        col_gap1, col_gap2 = st.columns(2)
        
        with col_gap1:
            if UTILS_LOADED:
                display_skill_gap_chart(gap_analysis)
            else:
                display_skill_gap_chart_fallback(gap_analysis)
        
        with col_gap2:
            st.markdown("#### ✅ Skills Dimiliki")
            if gap_analysis.get('owned_skills'):
                for skill in gap_analysis['owned_skills'][:10]:
                    st.markdown(f"- 🎯 {skill.title()}")
            else:
                st.info("Belum ada match.")
            
            st.markdown("#### ❌ Skills yang Perlu Dipelajari")
            if gap_analysis.get('priority_skills'):
                for skill in gap_analysis['priority_skills'][:5]:
                    st.markdown(f"- 🔴 {skill.title()}")
    else:
        st.error("⚠️ Data okupasi tidak tersedia. Silakan periksa konfigurasi Anda.")

def render_learning_path_courses():
    """Render learning path and course recommendations"""
    # Hapus judul utama ini
    # st.markdown("### 📚 Learning Path & Rekomendasi Course")
    
    matcher = init_matcher()
    if not matcher:
        st.error("⚠️ Tidak dapat membuat learning path. Matcher tidak tersedia.")
        return
    
    user_skills = extract_skill_tokens(st.session_state.profil_teks)
    
    # Generate Learning Path
    learning_path = matcher.generate_learning_path(
        st.session_state.mapped_okupasi_id,
        user_skills
    )
    
    st.session_state.learning_path = learning_path
    
    # Display Learning Path
    if learning_path:
        # Hapus atau ubah judul bagian learning path
        # st.markdown("#### 📖 Learning Path Rekomendasi")
        if UTILS_LOADED:
            display_learning_path(learning_path)
        else:
            display_learning_path_fallback(learning_path)
        st.markdown("---")
    
    # Display Recommended Courses
    st.markdown("#### 🎓 Rekomendasi Course")
    st.info(f"🔍 Mencari course berdasarkan: **{st.session_state.mapped_okupasi_nama}**")
    
    if matcher.df_courses is None or matcher.df_courses.empty:
        st.warning(f"⚠️ Data course belum tersedia. Tambahkan sheet **'{SHEET_COURSE}'** di file Excel.")
        return
    
    # Extract keywords ONLY from okupasi name
    okupasi_nama = st.session_state.mapped_okupasi_nama or ""
    
    # Split okupasi name into individual words as keywords
    # Example: "Data Scientist" -> ["data", "scientist"]
    all_keywords = set(word.lower() for word in okupasi_nama.split() if word)
    
    # Filter courses based on keywords in Title
    recommended_courses = filter_courses_by_keywords(matcher.df_courses, all_keywords)
    
    if not recommended_courses:
        st.warning("⚠️ Tidak ada course yang cocok ditemukan.")
        st.info("💡 Menampilkan semua course yang tersedia:")
        display_all_courses(matcher.df_courses)
    else:
        st.success(f"🎯 Ditemukan {len(recommended_courses)} course yang relevan!")
        display_courses_table(recommended_courses)

def filter_courses_by_keywords(df_courses, keywords):
    """Filter courses based on keywords in Title"""
    if df_courses is None or df_courses.empty:
        return []
    
    filtered_courses = []
    
    for idx, row in df_courses.iterrows():
        title = str(row.get('Title', '')).lower()
        
        # Check if any keyword exists in title
        for keyword in keywords:
            if keyword in title:
                course_data = {
                    'CourseID': row.get('CourseID', 'N/A'),
                    'Title': row.get('Title', 'N/A'),
                    'Platform': row.get('Platform', 'N/A'),
                    'Jenis': row.get('Jenis', 'N/A'),
                    'URL': row.get('URL', '#'),
                    'matched_keyword': keyword
                }
                filtered_courses.append(course_data)
                break  # Only add once per course
    
    return filtered_courses

def display_all_courses(df_courses):
    """Display all available courses in table format"""
    if df_courses is None or df_courses.empty:
        return
    
    # Select only required columns
    display_df = df_courses[['CourseID', 'Title', 'Platform', 'Jenis', 'URL']].copy()
    
    # Display as table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "CourseID": st.column_config.TextColumn("Course ID", width="small"),
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Platform": st.column_config.TextColumn("Platform", width="medium"),
            "Jenis": st.column_config.TextColumn("Jenis", width="small"),
            "URL": st.column_config.LinkColumn("URL", width="small")
        }
    )
    
    st.caption(f"Total: {len(display_df)} courses")

def display_courses_table(courses):
    """Display recommended courses in card and table format"""
    # Display in expandable cards
    for i, course in enumerate(courses, 1):
        with st.expander(f"🎓 {i}. {course['Title']}", expanded=(i <= 3)):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Course ID:** {course['CourseID']}")
                st.markdown(f"**Platform:** {course['Platform']}")
                st.markdown(f"**Jenis:** {course['Jenis']}")
                st.markdown(f"**Matched Keyword:** `{course['matched_keyword']}`")
            
            with col2:
                if course['URL'] and course['URL'] != '#':
                    st.link_button("🔗 Buka Course", course['URL'], use_container_width=True)
    
    st.markdown("---")
    
    # Also display as table for easy reference
    with st.expander("📊 Lihat Semua dalam Tabel"):
        df_display = pd.DataFrame(courses)
        df_display = df_display[['CourseID', 'Title', 'Platform', 'Jenis', 'URL']]
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "CourseID": st.column_config.TextColumn("Course ID", width="small"),
                "Title": st.column_config.TextColumn("Title", width="large"),
                "Platform": st.column_config.TextColumn("Platform", width="medium"),
                "Jenis": st.column_config.TextColumn("Jenis", width="small"),
                "URL": st.column_config.LinkColumn("URL", width="small")
            }
        )

# ========================================
# PAGE 2: CAREER ASSISTANT
# ========================================

def page_career_assistant():
    """Career assistant with learning path, courses, and job search"""
    st.title("💡 Career Assistant")
    st.caption("Learning Path → Courses → Job Search → AI Chat")
    
    if not st.session_state.mapped_okupasi_id:
        st.warning("⚠️ Silakan lengkapi profil terlebih dahulu.")
        
        if st.button("🔙 Kembali ke Profil Talenta"):
            st.session_state.current_page = "Profil Talenta"
            st.rerun()
        return
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 SKKNI Info",
        "📚 Learning Path & Courses",
        "💼 Job Search",
        "💬 AI Career Chat"
    ])
    
    # TAB 1: SKKNI Info
    with tab1:
        render_skkni_info()
    
    # TAB 2: Learning Path & Courses
    with tab2:
        render_learning_path_courses()
    
    # TAB 3: Job Search
    with tab3:
        render_job_search()
    
    # TAB 4: AI Chat
    with tab4:
        render_ai_career_chat()

def render_skkni_info():
    """Render SKKNI information and skill gap analysis"""
    st.markdown("### 🎯 Okupasi Anda")
    
    matcher = init_matcher()
    if matcher and st.session_state.okupasi_info:
        okupasi_details = st.session_state.okupasi_info
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown(f"""
            <div class='okupasi-card'>
                <div style='font-size: 3em;'>👔</div>
                <div style='font-size: 1.5em; font-weight: bold; margin-top: 10px;'>
                    {okupasi_details.get('okupasi_nama', 'N/A')}
                </div>
                <div style='font-size: 0.9em; margin-top: 5px; opacity: 0.9;'>
                    {okupasi_details.get('okupasi_id', 'N/A')}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"**Area:** {okupasi_details.get('area_fungsi', 'N/A')}")
            st.markdown(f"**Unit:** {okupasi_details.get('unit_kompetensi', 'N/A')}")
            st.markdown(f"**Level:** {okupasi_details.get('level', 'N/A')}")
            
            with st.expander("📋 Keterampilan yang Dibutuhkan"):
                skills = okupasi_details.get('kuk_keywords', [])
                if skills:
                    for i, skill in enumerate(skills, 1):
                        st.markdown(f"{i}. {skill.title()}")
                else:
                    st.info("Tidak ada data keterampilan.")
        
        # Skill Gap Analysis
        st.markdown("---")
        st.markdown("### 📊 Skill Gap Analysis")
        
        user_skills = extract_skill_tokens(st.session_state.profil_teks)
        gap_analysis = matcher.calculate_skill_gap(user_skills, st.session_state.mapped_okupasi_id)
        
        col_gap1, col_gap2 = st.columns(2)
        
        with col_gap1:
            if UTILS_LOADED:
                display_skill_gap_chart(gap_analysis)
            else:
                display_skill_gap_chart_fallback(gap_analysis)
        
        with col_gap2:
            st.markdown("#### ✅ Skills Dimiliki")
            if gap_analysis.get('owned_skills'):
                for skill in gap_analysis['owned_skills'][:10]:
                    st.markdown(f"- 🎯 {skill.title()}")
            else:
                st.info("Belum ada match.")
            
            st.markdown("#### ❌ Skills yang Perlu Dipelajari")
            if gap_analysis.get('priority_skills'):
                for skill in gap_analysis['priority_skills'][:5]:
                    st.markdown(f"- 🔴 {skill.title()}")
    else:
        st.error("⚠️ Data okupasi tidak tersedia. Silakan periksa konfigurasi Anda.")

def render_learning_path_courses():
    """Render learning path and course recommendations"""
    st.markdown("### 📚 Learning Path & Rekomendasi Course")
    
    matcher = init_matcher()
    if not matcher:
        st.error("⚠️ Tidak dapat membuat learning path. Matcher tidak tersedia.")
        return
    
    user_skills = extract_skill_tokens(st.session_state.profil_teks)
    
    # Generate Learning Path
    learning_path = matcher.generate_learning_path(
        st.session_state.mapped_okupasi_id,
        user_skills
    )
    
    st.session_state.learning_path = learning_path
    
    # Display Learning Path
    if learning_path:
        st.markdown("#### 📖 Learning Path Rekomendasi")
        if UTILS_LOADED:
            display_learning_path(learning_path)
        else:
            display_learning_path_fallback(learning_path)
        st.markdown("---")
    
    # Display Recommended Courses
    st.markdown("#### 🎓 Rekomendasi Course")
    st.info(f"🔍 Mencari course berdasarkan: **{st.session_state.mapped_okupasi_nama}**")
    
    if matcher.df_courses is None or matcher.df_courses.empty:
        st.warning(f"⚠️ Data course belum tersedia. Tambahkan sheet **'{SHEET_COURSE}'** di file Excel.")
        return
    
    # Extract keywords ONLY from okupasi name
    okupasi_nama = st.session_state.mapped_okupasi_nama or ""
    
    # Split okupasi name into individual words as keywords
    # Example: "Data Scientist" -> ["data", "scientist"]
    all_keywords = set(word.lower() for word in okupasi_nama.split() if word)
    
    # Filter courses based on keywords in Title
    recommended_courses = filter_courses_by_keywords(matcher.df_courses, all_keywords)
    
    if not recommended_courses:
        st.warning("⚠️ Tidak ada course yang cocok ditemukan.")
        st.info("💡 Menampilkan semua course yang tersedia:")
        display_all_courses(matcher.df_courses)
    else:
        st.success(f"🎯 Ditemukan {len(recommended_courses)} course yang relevan!")
        display_courses_table(recommended_courses)

def filter_courses_by_keywords(df_courses, keywords):
    """Filter courses based on keywords in Title"""
    if df_courses is None or df_courses.empty:
        return []
    
    filtered_courses = []
    
    for idx, row in df_courses.iterrows():
        title = str(row.get('Title', '')).lower()
        
        # Check if any keyword exists in title
        for keyword in keywords:
            if keyword in title:
                course_data = {
                    'CourseID': row.get('CourseID', 'N/A'),
                    'Title': row.get('Title', 'N/A'),
                    'Platform': row.get('Platform', 'N/A'),
                    'Jenis': row.get('Jenis', 'N/A'),
                    'URL': row.get('URL', '#'),
                    'matched_keyword': keyword
                }
                filtered_courses.append(course_data)
                break  # Only add once per course
    
    return filtered_courses

def display_all_courses(df_courses):
    """Display all available courses in table format"""
    if df_courses is None or df_courses.empty:
        return
    
    # Select only required columns
    display_df = df_courses[['CourseID', 'Title', 'Platform', 'Jenis', 'URL']].copy()
    
    # Display as table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "CourseID": st.column_config.TextColumn("Course ID", width="small"),
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Platform": st.column_config.TextColumn("Platform", width="medium"),
            "Jenis": st.column_config.TextColumn("Jenis", width="small"),
            "URL": st.column_config.LinkColumn("URL", width="small")
        }
    )
    
    st.caption(f"Total: {len(display_df)} courses")

def display_courses_table(courses):
    """Display recommended courses in card and table format"""
    # Display in expandable cards
    for i, course in enumerate(courses, 1):
        with st.expander(f"🎓 {i}. {course['Title']}", expanded=(i <= 3)):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Course ID:** {course['CourseID']}")
                st.markdown(f"**Platform:** {course['Platform']}")
                st.markdown(f"**Jenis:** {course['Jenis']}")
                st.markdown(f"**Matched Keyword:** `{course['matched_keyword']}`")
            
            with col2:
                if course['URL'] and course['URL'] != '#':
                    st.link_button("🔗 Buka Course", course['URL'], use_container_width=True)
    
    st.markdown("---")
    
    # Also display as table for easy reference
    with st.expander("📊 Lihat Semua dalam Tabel"):
        df_display = pd.DataFrame(courses)
        df_display = df_display[['CourseID', 'Title', 'Platform', 'Jenis', 'URL']]
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "CourseID": st.column_config.TextColumn("Course ID", width="small"),
                "Title": st.column_config.TextColumn("Title", width="large"),
                "Platform": st.column_config.TextColumn("Platform", width="medium"),
                "Jenis": st.column_config.TextColumn("Jenis", width="small"),
                "URL": st.column_config.LinkColumn("URL", width="small")
            }
        )

# ========================================
# CONTINUE TO PART 5/5
# Part 5 akan berisi Job Search & AI Chat + Main Router
# ========================================
# ========================================
# JOB SEARCH TAB
# ========================================

def render_job_search():
    """Render job search portals and Google CSE"""
    st.markdown("### 💼 Pencarian Lowongan Kerja")
    
    matcher = init_matcher()
    if not matcher:
        st.error("⚠️ Matcher tidak tersedia. Tidak bisa memberikan rekomendasi keyword.")
        return
    
    job_keywords = matcher.get_job_search_keywords(st.session_state.mapped_okupasi_id)
    
    st.markdown("#### 🔍 Keywords Rekomendasi")
    if job_keywords:
        st.info(f"**Posisi:** {job_keywords[0]}")
        primary_keyword = job_keywords[0]
    else:
        primary_keyword = "Data Scientist"
    
    st.markdown("---")
    
    # Prepare URLs
    primary_keyword_encoded = primary_keyword.replace(" ", "+")
    
    # Job portal URLs
    job_portals = {
        "LinkedIn": {
            "url": f"https://www.linkedin.com/jobs/search/?keywords={primary_keyword_encoded}&location=Indonesia",
            "color": "#0077B5",
            "icon": "🔵",
            "description": "Platform profesional terbesar untuk mencari lowongan kerja di berbagai industri."
        },
        "Jobstreet": {
            "url": f"https://id.jobstreet.com/id/{primary_keyword.title().replace(' ', '-')}-jobs",
            "color": "#FF6B35",
            "icon": "🟠",
            "description": "Portal lowongan kerja terpopuler di Indonesia dan Asia Tenggara."
        },
        "Glints": {
            "url": f"https://glints.com/id/opportunities/jobs/explore?keyword={primary_keyword_encoded}&country=ID&locationName=All+Cities%2FProvinces",
            "color": "#FD5631",
            "icon": "🔴",
            "description": "Platform talent ecosystem untuk profesional muda di Asia."
        },
        "Indeed": {
            "url": f"https://id.indeed.com/jobs?q={primary_keyword_encoded}&l=Indonesia",
            "color": "#2164F3",
            "icon": "🌐",
            "description": "Mesin pencari lowongan kerja terbesar di dunia."
        },
        "Kalibrr": {
            "url": f"https://www.kalibrr.com/id-ID/home/te/{primary_keyword.lower().replace(' ', '-')}",
            "color": "#00C48C",
            "icon": "💼",
            "description": "Platform rekrutmen modern dengan fitur AI matching."
        }
    }
    
    # Display job portals
    st.markdown("### 🌐 Portal Lowongan Kerja")
    
    # First row: LinkedIn, Jobstreet, Glints
    col1, col2, col3 = st.columns(3)
    
    for idx, (portal_name, portal_info) in enumerate(list(job_portals.items())[:3]):
        col = [col1, col2, col3][idx]
        with col:
            st.markdown(f"""
            <div class='job-card'>
                <h3 style='color: {portal_info["color"]};'>{portal_info["icon"]} {portal_name}</h3>
                <p style='color: #9ca3af; font-size: 0.9em;'>{portal_info["description"]}</p>
                <p><strong>Keyword:</strong> {primary_keyword}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.link_button(f"🔗 {portal_name}", portal_info["url"], use_container_width=True)
    
    st.markdown("---")
    
    # Second row: Indeed, Kalibrr
    col4, col5 = st.columns(2)
    
    for idx, (portal_name, portal_info) in enumerate(list(job_portals.items())[3:]):
        col = [col4, col5][idx]
        with col:
            st.markdown(f"""
            <div class='job-card'>
                <h3 style='color: {portal_info["color"]};'>{portal_info["icon"]} {portal_name}</h3>
                <p style='color: #9ca3af; font-size: 0.9em;'>{portal_info["description"]}</p>
                <p><strong>Keyword:</strong> {primary_keyword}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.link_button(f"🔗 {portal_name}", portal_info["url"], use_container_width=True)
    
    st.markdown("---")
    
    # Google Custom Search
    st.markdown("### 🔍 Google Job Search")
    
    if get_api_status().get('google_cse'):
        st.components.v1.html(f"""
        <script async src="https://cse.google.com/cse.js?cx={GOOGLE_CSE_ID}"></script>
        <div class="gcse-search"></div>
        """, height=400)
    else:
        st.warning("⚠️ Google CSE tidak dikonfigurasi. Gunakan link di bawah:")
        google_jobs_url = f"https://www.google.com/search?q={primary_keyword_encoded}+jobs+indonesia"
        st.link_button("🔍 Google Jobs Search", google_jobs_url, use_container_width=True)
    
    st.markdown("---")
    
    # Tips
    with st.expander("💡 Tips Pencarian Lowongan"):
        st.markdown("""
        **Tips untuk mendapatkan hasil terbaik:**
        
        1. **Update profil Anda** di setiap platform agar mudah ditemukan recruiter
        2. **Gunakan filter** untuk menyaring berdasarkan:
           - Lokasi kerja (remote/onsite/hybrid)
           - Tingkat pengalaman
           - Gaji yang diharapkan
           - Jenis pekerjaan (full-time/part-time/contract)
        
        3. **Set Job Alert** di masing-masing platform untuk notifikasi lowongan baru
        4. **Sesuaikan CV** dengan job description yang Anda lamar
        5. **Network aktif** di LinkedIn untuk meningkatkan visibility
        
        **Boolean Search Tips:**
        - Gunakan tanda kutip untuk exact match: `"Data Scientist"`
        - Gunakan OR untuk variasi: `Data Scientist OR Machine Learning Engineer`
        - Gunakan minus untuk exclude: `Data Scientist -Intern`
        """)

# ========================================
# AI CAREER CHAT TAB
# ========================================

def render_ai_career_chat():
    """Render AI Career Chat tab"""
    if CHATBOT_LOADED:
        render_career_chatbot()
    else:
        st.error("❌ Modul chatbot tidak tersedia.")
        st.info("💡 Pastikan file `chatbot_assistant.py` ada di folder project.")
        
        with st.expander("ℹ️ Cara Mengaktifkan AI Career Chat"):
            st.markdown("""
            **Untuk mengaktifkan fitur AI Career Chat:**
            
            1. Pastikan file `chatbot_assistant.py` ada di folder yang sama dengan `app.py`
            2. File harus berisi fungsi `render_career_chatbot()`
            3. Restart aplikasi Streamlit
            
            **Fitur yang tersedia setelah aktif:**
            - Chat dengan AI untuk konsultasi karir
            - Rekomendasi personalized berdasarkan profil Anda
            - Tips interview dan career development
            - Q&A tentang learning path dan okupasi
            """)

# ========================================
# MAIN ROUTER
# ========================================

def main():
    """Main application router"""
    # Render sidebar
    render_sidebar()
    
    # Route to appropriate page
    current_page = st.session_state.current_page
    
    if current_page == "Profil Talenta":
        page_profil_talenta()
    elif current_page == "Career Assistant":
        page_career_assistant()
    else:
        page_profil_talenta()

# ========================================
# FOOTER
# ========================================

def render_footer():
    """Render application footer"""
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #9ca3af; padding: 20px;'>
        <p><strong>🚀 Digital Talent Platform</strong></p>
        <p style='font-size: 0.85em;'>
            CV Analysis → SKKNI Mapping → Learning Path → Courses → Jobs
        </p>
        <p style='font-size: 0.75em; margin-top: 10px;'>
            Built with Streamlit • Powered by AI
        </p>
    </div>
    """, unsafe_allow_html=True)

# ========================================
# RUN APPLICATION
# ========================================

if __name__ == "__main__":
    main()
    render_footer()

# ========================================
# END OF app.py
# 
# COMPLETE FILE STRUCTURE:
# Part 1: Import & Setup
# Part 2: Helper Functions & CV Processing
# Part 3: Sidebar & Profil Talenta Page
# Part 4: Career Assistant - SKKNI Info & Learning Path
# Part 5: Job Search, AI Chat & Main Router (THIS PART)
#
# Cara menggunakan:
# 1. Copy semua 5 part secara berurutan ke dalam satu file app.py
# 2. Pastikan semua dependencies terinstall
# 3. Jalankan: streamlit run app.py

# ========================================


