import feedparser
from bs4 import BeautifulSoup
import re
from typing import List, Dict
import streamlit as st
import time

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
    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        cleaned = soup.get_text(separator=" ", strip=True)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.lower()
    except Exception:
        return str(raw_html).lower()


def match_keywords(text: str, keywords: List[str]) -> List[str]:
    """Match keywords in text and return found matches"""
    if not text or not keywords:
        return []
    
    found = []
    text_lower = text.lower()
    
    for keyword in keywords:
        keyword_lower = keyword.lower().strip()
        if keyword_lower and keyword_lower in text_lower:
            found.append(keyword)
    
    return list(set(found))  # Remove duplicates


# =====================================================================================
# RSS FETCHING (SILENT MODE)
# =====================================================================================

def fetch_all_rss_silent(feeds: List[str] = RSS_FEEDS) -> tuple:
    """Fetch all jobs from RSS feeds silently (no status messages)"""
    all_jobs = []
    debug_info = {
        'total_feeds': len(feeds),
        'successful_feeds': 0,
        'failed_feeds': 0,
        'total_entries': 0,
        'feed_details': []
    }
    
    for url in feeds:
        feed_info = {
            'url': url,
            'status': 'pending',
            'entries': 0,
            'error': None
        }
        
        try:
            # Parse feed (silent)
            feed = feedparser.parse(url)
            
            # Check for errors
            if hasattr(feed, 'bozo') and feed.bozo:
                feed_info['error'] = str(getattr(feed, 'bozo_exception', 'Unknown error'))
                feed_info['status'] = 'error'
            else:
                feed_info['status'] = 'success'
            
            # Get entries
            entries_count = len(feed.entries)
            feed_info['entries'] = entries_count
            debug_info['total_entries'] += entries_count
            
            if entries_count == 0:
                feed_info['status'] = 'empty'
            else:
                debug_info['successful_feeds'] += 1
            
            # Extract jobs
            for entry in feed.entries:
                description = ""
                
                # Try multiple fields for description
                if hasattr(entry, "summary"):
                    description = entry.summary
                elif hasattr(entry, "description"):
                    description = entry.description
                elif hasattr(entry, "content") and len(entry.content) > 0:
                    description = entry.content[0].value
                
                job = {
                    "source": url.split("/")[2],
                    "title": getattr(entry, "title", "No Title"),
                    "link": getattr(entry, "link", "#"),
                    "description_html": description,
                    "published": getattr(entry, "published", "Unknown date")
                }
                
                all_jobs.append(job)
        
        except Exception as e:
            feed_info['status'] = 'failed'
            feed_info['error'] = str(e)
            debug_info['failed_feeds'] += 1
        
        debug_info['feed_details'].append(feed_info)
        time.sleep(0.3)  # Small delay between requests
    
    return all_jobs, debug_info


# =====================================================================================
# RSS FETCHING WITH DEBUG (VERBOSE MODE)
# =====================================================================================

def fetch_all_rss_debug(feeds: List[str] = RSS_FEEDS) -> tuple:
    """Fetch all jobs from RSS feeds with detailed debugging"""
    all_jobs = []
    debug_info = {
        'total_feeds': len(feeds),
        'successful_feeds': 0,
        'failed_feeds': 0,
        'total_entries': 0,
        'feed_details': []
    }
    
    for idx, url in enumerate(feeds, 1):
        feed_info = {
            'url': url,
            'status': 'pending',
            'entries': 0,
            'error': None
        }
        
        try:
            st.info(f"🔄 Fetching feed {idx}/{len(feeds)}: {url}")
            
            # Parse feed
            feed = feedparser.parse(url)
            
            # Check for errors
            if hasattr(feed, 'bozo') and feed.bozo:
                feed_info['error'] = str(getattr(feed, 'bozo_exception', 'Unknown error'))
                feed_info['status'] = 'error'
            else:
                feed_info['status'] = 'success'
            
            # Get entries
            entries_count = len(feed.entries)
            feed_info['entries'] = entries_count
            debug_info['total_entries'] += entries_count
            
            if entries_count == 0:
                st.warning(f"⚠️ {url}: No entries found")
                feed_info['status'] = 'empty'
            else:
                st.success(f"✅ {url}: Found {entries_count} jobs")
                debug_info['successful_feeds'] += 1
            
            # Extract jobs
            for entry in feed.entries:
                description = ""
                
                # Try multiple fields for description
                if hasattr(entry, "summary"):
                    description = entry.summary
                elif hasattr(entry, "description"):
                    description = entry.description
                elif hasattr(entry, "content") and len(entry.content) > 0:
                    description = entry.content[0].value
                
                job = {
                    "source": url.split("/")[2],
                    "title": getattr(entry, "title", "No Title"),
                    "link": getattr(entry, "link", "#"),
                    "description_html": description,
                    "published": getattr(entry, "published", "Unknown date")
                }
                
                all_jobs.append(job)
        
        except Exception as e:
            st.error(f"❌ Error fetching {url}: {str(e)}")
            feed_info['status'] = 'failed'
            feed_info['error'] = str(e)
            debug_info['failed_feeds'] += 1
        
        debug_info['feed_details'].append(feed_info)
        time.sleep(0.5)  # Small delay between requests
    
    return all_jobs, debug_info


# =====================================================================================
# JOB MATCHING ENGINE
# =====================================================================================

def process_jobs_with_profile(
    user_skills: List[str],
    user_occupations: List[str],
    unit_kompetensi: str = "",
    max_results: int = 50,
    show_debug: bool = False,
    silent_mode: bool = True
) -> tuple:
    """
    Process jobs and match with user profile
    Returns: (matched_jobs, debug_info)
    """
    
    # Fetch jobs from RSS feeds (silent or verbose)
    if silent_mode:
        raw_jobs, fetch_debug = fetch_all_rss_silent()
    else:
        raw_jobs, fetch_debug = fetch_all_rss_debug()
    
    # Show fetch statistics (only if debug mode)
    if show_debug and not silent_mode:
        st.info(f"""
        **📊 Fetch Statistics:**
        - Total feeds checked: {fetch_debug['total_feeds']}
        - Successful: {fetch_debug['successful_feeds']}
        - Failed: {fetch_debug['failed_feeds']}
        - Total jobs fetched: {fetch_debug['total_entries']}
        """)
    
    if not raw_jobs:
        if not silent_mode:
            st.warning("⚠️ Tidak ada job yang berhasil di-fetch dari RSS feeds")
        return [], fetch_debug
    
    # Prepare keywords for matching
    all_keywords = []
    all_keywords.extend([skill.lower().strip() for skill in user_skills if skill])
    all_keywords.extend([occ.lower().strip() for occ in user_occupations if occ])
    
    if unit_kompetensi:
        unit_keywords = [k.strip().lower() for k in re.split(r'[,;]+', unit_kompetensi) if k.strip()]
        all_keywords.extend(unit_keywords)
    
    # Remove duplicates and empty strings
    all_keywords = [k for k in list(set(all_keywords)) if k]
    
    # Show search info (only if debug mode)
    if show_debug and not silent_mode:
        st.info(f"🔍 Searching with {len(all_keywords)} keywords: {', '.join(all_keywords[:10])}")
    
    results = []
    processed_count = 0
    matched_count = 0
    
    # Create progress bar only if not silent
    if not silent_mode:
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    for idx, job in enumerate(raw_jobs):
        processed_count += 1
        
        # Update progress (only if not silent)
        if not silent_mode:
            progress = (idx + 1) / len(raw_jobs)
            progress_bar.progress(progress)
            status_text.text(f"Processing job {idx + 1}/{len(raw_jobs)}: {job['title'][:50]}...")
        
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
        title_score = len(matched_in_title) * 3
        desc_score = len(matched_in_desc) * 1
        skill_score = len(matched_skills) * 2
        occu_score = len(matched_occu) * 4
        
        total_score = title_score + desc_score + skill_score + occu_score
        
        # Only include jobs with at least 1 match
        if total_score > 0:
            matched_count += 1
            results.append({
                "source": job["source"],
                "title": job["title"],
                "link": job["link"],
                "published": job.get("published", "Unknown"),
                "description_preview": cleaned_desc[:300] + "..." if len(cleaned_desc) > 300 else cleaned_desc,
                "matched_skills": matched_skills,
                "matched_occupations": matched_occu,
                "match_score": total_score,
                "matched_keywords_count": len(matched_in_title) + len(matched_in_desc)
            })
    
    # Clear progress indicators (only if not silent)
    if not silent_mode:
        progress_bar.empty()
        status_text.empty()
    
    # Sort by match score
    results = sorted(results, key=lambda x: x["match_score"], reverse=True)
    
    # Update debug info
    fetch_debug['processed_jobs'] = processed_count
    fetch_debug['matched_jobs'] = matched_count
    fetch_debug['match_rate'] = f"{(matched_count/processed_count*100):.1f}%" if processed_count > 0 else "0%"
    
    # Show completion stats (only if debug mode and not silent)
    if show_debug and not silent_mode:
        st.success(f"""
        **✅ Processing Complete:**
        - Processed: {processed_count} jobs
        - Matched: {matched_count} jobs ({fetch_debug['match_rate']})
        - Returning top: {min(len(results), max_results)} results
        """)
    
    return results[:max_results], fetch_debug


# =====================================================================================
# STREAMLIT UI COMPONENT
# =====================================================================================

def render_rss_job_recommendations(
    user_skills: List[str],
    okupasi_nama: str,
    unit_kompetensi: str = "",
    okupasi_info: Dict = None,
    silent_mode: bool = True
):
    """Render RSS job recommendations in Streamlit"""
    
    st.markdown("### 🌐 Remote Job Recommendations")
    st.caption("Lowongan kerja remote dari berbagai platform internasional")
    
    # Debug mode toggle
    show_debug = st.checkbox("🐛 Show Debug Info", value=False)
    
    # Prepare occupation list
    user_occupations = [okupasi_nama] if okupasi_nama else []
    if okupasi_info:
        area_fungsi = okupasi_info.get('area_fungsi', '')
        if area_fungsi and area_fungsi not in user_occupations:
            user_occupations.append(area_fungsi)
    
    # Show search criteria
    with st.expander("🔍 Kriteria Pencarian", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📋 Okupasi:**")
            if user_occupations:
                for occ in user_occupations:
                    st.markdown(f"- {occ}")
            else:
                st.warning("⚠️ Tidak ada okupasi")
            
            st.markdown("**🎯 Unit Kompetensi:**")
            if unit_kompetensi:
                st.markdown(f"- {unit_kompetensi}")
            else:
                st.info("Tidak ada unit kompetensi")
        
        with col2:
            st.markdown("**💡 Skills yang Dicari:**")
            if user_skills:
                for skill in user_skills[:15]:
                    st.markdown(f"- {skill}")
                if len(user_skills) > 15:
                    st.caption(f"... dan {len(user_skills) - 15} skills lainnya")
            else:
                st.warning("⚠️ Tidak ada skills")
    
    # Validation
    if not user_skills and not user_occupations:
        st.error("❌ Tidak dapat mencari lowongan tanpa skills atau okupasi!")
        st.info("💡 Pastikan Anda sudah mengisi profil dengan lengkap di tab 'Profil Talenta'")
        return
    
    # Fetch and process jobs (silent or verbose based on mode)
    with st.spinner("🔍 Mencari lowongan kerja yang sesuai..."):
        matched_jobs, debug_info = process_jobs_with_profile(
            user_skills=user_skills,
            user_occupations=user_occupations,
            unit_kompetensi=unit_kompetensi,
            max_results=50,
            show_debug=show_debug,
            silent_mode=silent_mode
        )
    
    # Show debug info (only if requested)
    if show_debug:
        with st.expander("🐛 Debug Information", expanded=False):
            st.json(debug_info)
    
    # Check results
    if not matched_jobs:
        st.warning("⚠️ Tidak ada lowongan yang cocok ditemukan dari RSS feeds.")
        
        # Show helpful tips
        with st.expander("💡 Tips untuk mendapatkan lebih banyak hasil"):
            st.markdown("""
            **Kemungkinan penyebab:**
            1. Keywords terlalu spesifik
            2. RSS feeds sedang tidak tersedia
            3. Tidak ada lowongan baru yang match
            
            **Solusi:**
            1. Tambahkan lebih banyak skills di profil Anda
            2. Gunakan skills yang lebih umum (misal: "python" bukan "pytorch 2.0")
            3. Coba lagi nanti (RSS feeds di-update secara berkala)
            4. Gunakan tab "Job Portals" untuk alternatif pencarian
            """)
        
        # Show what was searched (only if debug)
        if show_debug:
            st.info(f"Searched with: {', '.join(user_skills[:10])} | {', '.join(user_occupations)}")
        
        return
    
    # Display results
    st.success(f"✅ Ditemukan **{len(matched_jobs)}** lowongan yang cocok!")
    
    # Statistics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Lowongan", len(matched_jobs))
    
    avg_score = sum(j['match_score'] for j in matched_jobs) / len(matched_jobs)
    col2.metric("Rata-rata Match Score", f"{avg_score:.1f}")
    
    unique_sources = len(set(job['source'] for job in matched_jobs))
    col3.metric("Sumber RSS", unique_sources)
    
    st.markdown("---")
    
    # Display jobs in cards
    for i, job in enumerate(matched_jobs, 1):
        with st.expander(
            f"**{i}. {job['title']}** (Score: {job['match_score']})",
            expanded=(i <= 3)
        ):
            col_job1, col_job2 = st.columns([3, 1])
            
            with col_job1:
                st.markdown(f"**Source:** `{job['source']}`")
                st.markdown(f"**Published:** {job.get('published', 'Unknown')}")
                st.markdown(f"**Match Score:** {job['match_score']} points")
                
                if job['matched_occupations']:
                    st.markdown("**✅ Matched Occupations:**")
                    st.markdown(", ".join([f"`{o}`" for o in job['matched_occupations']]))
                
                if job['matched_skills']:
                    st.markdown("**🎯 Matched Skills:**")
                    skills_display = job['matched_skills'][:15]
                    st.markdown(", ".join([f"`{s}`" for s in skills_display]))
                    if len(job['matched_skills']) > 15:
                        st.caption(f"... dan {len(job['matched_skills']) - 15} skills lainnya")
                
                with st.container():
                    st.markdown("**📄 Deskripsi:**")
                    st.caption(job['description_preview'])
            
            with col_job2:
                st.link_button(
                    "🔗 Lihat Lowongan",
                    job['link'],
                    use_container_width=True
                )
                
                st.markdown("---")
                st.metric("Keywords", job['matched_keywords_count'])
    
    # Tips
    st.markdown("---")
    with st.expander("💡 Tips Melamar Kerja Remote"):
        st.markdown("""
        **Tips untuk melamar lowongan remote:**
        
        1. **Perhatikan timezone** - Pastikan Anda bisa bekerja di timezone yang diminta
        2. **Siapkan portfolio online** - GitHub, portfolio website, atau LinkedIn yang lengkap
        3. **Komunikasi yang jelas** - Remote work membutuhkan komunikasi tertulis yang baik
        4. **Peralatan yang memadai** - Pastikan internet dan perangkat Anda mendukung
        5. **Highlight remote experience** - Jika pernah remote work, tonjolkan pengalaman tersebut
        
        **Red flags yang perlu diwaspadai:**
        - ❌ Meminta biaya pendaftaran
        - ❌ Tidak jelas detail perusahaan
        - ❌ Tawaran gaji yang terlalu tinggi/tidak realistis
        - ❌ Proses interview yang terlalu cepat tanpa verifikasi
        """)
