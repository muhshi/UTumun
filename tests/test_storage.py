import pytest
from tuton.storage import save_session_data, load_session_data

def test_storage_save_and_load(tmp_path, monkeypatch):
    import tuton.storage as storage
    monkeypatch.setattr(storage, "STORAGE_DIR", tmp_path)

    sample_courses = {
        "413073": {
            "name": "Bahasa Indonesia 2137",
            "total": 43,
            "completed": 43,
            "pending": 0
        }
    }

    saved_path = save_session_data(1, "forum", sample_courses)
    assert tmp_path.exists()

    loaded = load_session_data(1)
    assert loaded["session"] == 1
    assert loaded["type"] == "forum"
    assert "last_synced_at" in loaded
    assert loaded["courses"]["413073"]["completed"] == 43
