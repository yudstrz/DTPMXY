# 🚀 Quick Start Guide - Career Chatbot

## ⚡ Implementasi dalam 5 Menit

### Step 1: Download File Baru
Copy file `chatbot_assistant.py` ke folder project Anda:
```
project/
├── app.py                 ✅ (sudah ada)
├── config.py              ✅ (sudah ada)
├── chatbot_assistant.py   🆕 (file baru - COPY INI)
└── utils/
    └── skkni_matcher.py   ✅ (sudah ada)
```

### Step 2: Update app.py

**Tambahkan di bagian IMPORT** (baris ~50, setelah import utils):
```python
# Import chatbot module
try:
    from chatbot_assistant import render_career_chatbot
    CHATBOT_LOADED = True
except ImportError:
    st.warning("⚠️ Modul chatbot tidak ditemukan.")
    CHATBOT_LOADED = False
```

**Update fungsi `render_job_search()`** (baris ~730, sebelum Google CSE section):
```python
def render_job_search():
    # ... existing code untuk job portals ...
    
    st.markdown("---")
    
    # 🆕 TAMBAHKAN INI
    # ========================================
    # AI CAREER CHATBOT
    # ========================================
    
    if CHATBOT_LOADED:
        st.markdown("---")
        render_career_chatbot()
        st.markdown("---")
    
    # ========================================
    # END OF CHATBOT
    # ========================================
    
    # Google Custom Search (existing code)
    st.markdown("### 🔍 Google Job Search")
    # ... rest of code ...
```

### Step 3: Verifikasi API Key

Buka `config.py` dan pastikan sudah ada:
```python
GEMINI_API_KEY = "AIzaSyA8HdquILdHjGN0iGrpuII5ccFKPloZdmE"
GEMINI_MODEL = "gemini-1.5-flash"
```

### Step 4: Run & Test

```bash
streamlit run app.py
```

**Testing Flow:**
1. Upload CV di "Profil Talenta"
2. Klik "Simpan & Petakan ke SKKNI"
3. Buka tab "Career Assistant" → "Job Search"
4. Scroll ke bawah → Lihat "💬 Career Assistant AI"
5. Klik quick suggestion atau ketik pertanyaan!

---

## 📋 Checklist Implementasi

- [ ] File `chatbot_assistant.py` sudah di-copy ke project
- [ ] Import statement ditambahkan di `app.py`
- [ ] Function `render_job_search()` sudah diupdate
- [ ] API key sudah dikonfigurasi di `config.py`
- [ ] Aplikasi berjalan tanpa error
- [ ] Chatbot muncul di tab "Job Search"
- [ ] Quick suggestions berfungsi
- [ ] Chat input merespons dengan baik

---

## 🧪 Testing Standalone

Jika ingin test chatbot secara terpisah:

1. Copy file `test_chatbot.py` ke project
2. Run: `streamlit run test_chatbot.py`
3. Test dengan berbagai profil okupasi
4. Monitor token usage & cost

---

## ❓ Troubleshooting Cepat

### ❌ Error: Module 'chatbot_assistant' not found
**Solusi:** Pastikan file `chatbot_assistant.py` ada di folder yang sama dengan `app.py`

### ❌ Error: API key not valid
**Solusi:** 
1. Cek API key di `config.py`
2. Verifikasi di [Google AI Studio](https://makersuite.google.com/app/apikey)
3. Enable Gemini API jika belum

### ❌ Chatbot tidak muncul
**Solusi:**
1. Pastikan profil sudah dilengkapi (okupasi sudah dimapping)
2. Cek console untuk error messages
3. Verifikasi `CHATBOT_LOADED = True` di logs

### ❌ Response terlalu lambat
**Solusi:**
1. Check internet connection
2. Gemini Flash biasanya < 5 detik
3. Jika > 10 detik, ada masalah API/network

---

## 💡 Tips Penggunaan

### Pertanyaan yang Efektif:
✅ "Lowongan entry-level apa yang cocok untuk Data Scientist?"
✅ "Skill Python apa saja yang harus saya kuasai?"
✅ "Tips interview untuk posisi backend developer?"
✅ "Bagaimana cara menonjol di antara kandidat lain?"

### Hindari:
❌ Pertanyaan terlalu panjang (> 100 kata)
❌ Multiple questions dalam satu chat
❌ Topik di luar karir/pekerjaan

---

## 📊 Monitoring

### Check Token Usage:
1. Expand "ℹ️ Info Token & Efisiensi"
2. Monitor estimasi token terpakai
3. Clear chat jika sudah > 2000 tokens

### Cost Tracking:
- **Per chat:** ~Rp 4-5
- **100 chat/hari:** ~Rp 400-500
- **1000 chat/bulan:** ~Rp 4.000-5.000

Sangat terjangkau! 🎉

---

## 🎯 Next Steps

Setelah implementasi berhasil:

1. **Customize Prompts:** Edit system prompt di `chatbot_assistant.py` line 30-60
2. **Add Features:** Tambah quick suggestions di line 120-130
3. **Fine-tune:** Adjust token limits sesuai kebutuhan
4. **Monitor:** Track usage & optimize berdasarkan analytics

---

## 📞 Support

Jika ada masalah:
1. ✅ Baca CHATBOT_IMPLEMENTATION.md (dokumentasi lengkap)
2. ✅ Check Troubleshooting section
3. ✅ Test dengan `test_chatbot.py`
4. ✅ Review code comments di `chatbot_assistant.py`

---

## ✅ Summary

**3 File yang Dibutuhkan:**
1. `chatbot_assistant.py` - Module chatbot (NEW)
2. `app.py` - Main app (UPDATE 2 sections)
3. `config.py` - Configuration (VERIFY API key)

**Total Waktu:** 5-10 menit
**Lines of Code Added:** ~20 lines di app.py
**Dependencies Tambahan:** 0 (zero!)

**Result:** AI-powered career chatbot dengan token efficiency terbaik! 🚀

---

**Ready to Deploy!** 🎉