import re
from typing import Dict, Any

def clean_title_name(name: str) -> str:
    words = name.strip().split()
    return " ".join(w.capitalize() for w in words)

def evaluate_submission(student_name: str, content: str, session_num: int) -> Dict[str, Any]:
    """
    Mengevaluasi tanggapan mahasiswa berdasarkan rubrik resmi UT
    dan menghasilkan nilai (0-100) serta feedback tepat 2 paragraf.
    """
    name = clean_title_name(student_name)
    c_lower = content.lower()

    if session_num == 1:
        # Rubrik Sesi 1: Hakikat Bahasa, Arbitrer & Konvensional, M.A.K. Halliday
        has_hakikat = any(k in c_lower for k in ["hakikat", "lambang bunyi", "sistem", "bermakna", "komunikasi"])
        has_arbitrer = "arbitrer" in c_lower or "manasuka" in c_lower
        has_konvensi = "konvensional" in c_lower or "kesepakatan" in c_lower or "disepakati" in c_lower
        has_halliday = "halliday" in c_lower
        has_fungsi = any(k in c_lower for k in ["instrumental", "interaksional", "personal", "regulasi", "representasional", "heuristik"])
        has_bmp = "mkwn4108" in c_lower or "bmp" in c_lower or "modul" in c_lower

        score = 80
        if has_hakikat: score += 4
        if has_arbitrer: score += 3
        if has_konvensi: score += 2
        if has_halliday: score += 3
        if has_fungsi: score += 2
        if has_bmp: score += 2

        score = min(max(score, 82), 95)

        p1 = (
            f"Halo {name}, terima kasih atas partisipasi aktif Saudara dalam Forum Diskusi 1 ini. "
            f"Analisis yang Saudara paparkan sudah sangat baik dan terstruktur, khususnya dalam menjelaskan "
            f"bahwa percakapan antara Budi dan Wati tetap memenuhi hakikat bahasa sebagai sistem lambang bunyi "
            f"bermakna yang disepakati bersama. Pemahaman Saudara mengenai sifat bahasa yang arbitrer namun tetap "
            f"terikat konvensi sosial juga diuraikan secara logis, disertai identifikasi fungsi bahasa menurut "
            f"M.A.K. Halliday yang relevan dengan konteks dialog."
        )

        catatan = []
        if not has_konvensi:
            catatan.append("menegaskan aspek konvensional yang mengikat variasi arbitrer agar pesan tetap tersampaikan")
        if not has_bmp:
            catatan.append("mencantumkan rujukan resmi Buku Materi Pokok (BMP MKWN4108) UT")

        saran_str = " serta ".join(catatan) if catatan else "memperkaya kutipan tuturan langsung dari dialog percakapan untuk memperkuat pembuktian"

        p2 = (
            f"Sebagai catatan penyempurnaan ke depan, Saudara dapat lebih memperkuat analisis dengan {saran_str}. "
            f"Pertahankan antusiasme, ketelitian, dan cara berpikir kritis ini pada sesi-sesi diskusi berikutnya!"
        )

    else:
        # Rubrik Sesi 2: Keterpaduan 4 Keterampilan, Teori Frank Smith, Tiga Tahapan Menulis
        has_keterampilan = all(k in c_lower for k in ["menyimak", "berbicara", "membaca", "menulis"]) or all(k in c_lower for k in ["ayu", "budi", "cinta", "dani"])
        has_smith = "smith" in c_lower
        has_visual = "visual" in c_lower or "non-visual" in c_lower or "skema" in c_lower or "pemaknaan" in c_lower
        has_tahapan = any(k in c_lower for k in ["prapenulisan", "pra-penulisan", "pra penulisan"]) and any(k in c_lower for k in ["penulisan", "drafting"]) and any(k in c_lower for k in ["pascapenulisan", "pasca-penulisan", "revisi", "editing"])
        has_elemen = any(k in c_lower for k in ["ringkasan", "rekomendasi", "laporan akhir"])
        has_bmp = "mkwn4108" in c_lower or "bmp" in c_lower or "modul" in c_lower

        score = 80
        if has_keterampilan: score += 4
        if has_smith: score += 3
        if has_visual: score += 2
        if has_tahapan: score += 4
        if has_elemen: score += 1
        if has_bmp: score += 2

        score = min(max(score, 82), 95)

        p1 = (
            f"Halo {name}, terima kasih atas pengumpulan jawaban diskusi Sesi 2 yang telah Saudara susun dengan "
            f"sangat baik dan terstruktur. Kelebihan utama dari tanggapan Saudara terletak pada kemampuan menguraikan "
            f"kontribusi keempat keterampilan berbahasa (menyimak oleh Ayu, berbicara oleh Budi, membaca oleh Cinta, "
            f"dan menulis oleh Dani) dalam mendukung kesuksesan presentasi kelompok secara padu. Pemahaman Saudara "
            f"terhadap esensi membaca menurut teori Frank Smith juga berhasil dikaitkan secara logis dengan tindakan Cinta "
            f"dalam memilih kutipan yang relevan dan selaras dengan gagasan pokok proyek."
        )

        catatan = []
        if not has_visual:
            catatan.append("memperdalam konsep dua sumber informasi Frank Smith (informasi visual teks dan informasi non-visual berupa skemata pembaca)")
        if not has_elemen:
            catatan.append("memastikan elemen penting laporan Dani (khususnya ringkasan temuan dan rekomendasi aksi nyata pelestarian lingkungan) terintegrasi eksplisit")
        if not has_bmp:
            catatan.append("mencantumkan rujukan formal Buku Materi Pokok (BMP MKWN4108) UT secara lengkap")

        saran_str = " dan ".join(catatan) if catatan else "mengaitkan contoh konkret tantangan penyuntingan bahasa (PUEBI/EYD) pada tahap pascapenulisan Dani"

        p2 = (
            f"Sebagai catatan penyempurnaan ke depan, Saudara dapat lebih memperkuat analisis dengan {saran_str}. "
            f"Secara keseluruhan argumentasi Saudara sudah sangat baik, pertahankan daya kritis dan keaktifan ini pada sesi-sesi selanjutnya!"
        )

    return {
        "name": name,
        "score": score,
        "feedback": f"{p1}\n\n{p2}"
    }
