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


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_tuton.db"
    db = Database(db_path=db_file)
    db.init_db()
    return db


def test_seed_session3_and_session4_ground_truth(test_db):
    from tuton.seed_db import seed_from_markdown_reports
    seed_from_markdown_reports(test_db)
    metrics = test_db.get_recap_metrics()

    # Sesi 3: 150 total, 134 completed, 16 pending
    s3_total = sum(metrics["matrix"][cid][3]["total"] for cid in metrics["matrix"])
    s3_completed = sum(metrics["matrix"][cid][3]["completed"] for cid in metrics["matrix"])
    s3_pending = sum(metrics["matrix"][cid][3]["pending"] for cid in metrics["matrix"])
    assert s3_total == 150
    assert s3_completed == 134
    assert s3_pending == 16

    # Sesi 4: 125 total, 12 completed, 113 pending
    s4_total = sum(metrics["matrix"][cid][4]["total"] for cid in metrics["matrix"])
    s4_completed = sum(metrics["matrix"][cid][4]["completed"] for cid in metrics["matrix"])
    s4_pending = sum(metrics["matrix"][cid][4]["pending"] for cid in metrics["matrix"])
    assert s4_total == 125
    assert s4_completed == 12
    assert s4_pending == 113

