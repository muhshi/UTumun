import pytest
from tuton.matcher import match_feedbacks_to_students, normalize_name, clean_student_name

def test_clean_student_name():
    assert clean_student_name("Re: Forum Diskusi.1 by AHMAD FADLI") == "AHMAD FADLI"
    assert clean_student_name("Forum Diskusi.2 by 058104929 SAFIRA DIAH") == "SAFIRA DIAH"
    assert clean_student_name("058988712 SYAHRUL RAMANDANA") == "SYAHRUL RAMANDANA"

def test_normalize_name():
    assert normalize_name("Nur 'Azizah") == "nur azizah"
    assert normalize_name("HABIBUR RAHMAN") == "habibur rahman"

def test_match_feedbacks_fuzzy():
    students = [
        {"name": "NUR 'AZIZAH", "nim": "057659672", "score": None, "feedback": None},
        {"name": "HABIBUR RAHMAN", "nim": "057934868", "score": "94", "feedback": None},
        {"name": "FADRI TRI HARTANTO", "nim": "059890447", "score": None, "feedback": None},
    ]
    tutor_posts = [
        {"author": "AINUR ROSYIDAH", "content": "Nur Azizah, jawaban Anda sudah sangat baik..."},
        {"author": "AINUR ROSYIDAH", "content": "Waalaikumsalam saudara Habiburrahman, tanggapan Anda tepat..."},
    ]

    matched = match_feedbacks_to_students(students, tutor_posts)
    
    # Check Nur Azizah matched despite apostrophe
    s1 = next(s for s in matched if s["nim"] == "057659672")
    assert s1["feedback"] is not None
    assert "Nur Azizah" in s1["feedback"]

    # Check Habibur Rahman matched despite compound name
    s2 = next(s for s in matched if s["nim"] == "057934868")
    assert s2["feedback"] is not None

    # Check Fadri has no feedback
    s3 = next(s for s in matched if s["nim"] == "059890447")
    assert s3["feedback"] is None
