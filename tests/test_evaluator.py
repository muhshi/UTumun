import pytest
from tuton.evaluator import evaluate_submission

def test_evaluate_submission_sesi1():
    student_content = """
    1. Ya, Budi dan Wati sedang berbahasa karena memenuhi hakikat bahasa sebagai sistem lambang bunyi.
    2. Sifat arbitrer bahasa berarti bebas manasuka, namun konvensional disepakati mereka berdua.
    3. Menurut M.A.K. Halliday ada fungsi instrumental, interaksional, personal, dan regulasi.
    BMP MKWN4108 modul 1.
    """
    res = evaluate_submission(student_name="FADRI TRI HARTANTO", content=student_content, session_num=1)
    assert res["score"] >= 85
    paragraphs = [p for p in res["feedback"].split("\n\n") if p.strip()]
    assert len(paragraphs) == 2
    assert "Halo Fadri Tri Hartanto" in paragraphs[0]
    assert "NIM" not in paragraphs[0]
    assert "kelebihan" in paragraphs[0].lower() or "baik" in paragraphs[0].lower()
    assert "catatan" in paragraphs[1].lower() or "saran" in paragraphs[1].lower()

def test_evaluate_submission_sesi2():
    student_content = """
    1. Keterampilan menyimak Ayu, membaca Cinta, berbicara Budi, dan menulis Dani terintegrasi secara padu.
    2. Teori membaca Frank Smith modul hal 1.30: interaksi informasi visual dan non-visual dalam mencari makna.
    3. Tahapan menulis Dani modul hal 1.35: prapenulisan, penulisan, dan pascapenulisan dengan elemen ringkasan dan rekomendasi lingkungan.
    """
    res = evaluate_submission(student_name="ROSI ANINDHITA", content=student_content, session_num=2)
    assert res["score"] >= 90
    paragraphs = [p for p in res["feedback"].split("\n\n") if p.strip()]
    assert len(paragraphs) == 2
    assert "Halo Rosi Anindhita" in paragraphs[0]

def test_evaluate_submission_sesi3():
    student_content = """
    1. Bahasa nasional bersumber dari Sumpah Pemuda 1928 sebagai lambang identitas dan kebanggaan.
       Bahasa negara bersumber dari UUD 1945 Pasal 36 sebagai bahasa resmi kenegaraan dan pengantar pendidikan.
    2. UU No. 24 Tahun 2009 butir 2 menetapkan bahasa persatuan dan sarana komunikasi antardaerah.
    BMP MKWN4108 modul 1.
    """
    res = evaluate_submission(student_name="SAFIRA DIAH AYUNINGTIAS", content=student_content, session_num=3)
    assert res["score"] >= 88
    paragraphs = [p for p in res["feedback"].split("\n\n") if p.strip()]
    assert len(paragraphs) == 2
    assert "Halo Safira Diah Ayuningtias" in paragraphs[0]
    assert "NIM" not in paragraphs[0]

def test_evaluate_submission_sesi4():
    student_content = """
    1. Kalimat [1] 'banyak pohon-pohon' dan [2] 'banyak bunga-bunga' tidak efektif karena pleonasme (pemborosan kata).
    2. Ciri kalimat efektif yang dilanggar adalah kehematan kata.
    3. Perbaikan kalimat: 'Pada bulan September di kota Bojonegoro banyak pohon Tabebuya berbunga.'
    BMP MKWN4108 modul 4.
    """
    res = evaluate_submission(student_name="ELLY SUSANTI AGUSTINA", content=student_content, session_num=4)
    assert res["score"] >= 90
    paragraphs = [p for p in res["feedback"].split("\n\n") if p.strip()]
    assert len(paragraphs) == 2
    assert "Halo Elly Susanti Agustina" in paragraphs[0]
    assert "NIM" not in paragraphs[0]


def test_evaluate_submission_sesi5():
    student_content = """
    1. Judul artikel: Keberagaman Bahasa Daerah di Indonesia.
    2. Kutipan ilmiah: Kamus Besar Bahasa Indonesia (KBBI) dan Yudhistira dkk. (2022) sudah diperbaiki sesuai kaidah kutipan langsung dan tidak langsung serta daftar pustaka.
    3. Terdapat 718 bahasa daerah di Indonesia yang sebagian mengalami keterancaman.
    4. Peribahasa: Di mana bumi dipijak, di situ langit dijunjung.
    BMP MKWN4108 modul 5.
    """
    res = evaluate_submission(student_name="ELLY SUSANTI AGUSTINA", content=student_content, session_num=5)
    assert res["score"] >= 90
    paragraphs = [p for p in res["feedback"].split("\n\n") if p.strip()]
    assert len(paragraphs) == 2
    assert "Halo Elly Susanti Agustina" in paragraphs[0]
    assert "NIM" not in paragraphs[0]
    assert "Tugas 2" in paragraphs[0]


def test_clean_unwanted_signatures():
    from tuton.evaluator import clean_unwanted_signatures

    raw_fb_1 = (
        "Halo Fikri Wahyudin, terima kasih atas pengunggahan Tugas 2.\n\n"
        "Meskipun secara keseluruhan tugas Anda sudah memuaskan, perbaiki daftar pustaka. Tetap semangat!\n\n"
        "Salam sukses,\n"
        "Asisten Penilai Ibu Ainur Rosyidah Azmie Putry"
    )
    cleaned_1 = clean_unwanted_signatures(raw_fb_1)
    assert "Asisten" not in cleaned_1
    assert "Ainur" not in cleaned_1
    assert "Salam sukses" not in cleaned_1
    assert cleaned_1 == (
        "Halo Fikri Wahyudin, terima kasih atas pengunggahan Tugas 2.\n\n"
        "Meskipun secara keseluruhan tugas Anda sudah memuaskan, perbaiki daftar pustaka. Tetap semangat!"
    )

    raw_fb_2 = (
        "Halo Parlaungan, terima kasih atas tanggapan Anda.\n\n"
        "Perhatikan kaidah kutipan. Terus pertahankan semangat belajar!\n\n"
        "Salam,\n"
        "Asisten Dosen Penilai MKWN4108 Bahasa Indonesia"
    )
    cleaned_2 = clean_unwanted_signatures(raw_fb_2)
    assert "Asisten" not in cleaned_2
    assert "Dosen Penilai" not in cleaned_2
    assert cleaned_2 == (
        "Halo Parlaungan, terima kasih atas tanggapan Anda.\n\n"
        "Perhatikan kaidah kutipan. Terus pertahankan semangat belajar!"
    )

    # Clean text without signatures remains untouched
    raw_fb_3 = "Halo Mahasiswa, p1.\n\nIni masukan p2. Semangat selalu!"
    assert clean_unwanted_signatures(raw_fb_3) == raw_fb_3



