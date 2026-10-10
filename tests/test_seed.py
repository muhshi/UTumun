from pathlib import Path
import pytest
from tuton.db import Database
from tuton.seed_db import seed_from_markdown_reports


def test_seed_from_markdown_reports():
    """Menguji fungsi seeder historis dari laporan markdown dan file session."""
    test_db_path = Path("data/test_seed.db")
    if test_db_path.exists():
        test_db_path.unlink()

    try:
        db = Database(db_path=test_db_path)
        db.init_db()

        summary = seed_from_markdown_reports(db)
        submissions = db.get_submissions()

        # Assert submissions count > 50
        assert len(submissions) > 50

        # Assert metrics total_students > 50
        metrics = db.get_recap_metrics()
        assert metrics["total_students"] > 50

        # Verifikasi kelengkapan sesi 1 s.d. 4
        s1_subs = db.get_submissions(session_num=1)
        assert len(s1_subs) > 0

        s2_subs = db.get_submissions(session_num=2)
        assert len(s2_subs) > 0

        s3_subs = db.get_submissions(session_num=3)
        assert len(s3_subs) > 0

        s4_subs = db.get_submissions(session_num=4)
        assert len(s4_subs) > 0

    finally:
        if test_db_path.exists():
            test_db_path.unlink()
