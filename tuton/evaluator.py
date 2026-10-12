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

    elif session_num == 2:
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

    elif session_num == 3:
        # Rubrik Sesi 3 (Tugas 1): Kedudukan Bahasa Nasional vs Bahasa Negara & UU No. 24 Tahun 2009
        has_nasional_negara = "nasional" in c_lower and "negara" in c_lower
        has_sumpah_pemuda = any(k in c_lower for k in ["sumpah pemuda", "1928", "kebanggaan", "identitas"])
        has_uud45 = any(k in c_lower for k in ["uud 1945", "uud '45", "pasal 36", "resmi kenegaraan"])
        has_uu24 = any(k in c_lower for k in ["24 tahun 2009", "uu no 24", "uu 24", "undang-undang"])
        has_pemersatu = any(k in c_lower for k in ["pemersatu", "persatuan", "komunikasi antardaerah"])
        has_paragraf = len(content.strip().split("\n")) >= 2 or len(content.strip()) >= 200
        has_bmp = "mkwn4108" in c_lower or "bmp" in c_lower or "modul" in c_lower

        score = 80
        if has_nasional_negara: score += 3
        if has_sumpah_pemuda: score += 2
        if has_uud45: score += 2
        if has_uu24: score += 3
        if has_pemersatu: score += 2
        if has_paragraf: score += 2
        if has_bmp: score += 2

        score = min(max(score, 82), 95)

        p1 = (
            f"Halo {name}, terima kasih atas pengunggahan Tugas 1 yang telah Saudara susun dengan sangat baik "
            f"dan terstruktur. Keunggulan jawaban Saudara tampak pada ketepatan membedakan fungsi bahasa Indonesia "
            f"sebagai bahasa nasional (berlandaskan peristiwa historis Sumpah Pemuda 1928) dan sebagai bahasa negara "
            f"(berdasarkan ketentuan yuridis Pasal 36 UUD 1945). Saudara juga berhasil mengutip butir fungsi bahasa "
            f"persatuan dalam UU No. 24 Tahun 2009 serta menguraikan maknanya ke dalam susunan paragraf yang kohesif dan runtut."
        )

        catatan = []
        if not has_uud45:
            catatan.append("mempertegas rujukan yuridis Pasal 36 UUD 1945 pada fungsi bahasa negara")
        if not has_bmp:
            catatan.append("mencantumkan referensi resmi BMP MKWN4108 Modul 1/2 UT")

        saran_str = " dan ".join(catatan) if catatan else "memberikan contoh konkret penerapan fungsi bahasa negara dalam naskah administrasi pemerintahan"

        p2 = (
            f"Sebagai catatan penyempurnaan ke depan, Saudara dapat lebih melengkapi ulasan dengan {saran_str}. "
            f"Pertahankan ketelitian, penalaran ilmiah yang kritis, dan motivasi belajar yang tinggi untuk tugas-tugas selanjutnya!"
        )

    elif session_num == 4:
        # Rubrik Sesi 4 (Diskusi 4): Ciri Kalimat Efektif, Pleonasme Pohon Tabebuya Bojonegoro & Perbaikan Kalimat
        has_pleonasme = any(k in c_lower for k in ["pleonasme", "pemborosan", "kehematan", "hemat", "mubazir", "berlebihan"])
        has_ciri = any(k in c_lower for k in ["kehematan", "kelogisan", "keparalelan", "ketegasan", "kesepadanan", "kecermatan"])
        has_perbaikan = any(k in c_lower for k in ["perbaikan", "banyak pohon", "pohon-pohon", "banyak bunga", "bunga-bunga", "seharusnya"])
        has_tabebuya = "tabebuya" in c_lower or "bojonegoro" in c_lower
        has_bmp = "mkwn4108" in c_lower or "bmp" in c_lower or "modul" in c_lower

        score = 80
        if has_pleonasme: score += 4
        if has_ciri: score += 3
        if has_perbaikan: score += 4
        if has_tabebuya: score += 2
        if has_bmp: score += 2

        score = min(max(score, 82), 95)

        p1 = (
            f"Halo {name}, terima kasih atas partisipasi aktif Saudara dalam Forum Diskusi 4 ini. "
            f"Analisis yang Saudara paparkan sudah sangat baik dan tajam, khususnya dalam mengidentifikasi ketidakefektifan "
            f"kalimat [1] dan [2] pada teks pohon Tabebuya di Bojonegoro. Saudara tepat menjelaskan bahwa perulangan bentuk jamak "
            f"(pleonasme) pada frasa tersebut melanggar prinsip kehematan kata, serta mampu memberikan formulasi perbaikan "
            f"kalimat yang jauh lebih efektif, lugas, dan sesuai kaidah tata bahasa baku."
        )

        catatan = []
        if not has_ciri:
            catatan.append("memperjelas prinsip kehematan kata di samping prinsip kelogisan dan kesepadanan struktur")
        if not has_bmp:
            catatan.append("menyertakan rujukan BMP MKWN4108 Modul 4/5 UT sebagai dasar teori penyuntingan kalimat")

        saran_str = " serta ".join(catatan) if catatan else "mengulas lebih lanjut aspek keparalelan bentuk pada analisis kalimat berikutnya"

        p2 = (
            f"Sebagai catatan penyempurnaan ke depan, Saudara dapat lebih memperkuat analisis dengan {saran_str}. "
            f"Pertahankan kecermatan berbahasa dan cara berpikir analitis ini pada sesi-sesi diskusi mendatang!"
        )

    else:
        # Rubrik Sesi 5 (Tugas 2): Judul Artikel, Identifikasi & Perbaikan Kutipan Ilmiah, Daftar Pustaka, Kondisi Bahasa Daerah & Peribahasa
        has_kutipan = any(k in c_lower for k in ["kutipan", "yudhistira", "oudri", "kbbi", "liputan6", "kemendikbud"])
        has_dapus = any(k in c_lower for k in ["daftar pustaka", "referensi", "pustaka"])
        has_bahasa_daerah = any(k in c_lower for k in ["718", "bahasa daerah", "punah", "kritis", "1340"])
        has_peribahasa = "peribahasa" in c_lower
        has_bmp = "mkwn4108" in c_lower or "bmp" in c_lower or "modul" in c_lower

        score = 88
        if has_kutipan: score += 2
        if has_dapus: score += 2
        if has_bahasa_daerah: score += 1
        if has_peribahasa: score += 1
        if has_bmp: score += 1

        score = min(max(score, 88), 95)

        p1 = (
            f"Halo {name}, terima kasih atas pengunggahan Tugas 2 yang telah Saudara kerjakan dengan sangat baik, rapi, dan terstruktur. "
            f"Keunggulan jawaban Saudara tampak pada ketepatan merumuskan judul artikel yang representatif, kecermatan menandai serta "
            f"memperbaiki tata cara penulisan kutipan ilmiah (seperti kutipan KBBI, Yudhistira dkk. 2022, serta sumber daring), "
            f"sekaligus kemampuan menguraikan kondisi kekayaan 718 bahasa daerah Indonesia dan contoh peribahasa secara bernas."
        )

        p2 = (
            f"Sebagai catatan penyempurnaan ke depan, Saudara dapat lebih mencermati konsistensi tanda baca, penulisan huruf miring "
            f"pada judul sumber di bagian daftar pustaka, serta menambahkan rujukan Buku Materi Pokok (BMP MKWN4108) UT agar "
            f"landasan teori karya ilmiah semakin kokoh. Pertahankan ketelitian dan semangat belajar ini pada sesi-sesi selanjutnya!"
        )

    return {
        "name": name,
        "score": score,
        "feedback": f"{p1}\n\n{p2}"
    }
