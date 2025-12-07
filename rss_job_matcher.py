import feedparser
from bs4 import BeautifulSoup
import re
from typing import List, Dict
import streamlit as st

# =====================================================================================
# RSS FEED SOURCES
# =====================================================================================
RSS_FEEDS = [
    "https://weworkremotely.com/remote-jobs.rss",
    "https://jobicy.com/feed/job_feed",
    "https://www.skipthedrive.com/feed/",
    "https://smartremotejobs.com/feed/all.rss",
    "https://www.freelancer.com/rss.xml",
    "https://golangprojects.com/rss.xml"
]

# =====================================================================================
# HELPER FUNCTIONS
# =====================================================================================

def clean_html(raw_html: str) -> str:
    """Clean HTML and extract plain text"""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    cleaned = soup.get_text(separator=" ", strip=True)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.lower()


def match_keywords(text: str, keywords: List[str]) -> List[str]:
    """Match keywords in text and return found matches"""
    if not text or not keywords:
        return []
    
    found = []
    text_lower = text.lower()
    
    for keyword in keywords:
        if keyword.lower() in text_lower:
            found.append(keyword)
    
    return list(set(found))  # Remove duplicates


# =====================================================================================
# RSS FETCHING
# =====================================================================================

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_all_rss(feeds: List[str] = RSS_FEEDS) -> List[Dict]:
    """Fetch all jobs from RSS feeds with caching"""
    all_jobs = []
    
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            
            for entry in feed.entries:
                # Extract description from various possible fields
                description = ""
                if hasattr(entry, "summary"):
                    description = entry.summary
                elif hasattr(entry, "description"):
                    description = entry.description
                elif hasattr(entry, "content") and len(entry.content) > 0:
                    description = entry.content[0].value
                
                all_jobs.append({
                    "source": url.split("/")[2],  # Extract domain name
                    "title": entry.title if hasattr(entry, "title") else "No Title",
                    "link": entry.link if hasattr(entry, "link") else "#",
                    "description_html": description,
                })
        
        except Exception as e:
            st.warning(f"⚠️ Gagal mengambil data dari {url}: {str(e)}")
            continue
    
    return all_jobs


# =====================================================================================
# JOB MATCHING ENGINE
# =====================================================================================

def process_jobs_with_profile(
    user_skills: List[str],
    user_occupations: List[str],
    unit_kompetensi: str = "",
    max_results: int = 20
) -> List[Dict]:
    """
    Process jobs and match with user profile
    
    Args:
        user_skills: List of user's skills (e.g., ["python", "pandas", "numpy"])
        user_occupations: List of user's occupations (e.g., ["data scientist"])
        unit_kompetensi: Additional unit kompetensi to match
        max_results: Maximum number of results to return
    
    Returns:
        List of matched jobs sorted by relevance score
    """
    
    # Fetch jobs from RSS feeds
    with st.spinner("🔄 Mengambil lowongan kerja dari RSS feeds..."):
        raw_jobs = fetch_all_rss()
    
    if not raw_jobs:
        return []
    
    # Prepare keywords for matching
    all_keywords = []
    all_keywords.extend([skill.lower() for skill in user_skills])
    all_keywords.extend([occ.lower() for occ in user_occupations])
    
    if unit_kompetensi:
        # Split unit kompetensi into individual keywords
        unit_keywords = [k.strip().lower() for k in unit_kompetensi.split(",")]
        all_keywords.extend(unit_keywords)
    
    # Remove duplicates
    all_keywords = list(set(all_keywords))
    
    results = []
    
    for job in raw_jobs:
        # Clean description
        cleaned_desc = clean_html(job["description_html"])
        title_lower = job["title"].lower()
        
        # Match in both title and description
        matched_in_title = match_keywords(title_lower, all_keywords)
        matched_in_desc = match_keywords(cleaned_desc, all_keywords)
        
        # Separate skill and occupation matches
        matched_skills = match_keywords(
            f"{title_lower} {cleaned_desc}", 
            user_skills
        )
        matched_occu = match_keywords(
            f"{title_lower} {cleaned_desc}", 
            user_occupations
        )
        
        # Calculate score with weighting
        # Title matches are worth more than description matches
        title_score = len(matched_in_title) * 3
        desc_score = len(matched_in_desc) * 1
        skill_score = len(matched_skills) * 2
        occu_score = len(matched_occu) * 4
        
        total_score = title_score + desc_score + skill_score + occu_score
        
        # Only include jobs with at least 1 match
        if total_score > 0:
            results.append({
                "source": job["source"],
                "title": job["title"],
                "link": job["link"],
                "description_preview": cleaned_desc[:300] + "..." if len(cleaned_desc) > 300 else cleaned_desc,
                "matched_skills": matched_skills,
                "matched_occupations": matched_occu,
                "match_score": total_score,
                "matched_keywords_count": len(matched_in_title) + len(matched_in_desc)
            })
    
    # Sort by match score (highest first)
    results = sorted(results, key=lambda x: x["match_score"], reverse=True)
    
    # Return top N results
    return results[:max_results]


# =====================================================================================
# STREAMLIT UI COMPONENT
# =====================================================================================

def render_rss_job_recommendations(
    user_skills: List[str],
    okupasi_nama: str,
    unit_kompetensi: str = "",
    okupasi_info: Dict = None
):
    """
    Render RSS job recommendations in Streamlit
    
    Args:
        user_skills: List of user's skills
        okupasi_nama: User's occupation name
        unit_kompetensi: Unit kompetensi string
        okupasi_info: Full okupasi information dictionary
    """
    
    st.markdown("### 🌐 Remote Job Recommendations (RSS Feeds)")
    st.caption("Lowongan kerja remote dari berbagai platform internasional")
    
    # Prepare occupation list
    user_occupations = [okupasi_nama]
    if okupasi_info:
        # Add area fungsi as additional occupation keyword
        area_fungsi = okupasi_info.get('area_fungsi', '')
        if area_fungsi:
            user_occupations.append(area_fungsi)
    
    # Show what we're searching for
    with st.expander("🔍 Kriteria Pencarian", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Okupasi:**")
            for occ in user_occupations:
                st.markdown(f"- {occ}")
            
            st.markdown("**Unit Kompetensi:**")
            if unit_kompetensi:
                st.markdown(f"- {unit_kompetensi}")
            else:
                st.info("Tidak ada unit kompetensi")
        
        with col2:
            st.markdown("**Skills yang Dicari:**")
            if user_skills:
                for skill in user_skills[:10]:  # Show max 10
                    st.markdown(f"- {skill}")
                if len(user_skills) > 10:
                    st.caption(f"... dan {len(user_skills) - 10} skills lainnya")
            else:
                st.info("Tidak ada skills")
    
    # Fetch and process jobs
    matched_jobs = process_jobs_with_profile(
        user_skills=user_skills,
        user_occupations=user_occupations,
        unit_kompetensi=unit_kompetensi,
        max_results=20
    )
    
    if not matched_jobs:
        st.warning("⚠️ Tidak ada lowongan yang cocok ditemukan dari RSS feeds.")
        st.info("💡 Tips: Pastikan koneksi internet Anda stabil. RSS feeds mungkin sedang down atau tidak ada lowongan baru.")
        return
    
    # Display results
    st.success(f"✅ Ditemukan **{len(matched_jobs)}** lowongan yang cocok!")
    
    # Statistics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Lowongan", len(matched_jobs))
    col2.metric("Rata-rata Match Score", f"{sum(j['match_score'] for j in matched_jobs) / len(matched_jobs):.1f}")
    
    # Count unique sources
    unique_sources = len(set(job['source'] for job in matched_jobs))
    col3.metric("Sumber RSS", unique_sources)
    
    st.markdown("---")
    
    # Display jobs in cards
    for i, job in enumerate(matched_jobs, 1):
        with st.expander(
            f"**{i}. {job['title']}** (Score: {job['match_score']})",
            expanded=(i <= 3)  # Expand first 3
        ):
            col_job1, col_job2 = st.columns([2, 1])
            
            with col_job1:
                st.markdown(f"**Source:** {job['source']}")
                st.markdown(f"**Match Score:** {job['match_score']} points")
                
                # Show matched keywords
                if job['matched_occupations']:
                    st.markdown("**✅ Matched Occupations:**")
                    st.markdown(", ".join([f"`{o}`" for o in job['matched_occupations']]))
                
                if job['matched_skills']:
                    st.markdown("**🎯 Matched Skills:**")
                    st.markdown(", ".join([f"`{s}`" for s in job['matched_skills'][:10]]))
                
                # Show description preview
                with st.container():
                    st.markdown("**📄 Deskripsi:**")
                    st.caption(job['description_preview'])
            
            with col_job2:
                st.link_button(
                    "🔗 Lihat Lowongan",
                    job['link'],
                    use_container_width=True
                )
                
                # Additional info
                st.markdown("---")
                st.metric("Keywords Match", job['matched_keywords_count'])
    
    # Additional tips
    st.markdown("---")
    with st.expander("💡 Tips Melamar Kerja Remote"):
        st.markdown("""
        **Tips untuk melamar lowongan remote:**
        
        1. **Perhatikan timezone** - Pastikan Anda bisa bekerja di timezone yang diminta
        2. **Siapkan portfolio online** - GitHub, portfolio website, atau LinkedIn yang lengkap
        3. **Komunikasi yang jelas** - Remote work membutuhkan komunikasi tertulis yang baik
        4. **Peralatan yang memadai** - Pastikan internet dan perangkat Anda mendukung remote work
        5. **Highlight remote experience** - Jika pernah remote work, tonjolkan pengalaman tersebut
        
        **Red flags yang perlu diwaspadai:**
        - Meminta biaya pendaftaran
        - Tidak jelas detail perusahaan
        - Tawaran gaji yang terlalu tinggi/tidak realistis
        - Proses interview yang terlalu cepat tanpa verifikasi
        """)
