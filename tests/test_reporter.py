import pytest
from tuton.reporter import (
    format_recap_summary_table,
    format_pending_names_list,
    format_pending_student_card,
)

def test_format_recap_summary_table():
    summary_data = [
        {
            "session": 1,
            "classes": [
                {"name": "Bahasa Indonesia 2137", "code": "2137", "total": 43, "completed": 41, "pending": 2},
                {"name": "Bahasa Indonesia 2141", "code": "2141", "total": 48, "completed": 48, "pending": 0},
            ]
        }
    ]
    table_md = format_recap_summary_table(summary_data)
    assert "Total Mhs" in table_md
    assert "Kurang (Pending)" in table_md
    assert "Bahasa Indonesia 2137" in table_md
    assert "2141" in table_md

def test_format_pending_student_card():
    student_eval = {
        "name": "Fadri Tri Hartanto",
        "nim": "059890447",
        "course_name": "Bahasa Indonesia 2145",
        "session": 1,
        "score": 90,
        "status_desc": "Belum ada nilai & belum ada feedback",
        "feedback": "Halo Fadri Tri Hartanto...\n\nSebagai catatan..."
    }
    card_md = format_pending_student_card(student_eval)
    assert "Fadri Tri Hartanto" in card_md
    assert "90" in card_md
    assert "```text" in card_md
    assert "Halo Fadri Tri Hartanto" in card_md

def test_format_pending_names_list():
    pending_grouped = {
        "Sesi 1 — Bahasa Indonesia 2137": [
            {"name": "Budi", "nim": "012345678", "score": None, "feedback": None}
        ],
        "Sesi 1 — Bahasa Indonesia 2141": []
    }
    names_md = format_pending_names_list(pending_grouped)
    assert "Budi" in names_md
    assert "012345678" in names_md
    assert "Semua mahasiswa sudah selesai" in names_md
