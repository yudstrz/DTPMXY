"""
SKKNI Smart Matcher - Simplified Version
Menghubungkan CV → SKKNI/PON TIK → Rekomendasi Course (dari Excel)
"""

import pandas as pd
import streamlit as st
from typing import Dict, List
import re

class SKKNIMatcher:
    """
    Class untuk matching CV dengan SKKNI/PON TIK
    dan generate rekomendasi pembelajaran dari Excel
    """
    
    def __init__(self, df_pon: pd.DataFrame, df_courses: pd.DataFrame = None):
        """
        Args:
            df_pon: DataFrame PON TIK dari Excel
            df_courses: DataFrame Course dari Excel (opsional)
        """
        self.df_pon = df_pon
        self.df_courses = df_courses
    
    def get_okupasi_details(self, okupasi_id: str) -> Dict:
        """
        Ambil detail lengkap okupasi berdasarkan ID
        """
        okupasi_data = self.df_pon[self.df_pon['OkupasiID'] == okupasi_id]
        
        if okupasi_data.empty:
            return {}
        
        row = okupasi_data.iloc[0]
        
        # Parse keywords
        kuk_raw = str(row.get('Kuk_Keywords', ''))
        keywords = self._parse_keywords(kuk_raw)
        
        return {
            'okupasi_id': str(row.get('OkupasiID', 'N/A')),
            'okupasi_nama': str(row.get('Okupasi', 'N/A')),
            'area_fungsi': str(row.get('Area_Fungsi', 'N/A')),
            'unit_kompetensi': str(row.get('Unit_Kompetensi', 'N/A')),
            'kuk_keywords': keywords,
            'level': self._infer_level(row)
        }
    
    def calculate_skill_gap(self, user_skills: List[str], okupasi_id: str) -> Dict:
        """
        Hitung skill gap antara user dengan SKKNI
        """
        okupasi = self.get_okupasi_details(okupasi_id)
        
        if not okupasi:
            return {}
        
        required_skills = set(s.lower() for s in okupasi['kuk_keywords'])
        user_skills_lower = set(s.lower() for s in user_skills)
        
        missing = list(required_skills - user_skills_lower)
        owned = list(required_skills & user_skills_lower)
        
        gap_pct = (len(missing) / len(required_skills) * 100) if required_skills else 0
        
        # Prioritize skills
        priority = self._prioritize_skills(missing, okupasi['okupasi_nama'])
        
        return {
            'missing_skills': missing,
            'owned_skills': owned,
            'gap_percentage': round(gap_pct, 1),
            'priority_skills': priority
        }
    
    def generate_learning_path(self, okupasi_id: str, current_skills: List[str]) -> List[Dict]:
        """
        Generate learning path berdasarkan skill gap
        """
        gap_analysis = self.calculate_skill_gap(current_skills, okupasi_id)
        
        if not gap_analysis:
            return []
        
        missing = gap_analysis['missing_skills']
        priority = gap_analysis['priority_skills']
        
        # Split ke 3 fase
        phase_1 = priority[:3] if len(priority) >= 3 else priority
        phase_2 = priority[3:6] if len(priority) >= 6 else priority[3:]
        phase_3 = [s for s in missing if s not in priority][:3]
        
        learning_path = []
        
        if phase_1:
            learning_path.append({
                'phase': 1,
                'title': '🎯 Foundation Phase (Priority)',
                'skills': phase_1,
                'estimated_duration': '1-2 bulan',
                'focus': 'Core skills yang paling dibutuhkan pasar'
            })
        
        if phase_2:
            learning_path.append({
                'phase': 2,
                'title': '📈 Intermediate Phase',
                'skills': phase_2,
                'estimated_duration': '2-3 bulan',
                'focus': 'Spesialisasi dan tools lanjutan'
            })
        
        if phase_3:
            learning_path.append({
                'phase': 3,
                'title': '🚀 Advanced Phase',
                'skills': phase_3,
                'estimated_duration': '3-6 bulan',
                'focus': 'Expert-level skills dan certification'
            })
        
        return learning_path
    
    def get_recommended_courses(self, skills: List[str], top_n: int = 8) -> List[Dict]:
        """
        Ambil course recommendations dari Excel berdasarkan skills
        
        Returns:
            List of courses yang match dengan skills
        """
        if self.df_courses is None or self.df_courses.empty:
            return []
        
        skills_lower = set(s.lower() for s in skills)
        
        courses_with_score = []
        
        for _, row in self.df_courses.iterrows():
            course_skills_raw = str(row.get('Skills', ''))
            course_skills = set(self._parse_keywords(course_skills_raw))
            
            # Calculate match score
            matched = skills_lower & course_skills
            match_score = len(matched)
            
            if match_score > 0:
                courses_with_score.append({
                    'course_id': str(row.get('CourseID', 'N/A')),
                    'title': str(row.get('Judul', 'N/A')),
                    'instructor': str(row.get('Instructor', 'N/A')),
                    'price': str(row.get('Price', 'Gratis')),
                    'level': str(row.get('Level', 'All Levels')),
                    'url': str(row.get('URL', '#')),
                    'description': str(row.get('Deskripsi', '')),
                    'platform': str(row.get('Platform', 'Maxy Academy')),
                    'matched_skills': list(matched),
                    'match_score': match_score
                })
        
        # Sort by match score
        courses_with_score.sort(key=lambda x: x['match_score'], reverse=True)
        
        return courses_with_score[:top_n]
    
    def get_job_search_keywords(self, okupasi_id: str) -> List[str]:
        """
        Generate keywords untuk job search berdasarkan okupasi
        """
        okupasi = self.get_okupasi_details(okupasi_id)
        
        if not okupasi:
            return []
        
        keywords = []
        
        # 1. Nama okupasi
        keywords.append(okupasi['okupasi_nama'])
        
        # 2. Variasi nama
        variations = self._generate_job_title_variations(okupasi['okupasi_nama'])
        keywords.extend(variations)
        
        # 3. Top skills
        keywords.extend(okupasi['kuk_keywords'][:5])
        
        # Deduplicate
        keywords = list(dict.fromkeys([k.strip() for k in keywords if k.strip()]))
        
        return keywords
    
    # ========================================
    # Helper Methods
    # ========================================
    
    def _parse_keywords(self, kuk_raw: str) -> List[str]:
        """Parse keywords dari string, respecting parentheses"""
        if not isinstance(kuk_raw, str):
            return []
        
        keywords = []
        current_word = []
        paren_depth = 0
        
        # Parse char by char to handle parentheses
        for char in kuk_raw:
            if char == '(':
                paren_depth += 1
                current_word.append(char)
            elif char == ')':
                if paren_depth > 0:
                    paren_depth -= 1
                current_word.append(char)
            elif char in [',', ';', '|', '\n'] and paren_depth == 0:
                word = "".join(current_word).strip()
                if word:
                    keywords.append(word.lower())
                current_word = []
            else:
                # Replace newline with space if passing through
                if char == '\n':
                    current_word.append(' ')
                else:
                    current_word.append(char)
                
        # Handle last word
        if current_word:
            word = "".join(current_word).strip()
            if word:
                keywords.append(word.lower())
        
        return list(dict.fromkeys(keywords))
    
    def _infer_level(self, row: pd.Series) -> str:
        """Infer level dari okupasi"""
        okupasi_nama = str(row.get('Okupasi', '')).lower()
        
        if any(word in okupasi_nama for word in ['junior', 'entry', 'associate']):
            return 'Junior'
        elif any(word in okupasi_nama for word in ['senior', 'lead', 'principal', 'expert']):
            return 'Senior'
        else:
            return 'Mid-Level'
    
    def _prioritize_skills(self, skills: List[str], okupasi_nama: str) -> List[str]:
        """Prioritize skills berdasarkan relevansi"""
        high_priority = ['python', 'sql', 'java', 'javascript', 'react', 'aws', 
                        'docker', 'kubernetes', 'machine learning', 'data analysis']
        
        priority = []
        normal = []
        
        for skill in skills:
            if any(hp in skill.lower() for hp in high_priority):
                priority.append(skill)
            else:
                normal.append(skill)
        
        return priority + normal
    
    def _generate_job_title_variations(self, title: str) -> List[str]:
        """Generate variasi job title"""
        variations = []
        
        mappings = {
            'data scientist': ['data science', 'ds', 'data analyst'],
            'software engineer': ['software developer', 'programmer', 'swe'],
            'devops engineer': ['devops', 'site reliability engineer', 'sre'],
            'ui/ux designer': ['ui designer', 'ux designer', 'product designer'],
        }
        
        title_lower = title.lower()
        
        for key, vars in mappings.items():
            if key in title_lower:
                variations.extend(vars)
        
        return variations


# ========================================
# Helper Functions untuk Streamlit
# ========================================

def create_skkni_matcher(excel_path: str, sheet_pon: str, sheet_course: str = None) -> SKKNIMatcher:
    """
    Factory function untuk create matcher instance
    """
    try:
        df_pon = pd.read_excel(excel_path, sheet_name=sheet_pon, engine='openpyxl')
        
        df_courses = None
        if sheet_course:
            try:
                df_courses = pd.read_excel(excel_path, sheet_name=sheet_course, engine='openpyxl')
            except:
                st.warning(f"⚠️ Sheet '{sheet_course}' tidak ditemukan. Course recommendation dinonaktifkan.")
        
        return SKKNIMatcher(df_pon, df_courses)
    except Exception as e:
        st.error(f"❌ Gagal load data SKKNI: {e}")
        return None


def display_learning_path(learning_path: List[Dict]):
    """Display learning path dengan Streamlit"""
    if not learning_path:
        st.success("✅ Tidak ada skill gap yang signifikan!")
        return
    
    # st.markdown("### 📚 Learning Path Rekomendasi") # Header removed
    
    for phase in learning_path:
        p_num = phase['phase']
        
        # Determine container style/color based on phase
        if p_num == 1:
            container_func = st.info  # Blue for Foundation
            icon = "🎯"
        elif p_num == 2:
            container_func = st.success  # Green for Intermediate
            icon = "📈"
        else:
            container_func = st.warning  # Orange for Advanced
            icon = "🚀"
            
        with st.container():
            st.markdown(f"#### {icon} {phase['title']}")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                 st.markdown(f"**Fokus:** {phase['focus']}")
            with col2:
                 st.caption(f"⏱️ **Estimasi:** {phase['estimated_duration']}")
            
            # Use the color box for skills
            with container_func("Skills to Learn"):
                skills_text = ", ".join([f"**{s.title()}**" for s in phase['skills']])
                st.markdown(skills_text)
            
            st.write("") # Spacer


def display_skill_gap_chart(gap_analysis: Dict):
    """Display skill gap visualization"""
    if not gap_analysis:
        return
    
    try:
        import plotly.graph_objects as go
        
        owned = len(gap_analysis['owned_skills'])
        missing = len(gap_analysis['missing_skills'])
        
        fig = go.Figure(data=[
            go.Pie(
                labels=['Skills Dimiliki', 'Skills Gap'],
                values=[owned, missing],
                hole=.4,
                marker_colors=['#4CAF50', '#FF5252']
            )
        ])
        
        fig.update_layout(
            title=f"Skill Gap: {gap_analysis['gap_percentage']}%",
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        # Fallback jika plotly tidak tersedia
        st.metric("Skill Gap", f"{gap_analysis['gap_percentage']}%")