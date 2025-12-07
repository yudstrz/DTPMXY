# ========================================
# JOB SEARCH TAB (UPDATED WITH RSS FEED)
# ========================================

def render_job_search():
    """Render job search portals, Google CSE, and RSS feed recommendations"""
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
    
    # Create tabs for different job search methods
    tab_portal, tab_rss = st.tabs(["🌐 Job Portals", "📡 Remote Jobs (RSS)"])
    
    # ========================================
    # TAB 1: JOB PORTALS (Original)
    # ========================================
    with tab_portal:
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
        st.markdown("#### 🌐 Portal Lowongan Kerja")
        
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
        st.markdown("#### 🔍 Google Job Search")
        
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
    # TAB 2: RSS FEED JOBS (NEW)
    # ========================================
    with tab_rss:
        try:
            # Import RSS job matcher
            from rss_job_matcher import render_rss_job_recommendations
            
            # Get user skills from profile
            user_skills = extract_skill_tokens(st.session_state.profil_teks)
            
            # Get okupasi info
            okupasi_nama = st.session_state.mapped_okupasi_nama or "Data Scientist"
            unit_kompetensi = st.session_state.okupasi_info.get('unit_kompetensi', '')
            
            # Render RSS job recommendations
            render_rss_job_recommendations(
                user_skills=user_skills,
                okupasi_nama=okupasi_nama,
                unit_kompetensi=unit_kompetensi,
                okupasi_info=st.session_state.okupasi_info
            )
        
        except ImportError:
            st.error("❌ Modul `rss_job_matcher.py` tidak ditemukan!")
            st.info("""
            **Cara mengaktifkan fitur RSS Job Feed:**
            
            1. Simpan file `rss_job_matcher.py` di folder yang sama dengan `app.py`
            2. Install dependencies yang diperlukan:
               ```
               pip install feedparser beautifulsoup4
               ```
            3. Restart aplikasi Streamlit
            """)
        
        except Exception as e:
            st.error(f"❌ Error saat memuat RSS jobs: {e}")
            st.info("💡 Pastikan koneksi internet Anda stabil dan semua dependencies terinstall.")
