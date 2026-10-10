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
