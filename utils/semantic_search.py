# ========================================
# utils/semantic_search.py
# ========================================
"""
Semantic Search Engine menggunakan FAISS + Sentence Transformers
Mendukung PON TIK dan SKKNI mapping
"""

import os
import pickle
import pandas as pd
import streamlit as st
import faiss
from sentence_transformers import SentenceTransformer

from config import (
    EXCEL_PATH, SHEET_PON, SHEET_SKKNI,
    EMBEDDING_MODEL, FAISS_INDEX_FILE, FAISS_DATA_FILE,
    SKKNI_INDEX_FILE, SKKNI_DATA_FILE
)

@st.cache_resource
def initialize_pon_semantic_search():
    """Inisialisasi semantic search untuk PON TIK"""
    INDEX_FILE = FAISS_INDEX_FILE
    DATA_FILE = FAISS_DATA_FILE
    
    try:
        model = SentenceTransformer(EMBEDDING_MODEL)
    except Exception as e:
        st.error(f"Gagal load model: {e}")
        return None, None, None
    
    # Cek apakah index sudah ada
    if os.path.exists(INDEX_FILE) and os.path.exists(DATA_FILE):
        try:
            index = faiss.read_index(INDEX_FILE)
            with open(DATA_FILE, 'rb') as f:
                df_pon = pickle.load(f)
            st.success("✅ PON TIK semantic engine loaded from cache")
            return model, index, df_pon
        except Exception as e:
            st.warning(f"Cache error: {e}. Rebuilding index...")
    
    # Build new index
    st.info("🔄 Building PON TIK semantic index...")
    
    df_pon = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_PON)
    
    if df_pon is None or df_pon.empty:
        st.error("Data PON TIK kosong!")
        return None, None, None
    
    # Buat corpus dari kolom relevan
    pon_corpus = (
        "Okupasi: " + df_pon['Okupasi'].astype(str) + ". " +
        "Unit Kompetensi: " + df_pon['Unit_Kompetensi'].astype(str) + ". " +
        "Keterampilan: " + df_pon['Kuk_Keywords'].astype(str)
    )
    
    # Encode
    pon_vectors = model.encode(pon_corpus.tolist(), show_progress_bar=True)
    
    # Build FAISS index
    d = pon_vectors.shape[1]
    index = faiss.IndexFlatIP(d)
    faiss.normalize_L2(pon_vectors)
    index.add(pon_vectors)
    
    # Save
    faiss.write_index(index, INDEX_FILE)
    with open(DATA_FILE, 'wb') as f:
        pickle.dump(df_pon, f)
    
    st.success("✅ PON TIK index created and saved")
    return model, index, df_pon


@st.cache_resource
def initialize_skkni_semantic_search():
    """Inisialisasi semantic search untuk SKKNI"""
    INDEX_FILE = SKKNI_INDEX_FILE
    DATA_FILE = SKKNI_DATA_FILE
    
    try:
        model = SentenceTransformer(EMBEDDING_MODEL)
    except Exception as e:
        st.error(f"Gagal load model: {e}")
        return None, None, None
    
    # Cek cache
    if os.path.exists(INDEX_FILE) and os.path.exists(DATA_FILE):
        try:
            index = faiss.read_index(INDEX_FILE)
            with open(DATA_FILE, 'rb') as f:
                df_skkni = pickle.load(f)
            st.success("✅ SKKNI semantic engine loaded from cache")
            return model, index, df_skkni
        except Exception as e:
            st.warning(f"Cache error: {e}. Rebuilding index...")
    
    # Build new index
    st.info("🔄 Building SKKNI semantic index...")
    
    df_skkni = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_SKKNI)
    
    if df_skkni is None or df_skkni.empty:
        st.error("Data SKKNI kosong!")
        return None, None, None
    
    # Buat corpus
    skkni_corpus = (
        "SKKNI: " + df_skkni['Nama_SKKNI'].astype(str) + ". " +
        "Bidang: " + df_skkni['Bidang'].astype(str) + ". " +
        "Kompetensi: " + df_skkni['Unit_Kompetensi'].astype(str) + ". " +
        "Keywords: " + df_skkni['Keywords'].astype(str)
    )
    
    # Encode
    skkni_vectors = model.encode(skkni_corpus.tolist(), show_progress_bar=True)
    
    # Build index
    d = skkni_vectors.shape[1]
    index = faiss.IndexFlatIP(d)
    faiss.normalize_L2(skkni_vectors)
    index.add(skkni_vectors)
    
    # Save
    faiss.write_index(index, INDEX_FILE)
    with open(DATA_FILE, 'wb') as f:
        pickle.dump(df_skkni, f)
    
    st.success("✅ SKKNI index created and saved")
    return model, index, df_skkni


def map_profile_to_pon(profile_text: str):
    """Map profil ke PON TIK"""
    model, index, df_pon = initialize_pon_semantic_search()
    
    if model is None or index is None:
        return None
    
    try:
        query_vector = model.encode([profile_text])
        faiss.normalize_L2(query_vector)
        
        scores, indices = index.search(query_vector, k=3)
        
        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            score = scores[0][i]
            data = df_pon.iloc[idx].to_dict()
            data['similarity_score'] = float(score)
            results.append(data)
        
        return results
    
    except Exception as e:
        st.error(f"Error mapping PON TIK: {e}")
        return None


def map_profile_to_skkni(profile_text: str, pon_okupasi_id: str = None):
    """Map profil ke SKKNI (dengan optional filter berdasarkan PON TIK)"""
    model, index, df_skkni = initialize_skkni_semantic_search()
    
    if model is None or index is None:
        return None
    
    try:
        # Jika ada PON okupasi ID, prioritaskan SKKNI yang related
        if pon_okupasi_id:
            related_skkni = df_skkni[
                df_skkni['PON_TIK_ID_Related'] == pon_okupasi_id
            ]
            
            if not related_skkni.empty:
                # Direct match found
                return related_skkni.iloc[0].to_dict()
        
        # Semantic search
        query_vector = model.encode([profile_text])
        faiss.normalize_L2(query_vector)
        
        scores, indices = index.search(query_vector, k=3)
        
        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            score = scores[0][i]
            data = df_skkni.iloc[idx].to_dict()
            data['similarity_score'] = float(score)
            results.append(data)
        
        return results
    
    except Exception as e:
        st.error(f"Error mapping SKKNI: {e}")
        return None


# ========================================
# utils/course_recommender.py
# ========================================
"""
Course Recommendation Engine untuk Maxy Academy
"""

import pandas as pd
import streamlit as st
from utils.cv_parser import extract_skill_tokens
from config import EXCEL_PATH, SHEET_MAXY

@st.cache_data(ttl=600)
def load_maxy_courses():
    """Load katalog kursus Maxy Academy"""
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_MAXY)
        return df
    except Exception as e:
        st.error(f"Error loading Maxy courses: {e}")
        return None


def recommend_courses_from_skkni(skkni_id: str, skill_gap: str, top_k: int = 5):
    """
    Recommend courses berdasarkan SKKNI dan skill gap
    
    Args:
        skkni_id: SKKNI identifier
        skill_gap: String berisi skills yang missing
        top_k: Jumlah rekomendasi
    
    Returns:
        List of recommended courses dengan scoring
    """
    df_courses = load_maxy_courses()
    
    if df_courses is None or df_courses.empty:
        return []
    
    # Filter courses related to SKKNI
    relevant_courses = df_courses[
        df_courses['SKKNI_ID_Related'] == skkni_id
    ]
    
    # Parse skill gap
    gap_tokens = extract_skill_tokens(skill_gap)
    
    # Score courses
    scored_courses = []
    for _, course in relevant_courses.iterrows():
        course_skills = extract_skill_tokens(
            str(course['Skills_Covered'])
        )
        
        # Calculate skill coverage
        matched_skills = [
            gap for gap in gap_tokens
            if any(gap in cs or cs in gap for cs in course_skills)
        ]
        
        coverage_score = (
            len(matched_skills) / len(gap_tokens) 
            if gap_tokens else 0
        )
        
        # Bonus for level progression
        level_bonus = {
            'Beginner': 0.1,
            'Intermediate': 0.05,
            'Advanced': 0.0
        }.get(course.get('Level', ''), 0)
        
        final_score = coverage_score + level_bonus
        
        scored_courses.append({
            'CourseID': course['CourseID'],
            'Nama_Course': course['Nama_Course'],
            'Deskripsi': course['Deskripsi'],
            'Skills_Covered': course['Skills_Covered'],
            'Level': course['Level'],
            'Durasi': course['Durasi'],
            'URL': course['URL'],
            'relevance_score': final_score,
            'matched_skills': matched_skills,
            'gap_coverage': f"{len(matched_skills)}/{len(gap_tokens)}"
        })
    
    # Sort by relevance
    scored_courses.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    return scored_courses[:top_k]


def recommend_courses_from_profile(profile_text: str, top_k: int = 5):
    """
    Recommend courses directly dari profile text
    (fallback jika SKKNI belum dipetakan)
    """
    df_courses = load_maxy_courses()
    
    if df_courses is None or df_courses.empty:
        return []
    
    profile_tokens = extract_skill_tokens(profile_text)
    
    scored_courses = []
    for _, course in df_courses.iterrows():
        course_skills = extract_skill_tokens(
            str(course['Skills_Covered'])
        )
        
        # Simple matching
        matched = sum(
            1 for pt in profile_tokens
            if any(pt in cs or cs in pt for cs in course_skills)
        )
        
        score = matched / max(len(profile_tokens), 1)
        
        if score > 0:
            scored_courses.append({
                'CourseID': course['CourseID'],
                'Nama_Course': course['Nama_Course'],
                'Deskripsi': course['Deskripsi'],
                'Skills_Covered': course['Skills_Covered'],
                'Level': course['Level'],
                'Durasi': course['Durasi'],
                'URL': course['URL'],
                'relevance_score': score
            })
    
    scored_courses.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    return scored_courses[:top_k]


# ========================================
# utils/job_search.py
# ========================================
"""
Job Search Engine menggunakan Google Custom Search Engine
"""

import requests
from urllib.parse import urlparse
import streamlit as st
from config import GOOGLE_CSE_API_KEY, GOOGLE_CSE_ID

def search_jobs_google_cse(query: str, location: str = "", max_results: int = 10):
    """
    Search jobs menggunakan Google CSE
    
    Args:
        query: Job title atau skills
        location: Lokasi (optional)
        max_results: Jumlah hasil (max 10 per request)
    
    Returns:
        List of job postings
    """
    
    if not GOOGLE_CSE_API_KEY or GOOGLE_CSE_API_KEY == "YOUR_GOOGLE_CSE_API_KEY":
        st.warning("⚠️ Google CSE API key belum diatur di config.py")
        return []
    
    # Build search query
    search_query = f'"{query}"'
    
    if location:
        search_query += f' "{location}"'
    
    # Add job-specific keywords
    search_query += " (lowongan OR job OR vacancy OR hiring OR karir)"
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': GOOGLE_CSE_API_KEY,
        'cx': GOOGLE_CSE_ID,
        'q': search_query,
        'num': min(max_results, 10),
        'sort': 'date'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        jobs = []
        for item in data.get('items', []):
            jobs.append({
                'title': item.get('title', ''),
                'link': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'source': extract_domain(item.get('link', '')),
                'displayLink': item.get('displayLink', '')
            })
        
        return jobs
    
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching jobs: {e}")
        return []
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return []


def extract_domain(url: str) -> str:
    """Extract clean domain name dari URL"""
    try:
        domain = urlparse(url).netloc
        domain = domain.replace('www.', '')
        return domain
    except:
        return url


def build_job_search_query(okupasi_nama: str, skills: list, location: str = ""):
    """
    Build optimized Boolean search query
    
    Example:
        Input: okupasi="Data Analyst", skills=["python", "sql", "tableau"]
        Output: "Data Analyst" AND (python OR sql OR tableau) AND Jakarta
    """
    
    base_query = f'"{okupasi_nama.lower()}"'
    
    # Add top 3 skills
    if skills:
        top_skills = skills[:3]
        skills_str = " OR ".join([f'"{s}"' for s in top_skills])
        base_query += f" AND ({skills_str})"
    
    # Add location
    if location:
        base_query += f' AND "{location}"'
    
    return base_query


# ========================================
# utils/rl_engine.py
# ========================================
"""
Reinforcement Learning Engine untuk personalized recommendations
"""

import random
from collections import defaultdict

class RLRecommender:
    """
    Q-Learning based recommender system
    """
    
    def __init__(self, learning_rate=0.1, discount_factor=0.9, epsilon=0.2):
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon
    
    def get_state(self, user_profile):
        """
        Convert user profile to state representation
        
        Args:
            user_profile: Dict dengan skill_preferences, location_preferences, dll
        
        Returns:
            String state representation
        """
        top_skills = sorted(
            user_profile['skill_preferences'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        top_locations = sorted(
            user_profile['location_preferences'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:2]
        
        skills_str = '_'.join([s[0] for s in top_skills])
        loc_str = '_'.join([l[0] for l in top_locations])
        
        state = f"skills_{skills_str}_loc_{loc_str}"
        return state
    
    def get_reward(self, action):
        """
        Calculate reward based on user action
        
        Actions:
            - apply: +10 (strong positive signal)
            - view: +2 (mild interest)
            - reject: -5 (negative signal)
            - ignore: -1 (passive negative)
        """
        rewards = {
            'apply': 10,
            'view': 2,
            'reject': -5,
            'ignore': -1
        }
        return rewards.get(action, 0)
    
    def update_q_value(self, state, action, reward, next_state, q_table):
        """
        Q-learning update rule:
        Q(s,a) = Q(s,a) + α[r + γ max Q(s',a') - Q(s,a)]
        """
        current_q = q_table[state][action]
        
        max_next_q = max(q_table[next_state].values()) if q_table[next_state] else 0
        
        new_q = current_q + self.lr * (reward + self.gamma * max_next_q - current_q)
        
        q_table[state][action] = new_q
        
        return new_q
    
    def select_action(self, state, available_jobs, q_table):
        """
        Epsilon-greedy action selection
        
        Returns:
            Selected job (action)
        """
        if not available_jobs:
            return None
        
        # Exploration
        if random.random() < self.epsilon:
            return random.choice(available_jobs)
        
        # Exploitation
        job_scores = {
            job['LowonganID']: q_table[state].get(job['LowonganID'], 0)
            for job in available_jobs
        }
        
        if not job_scores:
            return random.choice(available_jobs)
        
        best_job_id = max(job_scores, key=job_scores.get)
        
        best_job = next(
            (j for j in available_jobs if j['LowonganID'] == best_job_id),
            None
        )
        
        return best_job or random.choice(available_jobs)