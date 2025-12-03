"""
AI Career Assistant Chatbot Module
Menggunakan Gemini API untuk rekomendasi karir dan lowongan kerja
Dengan manajemen token yang efisien
"""

import streamlit as st
import requests
import json
from typing import List, Dict, Optional
from datetime import datetime

from config import GEMINI_API_KEY, GEMINI_MODEL


class CareerChatbot:
    """AI Career Assistant menggunakan Gemini API"""
    
    def __init__(self, api_key: str, model: str = "gemini-flash-latest"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        
        # Token limits untuk efisiensi
        self.MAX_INPUT_TOKENS = 4000  # Batas input untuk konteks
        self.MAX_OUTPUT_TOKENS = 800  # Batas output untuk respons
        self.CONTEXT_WINDOW = 3  # Hanya simpan 3 pesan terakhir
        
    def _build_system_prompt(self, user_profile: dict) -> str:
        """Build system prompt dengan informasi user yang ringkas"""
        
        okupasi = user_profile.get('okupasi_nama', 'Tidak diketahui')
        skill_gap = user_profile.get('skill_gap', 'Tidak ada data')
        lokasi = user_profile.get('lokasi', 'Indonesia')
        
        # Ringkas skill gap jika terlalu panjang
        if len(skill_gap) > 200:
            skills = skill_gap.split(',')[:5]
            skill_gap = ', '.join(skills) + '...'
        
        prompt = f"""Anda adalah AI Career Assistant untuk platform Digital Talent.

PROFIL USER (RINGKAS):
- Okupasi Target: {okupasi}
- Skill Gap Utama: {skill_gap}
- Lokasi: {lokasi}

TUGAS ANDA:
1. Berikan rekomendasi lowongan kerja yang relevan
2. Saran pengembangan karir berdasarkan skill gap
3. Tips interview dan persiapan karir
4. Jawab pertanyaan seputar karir di bidang TI/Digital

ATURAN:
- Jawaban SINGKAT dan PADAT (max 150 kata)
- Fokus pada ACTIONABLE ADVICE
- Gunakan emoji untuk readability
- Jika ditanya lowongan, sebutkan 2-3 posisi relevan dengan okupasi user
- Hindari penjelasan panjang, langsung ke poin penting

Gaya: Profesional namun ramah, seperti career mentor."""
        
        return prompt
    
    def _truncate_history(self, messages: List[Dict]) -> List[Dict]:
        """Potong history untuk menghemat token"""
        if len(messages) <= self.CONTEXT_WINDOW * 2:  # user + assistant pairs
            return messages
        
        # Ambil hanya N pesan terakhir (keep user-assistant pairs)
        return messages[-(self.CONTEXT_WINDOW * 2):]
    
    def _count_tokens_estimate(self, text: str) -> int:
        """Estimasi jumlah token (1 token ≈ 4 karakter untuk bahasa Indonesia)"""
        return len(text) // 4
    
    def _compress_message(self, text: str, max_tokens: int = 500) -> str:
        """Kompres pesan jika terlalu panjang"""
        estimated_tokens = self._count_tokens_estimate(text)
        
        if estimated_tokens <= max_tokens:
            return text
        
        # Potong teks dan tambahkan indikator
        max_chars = max_tokens * 4
        return text[:max_chars] + "... [dipotong untuk efisiensi]"
    
    def chat(self, user_message: str, user_profile: dict, chat_history: List[Dict]) -> Optional[str]:
        """
        Kirim chat ke Gemini API dengan manajemen token efisien
        
        Args:
            user_message: Pesan dari user
            user_profile: Dict berisi profil user (okupasi, skill_gap, dll)
            chat_history: List of message dicts dengan format {"role": "user/model", "parts": [{"text": "..."}]}
        
        Returns:
            Response text atau None jika error
        """
        
        try:
            # Compress user message
            compressed_message = self._compress_message(user_message, max_tokens=300)
            
            # Truncate history untuk efisiensi
            truncated_history = self._truncate_history(chat_history)
            
            # Build system instruction
            system_instruction = self._build_system_prompt(user_profile)
            
            # Prepare request
            url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
            
            # Build contents
            contents = truncated_history.copy()
            contents.append({
                "role": "user",
                "parts": [{"text": compressed_message}]
            })
            
            payload = {
                "contents": contents,
                "systemInstruction": {
                    "parts": [{"text": system_instruction}]
                },
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": self.MAX_OUTPUT_TOKENS,
                    "stopSequences": []
                },
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
                ]
            }
            
            # Send request
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract response
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    return candidate["content"]["parts"][0]["text"]
            
            return None
            
        except requests.exceptions.Timeout:
            st.error("⏱️ Request timeout. Coba lagi.")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"❌ API Error: {str(e)}")
            return None
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            return None
    
    def get_quick_suggestions(self, okupasi_nama: str) -> List[str]:
        """Generate quick suggestion buttons berdasarkan okupasi"""
        
        suggestions = [
            f"Lowongan apa yang cocok untuk {okupasi_nama}?",
            "Tips interview untuk posisi ini?",
            "Skill apa yang harus saya pelajari?",
            "Berapa gaji rata-rata untuk posisi ini?",
            "Bagaimana cara melamar kerja yang efektif?"
        ]
        
        return suggestions


def render_career_chatbot():
    """Render chatbot UI di Streamlit"""
    
    st.markdown("### 💬 Career Assistant AI")
    st.caption("Tanya apapun tentang karir, lowongan, atau pengembangan skill!")
    
    # Check if profile exists
    if not st.session_state.mapped_okupasi_id:
        st.warning("⚠️ Lengkapi profil Anda terlebih dahulu untuk mendapat rekomendasi yang akurat.")
        return
    
    # Initialize chatbot
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = CareerChatbot(GEMINI_API_KEY, GEMINI_MODEL)
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    # Prepare user profile
    user_profile = {
        'okupasi_nama': st.session_state.mapped_okupasi_nama,
        'skill_gap': st.session_state.skill_gap,
        'lokasi': st.session_state.form_lokasi or "Indonesia"
    }
    
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    
    # Quick suggestions
    if len(st.session_state.chat_messages) == 0:
        st.markdown("#### 🎯 Saran Pertanyaan:")
        
        suggestions = st.session_state.chatbot.get_quick_suggestions(
            st.session_state.mapped_okupasi_nama
        )
        
        cols = st.columns(2)
        for idx, suggestion in enumerate(suggestions[:4]):
            with cols[idx % 2]:
                if st.button(suggestion, key=f"suggest_{idx}", use_container_width=True):
                    st.session_state.pending_message = suggestion
                    st.rerun()
    
    # Handle pending message from button click
    if hasattr(st.session_state, 'pending_message'):
        user_input = st.session_state.pending_message
        delattr(st.session_state, 'pending_message')
    else:
        # Chat input
        user_input = st.chat_input("Ketik pertanyaan Anda di sini...")
    
    if user_input:
        # Add user message to display
        st.session_state.chat_messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Add to API history format
        st.session_state.chat_history.append({
            "role": "user",
            "parts": [{"text": user_input}]
        })
        
        # Get response
        with st.spinner("🤔 Sedang berpikir..."):
            response = st.session_state.chatbot.chat(
                user_input,
                user_profile,
                st.session_state.chat_history
            )
        
        if response:
            # Add assistant message
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": response
            })
            
            # Add to API history
            st.session_state.chat_history.append({
                "role": "model",
                "parts": [{"text": response}]
            })
        else:
            st.error("❌ Gagal mendapat respons. Coba lagi.")
        
        st.rerun()
    
    # Clear chat button
    if len(st.session_state.chat_messages) > 0:
        if st.button("🗑️ Hapus Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.chat_messages = []
            st.rerun()
    
    # Token usage info
    with st.expander("ℹ️ Info Token & Efisiensi"):
        total_tokens = sum(
            len(msg.get("parts", [{}])[0].get("text", "")) // 4 
            for msg in st.session_state.chat_history
        )
        
        st.markdown(f"""
        **Manajemen Token:**
        - Estimasi Token Terpakai: ~{total_tokens}
        - Batas Input: {st.session_state.chatbot.MAX_INPUT_TOKENS} tokens
        - Batas Output: {st.session_state.chatbot.MAX_OUTPUT_TOKENS} tokens
        - Context Window: {st.session_state.chatbot.CONTEXT_WINDOW} pesan terakhir
        
        **Optimisasi:**
        - ✅ Auto-compress pesan panjang
        - ✅ Truncate history otomatis
        - ✅ Sistem prompt ringkas
        - ✅ Response dibatasi 150 kata
        """)
