from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest

from run_dashboard import build_parser, ensure_database_populated, print_greeting, main
from tuton.db import Database


def test_build_parser_defaults():
    parser = build_parser()
    args = parser.parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 8000
    assert args.reload is False


def test_build_parser_custom_args():
    parser = build_parser()
    args = parser.parse_args(["--host", "0.0.0.0", "--port", "8080", "--reload"])
    assert args.host == "0.0.0.0"
    assert args.port == 8080
    assert args.reload is True


def test_print_greeting(capsys):
    print_greeting("127.0.0.1", 8000, "data/tuton.db")
    captured = capsys.readouterr().out
    assert "SISTEM ASISTEN TUTOR ONLINE UT (MKWN4108 BAHASA INDONESIA)" in captured
    assert "Tutor: Ainur Rosyidah Azmie Putry, S.Pd., M.Pd. (NIP: 01007726)" in captured
    assert "[✓] Database terhubung: data/tuton.db" in captured
    assert "[✓] Tema Visual: Warm Honey & Sunlight Gold" in captured
    assert "[✓] Server berjalan di: http://127.0.0.1:8000" in captured
    assert "Buka tautan di atas pada Google Chrome untuk memulai evaluasi mahasiswa." in captured
    assert "Tekan Ctrl+C untuk menghentikan server." in captured


def test_ensure_database_populated_when_empty():
    mock_db = MagicMock(spec=Database)
    mock_db.get_students.return_value = []
    mock_db.get_submissions.return_value = []

    with patch("run_dashboard.seed_from_markdown_reports") as mock_seed:
        mock_seed.return_value = {"total_students": 10, "total_submissions": 20}
        ensure_database_populated(mock_db)
        mock_db.init_db.assert_called_once()
        mock_seed.assert_called_once_with(mock_db)


def test_ensure_database_populated_when_already_populated():
    mock_db = MagicMock(spec=Database)
    mock_db.get_students.return_value = [{"nim": "12345"}]
    mock_db.get_submissions.return_value = [{"id": 1}]

    with patch("run_dashboard.seed_from_markdown_reports") as mock_seed:
        ensure_database_populated(mock_db)
        mock_db.init_db.assert_called_once()
        mock_seed.assert_not_called()


@patch("run_dashboard.uvicorn.run")
@patch("run_dashboard.get_db")
@patch("run_dashboard.ensure_database_populated")
def test_main_execution(mock_ensure, mock_get_db, mock_uvicorn_run, capsys):
    mock_db = MagicMock()
    mock_db.db_path = "/Users/saiful/development/tuton_ut/data/tuton.db"
    mock_get_db.return_value = mock_db

    main(["--port", "8888"])

    mock_ensure.assert_called_once_with(mock_db)
    mock_uvicorn_run.assert_called_once_with(
        "app.main:app",
        host="127.0.0.1",
        port=8888,
        reload=False,
    )
    captured = capsys.readouterr().out
    assert "http://127.0.0.1:8888" in captured
