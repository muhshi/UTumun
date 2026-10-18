import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tuton.submitter import submit_single_grade_to_ut


@pytest.mark.anyio
async def test_submit_single_grade_to_ut_forum_invalid_cmid(monkeypatch):
    """Test jika CMID forum diskusi tidak ditemukan dalam konfigurasi kelas."""
    monkeypatch.setattr("tuton.submitter.get_forum_cmid", lambda cid, snum: None)

    res = await submit_single_grade_to_ut(
        course_id="413073",
        session_num=4,
        student_nim="041234567",
        score=90,
        feedback="Halo Budi, tanggapan Anda sangat baik.\n\nPerlu ditambahkan rujukan BMP.",
        student_name="Budi Santoso",
    )
    assert res["success"] is False
    assert "CMID forum diskusi tidak ditemukan" in res["message"]


@pytest.mark.anyio
async def test_submit_single_grade_to_ut_forum_topic_not_found(monkeypatch):
    """Test jika topik diskusi tidak ditemukan di halaman kelas UT."""
    monkeypatch.setattr("tuton.submitter.get_forum_cmid", lambda cid, snum: "88888")

    mock_page = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value=None)  # topic_href is None

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_p = MagicMock()
    mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_p)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr("tuton.submitter.async_playwright", lambda: mock_cm)
    monkeypatch.setattr("tuton.submitter.ensure_authenticated_page", AsyncMock())

    res = await submit_single_grade_to_ut(
        course_id="413073",
        session_num=4,
        student_nim="041234567",
        score=90,
        feedback="Halo Budi, tanggapan Anda sangat baik.\n\nPerlu ditambahkan rujukan BMP.",
        student_name="Budi Santoso",
    )
    assert res["success"] is False
    assert "Topik forum diskusi tidak ditemukan" in res["message"]


@pytest.mark.anyio
async def test_submit_single_grade_to_ut_forum_mocked_success(monkeypatch):
    """Test alur pengiriman nilai rating dan balasan feedback forum diskusi yang sukses."""
    monkeypatch.setattr("tuton.submitter.get_forum_cmid", lambda cid, snum: "88888")

    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_p = MagicMock()
    mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_p)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr("tuton.submitter.async_playwright", lambda: mock_cm)
    monkeypatch.setattr("tuton.submitter.ensure_authenticated_page", AsyncMock())

    # Mock evaluate calls
    def mock_evaluate(script, *args):
        if "discussionname" in script or "topic" in script:
            return "https://elearning.ut.ac.id/mod/forum/discuss.php?d=99999"
        elif "rateSelect" in script or "targetScore" in script:
            return {
                "success": True,
                "rated": True,
                "already_replied": False,
                "reply_href": "https://elearning.ut.ac.id/mod/forum/post.php?reply=12345",
            }
        elif "id_message" in script or "editor" in script or "submit" in script:
            return True
        return True

    mock_page.evaluate = AsyncMock(side_effect=mock_evaluate)

    mock_loc = AsyncMock()
    mock_loc.count = AsyncMock(return_value=1)
    mock_loc.click = AsyncMock()
    mock_page.locator = MagicMock(return_value=mock_loc)

    res = await submit_single_grade_to_ut(
        course_id="413073",
        session_num=4,
        student_nim="041234567",
        score=92,
        feedback="Halo Budi, argumen diskusi Anda sangat tepat.\n\nSaran saya perlu diperkaya teori dari BMP.",
        student_name="Budi Santoso",
    )
    assert res["success"] is True
    assert "berhasil" in res["message"].lower()


@pytest.mark.anyio
async def test_submit_single_grade_to_ut_forum_already_replied(monkeypatch):
    """Test jika balasan tutor sudah ada, sistem tidak mengirim balasan ganda tetapi tetap memastikan rating tersimpan."""
    monkeypatch.setattr("tuton.submitter.get_forum_cmid", lambda cid, snum: "88888")

    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_p = MagicMock()
    mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_p)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr("tuton.submitter.async_playwright", lambda: mock_cm)
    monkeypatch.setattr("tuton.submitter.ensure_authenticated_page", AsyncMock())

    def mock_evaluate(script, *args):
        if "discussionname" in script or "topic" in script:
            return "https://elearning.ut.ac.id/mod/forum/discuss.php?d=99999"
        elif "rateSelect" in script or "targetScore" in script:
            return {
                "success": True,
                "rated": True,
                "already_replied": True,
                "reply_href": None,
            }
        return True

    mock_page.evaluate = AsyncMock(side_effect=mock_evaluate)

    res = await submit_single_grade_to_ut(
        course_id="413073",
        session_num=4,
        student_nim="041234567",
        score=95,
        feedback="Halo Budi, luar biasa.\n\nPertahankan!",
        student_name="Budi Santoso",
    )
    assert res["success"] is True
    assert "berhasil" in res["message"].lower()
