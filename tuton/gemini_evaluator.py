"""
Modul Evaluator Cerdas Berbasis Gemini API (gemini-3.8-flash)
Menghasilkan penilaian dan feedback 2 paragraf spesifik untuk mahasiswa MKWN4108 Bahasa Indonesia
berdasarkan Buku Materi Pokok (BMP) UT dan Rubrik Resmi Penskoran Tugas Tutorial.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
import httpx

from tuton.config import GEMINI_API_KEY
from tuton.evaluator import (
    evaluate_submission as fallback_evaluate_submission,
    clean_title_name,
    clean_unwanted_signatures,
)

logger = logging.getLogger("tuton.gemini_evaluator")

RUBRIK_TUGAS_2 = """
LEMBAR PEDOMAN PENSKORAN TUGAS TUTORIAL 2 (MKWN4108 BAHASA INDONESIA):
1.a. Ketepatan/kesesuaian judul dengan isi artikel (tema: Bahasa sebagai Warisan Kebudayaan Bangsa). [Maks 20 poin]
1.b. Temuan kutipan (diwarnai/ditandai) pada bagian-bagian tulisan (empat buah kutipan: KBBI, Yudhistira dkk. 2022, Liputan6.com, Itjen Kemendikbud). [Maks 20 poin]
1.c. Perbaikan kaidah penulisan kutipan yang salah dalam naskah (kutipan langsung/tidak langsung sesuai PUEBI/EYD). [Maks 10 poin]
2. Susunan 4 daftar pustaka sesuai kutipan yang terdapat dalam artikel (format APA style: Penulis. Tahun. Judul. Penerbit/URL). [Maks 20 poin]
3.a. Kondisi bahasa daerah di Indonesia: Berdasarkan artikel (Nabila Oudri), dari 718 bahasa daerah, kondisinya memprihatinkan (25 terancam punah, 6 kritis, 11 punah). [Maks 10 poin]
3.b. Sebuah peribahasa di luar yang ditulis dalam artikel beserta makna/konteks penggunaannya. [Maks 10 poin]
Penggunaan bahasa baku & kerapian: [Maks 10 poin]
Total Skor Maksimal: 100 poin. Rentang nilai wajar tugas mahasiswa aktif: 85 - 95.
"""

RUBRIK_DISKUSI_6 = """
LEMBAR PEDOMAN PENSKORAN FORUM DISKUSI 6 (MKWN4108 BAHASA INDONESIA):
Pokok Bahasan: Keterampilan Membaca Kritis (BMP MKWN4108 Modul 6) berdasarkan artikel ilmiah "Menumbuhkan Minat Belajar Matematika pada Anak dengan Pendekatan Kreatif" (Dewi Ayu Lu'lu'atu Fu'at & Cahyo Hasanudin).
1. Evaluasi Teks (Kekuatan & Kelemahan) [Maks 35 poin]:
   - Mengidentifikasi kekuatan teks: relevansi topik minat matematika anak, metode SLR & triangulasi data, ragam pendekatan kreatif (model POE, metode Gasing, media alat peraga, permainan edukatif).
   - Mengidentifikasi kelemahan teks: kesalahan tipografi/baku pada abstrak ('pendekatann', 'triagulasi', 'ketrampilan'), daftar pustaka memuat rujukan yang tidak relevan dengan matematika anak, kriteria inklusi/batasan SLR belum dirinci di abstrak.
2. Kualitas Rangkuman [Maks 25 poin]:
   - Rangkuman ditulis dengan kalimat sendiri (parafrasa baik/bebas plagiarisme), padat, merangkum esensi bahwa pendekatan kreatif mematahkan persepsi sulit/membosankan serta mengasah kemampuan berpikir kritis.
3. Kreativitas & Struktur Teras Berita (Lead) [Maks 30 poin]:
   - Lead berita berbasis peristiwa/pengamatan nyata di lingkungan sekitar, memikat pembaca, dan memenuhi unsur-unsur utama jurnalistik (5W+1H) secara efektif.
4. Kaidah Kebahasaan & Tata Tulis [Maks 10 poin]:
   - Menggunakan bahasa Indonesia baku, kalimat efektif, dan mematuhi PUEBI/EYD.
Total Skor Maksimal: 100 poin. Rentang nilai wajar mahasiswa aktif: 85 - 95.
"""

SYSTEM_PROMPT_TEMPLATE = """
Anda adalah dosen/tutor resmi mata kuliah MKWN4108 - Bahasa Indonesia di Universitas Terbuka (UT).

Tugas Anda:
Evaluasi lembar jawaban {session_title} mahasiswa secara teliti dan objektif berdasarkan Rubrik Penskoran Resmi UT.

PEDOMAN RUBRIK:
{rubrik}

STANDAR FORMAT FEEDBACK (WAJIB DIPATUHI SECARA KETAT):
1. Panjang feedback TEPAT 2 PARAGRAF (dipisahkan oleh dua baris baru \\n\\n).
2. PARAGRAF 1 (Apresiasi & Kelebihan Spesifik):
   - Wajib diawali sapaan pembuka: "{greeting_example}" (JANGAN mencantumkan NIM pada sapaan).
   - Sebutkan secara SPESIFIK apa yang bagus dari jawaban mahasiswa tersebut sesuai rubrik.
3. PARAGRAF 2 (Kekurangan Spesifik & Saran Perbaikan):
   - Ulas bagian mana dari jawabannya yang masih kurang lengkap atau belum tepat.
   - Ditutup langsung dengan kalimat pemacu semangat belajar untuk sesi-sesi selanjutnya.
4. ATURAN BEBAS SALAM/TANDA TANGAN (SANGAT PENTING):
   - DILARANG KERAS menyertakan salam penutup atau baris tanda tangan terpisah di akhir paragraf 2 (seperti "Salam sukses,", "Salam hangat,", "Asisten...", "Tutor...", atau nama dosen/asisten).
   - Feedback HARUS murni berakhir pada kalimat penutup pemacu semangat belajar di paragraf 2 tanpa baris tambahan apapun.
5. Gaya Bahasa: Akademis, santun, objektif, edukatif, dan alami khas dosen/tutor UT (hindari bahasa klise AI yang kaku).
6. Tentukan nilai numerik bulat (integer) antara 85 s.d. 95 yang proporsional dengan kelengkapan jawabannya.

Format Output WAJIB JSON:
{{
  "score": <integer 85-95>,
  "feedback": "<Paragraf 1>\\n\\n<Paragraf 2>",
  "strengths": "<ringkasan kelebihan singkat>",
  "improvements": "<ringkasan perbaikan singkat>"
}}
"""

def evaluate_with_gemini(
    student_name: str,
    submission_text: str,
    session_num: int = 5,
    previous_score: Optional[int] = None
) -> Dict[str, Any]:
    """
    Mengevaluasi tugas mahasiswa menggunakan Gemini 3.8 Flash.
    Jika API key tidak tersedia atau koneksi gagal, otomatis beralih ke rule-based evaluator.
    """
    clean_name = clean_title_name(student_name)
    
    # Jika bukan sesi 5 (tugas 2) atau jika teks pengumpulan terlalu pendek/kosong,
    # dan API key tidak ada, gunakan fallback
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY belum disetel, menggunakan fallback evaluator.")
        return fallback_evaluate_submission(clean_name, submission_text, session_num)

    # Potong teks submission jika terlalu panjang (maksimal 15.000 karakter cukup untuk tugas UT)
    trimmed_text = (submission_text or "").strip()
    if len(trimmed_text) > 15000:
        trimmed_text = trimmed_text[:15000] + "\n...[dipotong untuk efisiensi tokens]..."

    # Jika teks mahasiswa kosong/sangat sedikit, buat catatan berbasis metadata
    if len(trimmed_text) < 50:
        logger.info(f"Teks submission mahasiswa {clean_name} terlalu singkat, fallback ke evaluator.")
        return fallback_evaluate_submission(clean_name, submission_text, session_num)

    if session_num == 6:
        rubrik = RUBRIK_DISKUSI_6
        session_title = "Forum Diskusi 6"
        greeting_example = "Halo [Nama Mahasiswa], terima kasih atas tanggapan aktif Saudara dalam Forum Diskusi 6 ini..."
        sesi_label = f"Sesi {session_num} (Forum Diskusi 6)"
    elif session_num == 5:
        rubrik = RUBRIK_TUGAS_2
        session_title = "Tugas 2"
        greeting_example = "Halo [Nama Mahasiswa], terima kasih atas pengunggahan Tugas 2..."
        sesi_label = f"Sesi {session_num} (Tugas 2)"
    else:
        return fallback_evaluate_submission(clean_name, submission_text, session_num)

    system_instruction = SYSTEM_PROMPT_TEMPLATE.format(
        rubrik=rubrik,
        session_title=session_title,
        greeting_example=greeting_example,
    )
    user_prompt = f"""
Nama Mahasiswa: {clean_name}
Sesi: {sesi_label}
{f'Nilai Sesi Sebelumnya: {previous_score}' if previous_score else ''}

Berikut adalah isi tanggapan/jawaban yang disampaikan oleh mahasiswa:
---
{trimmed_text}
---

Evaluasilah lembar jawaban di atas dan kembalikan JSON persis sesuai format yang ditentukan.
"""

    candidate_models = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
    payload = {
        "contents": [
            {"parts": [{"text": user_prompt}]}
        ],
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = None
            for model_name in candidate_models:
                api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
                try:
                    resp = client.post(api_url, json=payload)
                    if resp.status_code == 200:
                        break
                    elif resp.status_code == 429:
                        logger.warning(f"Model {model_name} terkena limit quota (429), mencoba model alternatif...")
                        continue
                    else:
                        logger.warning(f"Model {model_name} status {resp.status_code}: {resp.text[:120]}")
                except Exception as ex:
                    logger.warning(f"Error request ke {model_name}: {ex}")
                    continue

            if not resp or resp.status_code != 200:
                logger.error("Seluruh model Gemini tidak dapat dijangkau / kehabisan kuota harian. Beralih ke fallback evaluator.")
                return fallback_evaluate_submission(clean_name, submission_text, session_num)

            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)

            score = int(parsed.get("score", 90))
            score = max(82, min(98, score))
            feedback = parsed.get("feedback", "").strip()

            if not feedback or "\n\n" not in feedback:
                feedback = (
                    f"Halo {clean_name}, terima kasih atas pengumpulan Tugas 2 yang telah Saudara susun dengan baik. "
                    f"Ulasan jawaban Saudara telah mencakup pokok-pokok penting yang diinstruksikan dalam rubrik tugas.\n\n"
                    f"Sebagai catatan perbaikan, Saudara disarankan untuk lebih menyempurnakan kaidah penulisan kutipan, "
                    f"format daftar pustaka sesuai gaya APA, dan memperkuat rujukan resmi BMP MKWN4108. Tetap semangat!"
                )
            else:
                feedback = clean_unwanted_signatures(feedback)

            return {
                "name": clean_name,
                "score": score,
                "feedback": feedback,
                "strengths": parsed.get("strengths", ""),
                "improvements": parsed.get("improvements", "")
            }

    except Exception as e:
        logger.error(f"Error calling Gemini API for {clean_name}: {e}")
        return fallback_evaluate_submission(clean_name, submission_text, session_num)
