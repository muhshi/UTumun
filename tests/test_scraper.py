import pytest
from tuton.scraper import build_flat_topic_url, parse_post_author_and_nim

def test_build_flat_topic_url():
    url_with_hash = "https://elearning.ut.ac.id/mod/forum/discuss.php?d=11190918#p122494901"
    assert build_flat_topic_url(url_with_hash) == "https://elearning.ut.ac.id/mod/forum/discuss.php?d=11190918&mode=1"

    url_plain = "https://elearning.ut.ac.id/mod/forum/discuss.php?d=12345"
    assert build_flat_topic_url(url_plain) == "https://elearning.ut.ac.id/mod/forum/discuss.php?d=12345&mode=1"

def test_parse_post_author_and_nim():
    author, nim = parse_post_author_and_nim("Re: Forum Diskusi.1 by 058104929 SAFIRA DIAH", "Halo...")
    assert author == "SAFIRA DIAH"
    assert nim == "058104929"

    author2, nim2 = parse_post_author_and_nim("ROSI ANINDHITA", "NIM: 057625959 dari Prodi Sistem Informasi")
    assert author2 == "ROSI ANINDHITA"
    assert nim2 == "057625959"

def test_build_assignment_grading_url():
    from tuton.scraper import build_assignment_grading_url
    url = build_assignment_grading_url("12345", perpage=100)
    assert "id=12345" in url
    assert "action=grading" in url
    assert "perpage=100" in url

def test_parse_assignment_grade_and_status():
    from tuton.scraper import parse_assignment_grade_and_status
    score, status = parse_assignment_grade_and_status("85.00")
    assert score == 85
    assert status == "completed"

    score, status = parse_assignment_grade_and_status("92.5")
    assert score == 92.5
    assert status == "completed"

    score, status = parse_assignment_grade_and_status("80,00 / 100")
    assert score == 80
    assert status == "completed"

    score, status = parse_assignment_grade_and_status("-")
    assert score is None
    assert status == "pending"

    score, status = parse_assignment_grade_and_status("")
    assert score is None
    assert status == "pending"

    score, status = parse_assignment_grade_and_status("Grade User grade / 100.00")
    assert score is None
    assert status == "pending"


def test_clean_html_feedback():
    from tuton.scraper import clean_html_feedback
    raw = '<div class="paragraph normal"><span>Halo Widyawati, terima kasih.</span></div>\n<div class="paragraph normal"><span>Kelebihan: Sangat rapi.</span></div>'
    cleaned = clean_html_feedback(raw)
    assert "Halo Widyawati, terima kasih." in cleaned
    assert "Kelebihan: Sangat rapi." in cleaned
    assert "<div" not in cleaned
    assert clean_html_feedback("Feedback comments") == ""
