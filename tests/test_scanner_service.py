import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from tuton.db import Database
from tuton.scanner_service import ScannerService, scanner_service


def test_scanner_service_initial_state():
    service = ScannerService()
    assert service.is_running is False
    assert service.progress == 0
    assert service.message == "Siap"
    assert service.session_num is None
    assert service.course_id is None
    assert service.error is None
    assert service.task is None


def test_scanner_service_get_status():
    service = ScannerService()
    status = service.get_status()
    assert isinstance(status, dict)
    assert status == {
        "is_running": False,
        "progress": 0,
        "message": "Siap",
        "session_num": None,
        "course_id": None,
        "error": None,
    }


def test_scanner_service_start_scan_already_running():
    async def _test():
        service = ScannerService()
        service.is_running = True
        result = await service.start_scan(session_num=1, course_id="45934")
        assert result.get("status") == "error"
        assert "berjalan" in result.get("message", "").lower()

    asyncio.run(_test())


def test_scanner_service_dry_run_lifecycle():
    async def _test():
        db = Database(":memory:")
        db.init_db()
        service = ScannerService(db=db)

        result = await service.start_scan(session_num=1, course_id="45934", dry_run=True)
        assert result.get("status") == "started"

        # Await background task
        assert service.task is not None
        await service.task

        assert service.is_running is False
        assert service.progress == 100
        assert "selesai" in service.message.lower()
        assert service.error is None

        logs = db.get_scan_logs()
        assert len(logs) >= 2
        statuses = [log["status"] for log in logs]
        assert "started" in statuses
        assert "success" in statuses

    asyncio.run(_test())


def test_scanner_service_error_handling_when_browser_fails():
    async def _test():
        db = Database(":memory:")
        db.init_db()
        service = ScannerService(db=db)

        with patch("tuton.scanner_service.async_playwright") as mock_pw:
            mock_pw.side_effect = RuntimeError("Browser executable not found")

            result = await service.start_scan(session_num=1, course_id="45934", dry_run=False)
            assert result.get("status") == "started"

            assert service.task is not None
            await service.task

            assert service.is_running is False
            assert service.error is not None
            assert "Browser executable not found" in service.error

            logs = db.get_scan_logs()
            assert any(l["status"] == "error" for l in logs)

    asyncio.run(_test())


def test_scanner_service_mocked_full_scan():
    async def _test():
        db = Database(":memory:")
        db.init_db()
        service = ScannerService(db=db)

        mock_playwright_cm = AsyncMock()
        mock_pw_inst = AsyncMock()
        mock_playwright_cm.__aenter__.return_value = mock_pw_inst
        mock_playwright_cm.__aexit__.return_value = None

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_pw_inst.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        forum_data = {
            "course": {"id": "45934", "code": "MKWN4108.12", "name": "MKWN4108 PBIN Sesi 1"},
            "session": 1,
            "posts": [
                {"postId": "p0", "author": "Tutor Ainur", "content": "Topik diskusi", "rating": None},
                {
                    "postId": "p1",
                    "author": "Ahmad Dani (041234567)",
                    "content": "Menurut Halliday hakikat bahasa bersifat arbitrer dan konvensional.",
                    "rating": "88",
                },
            ],
        }

        with patch("tuton.scanner_service.async_playwright", return_value=mock_playwright_cm), \
             patch("tuton.scanner_service.ensure_authenticated_page", new_callable=AsyncMock) as mock_auth, \
             patch("tuton.scanner_service.scrape_session_forum", new_callable=AsyncMock) as mock_forum:

            mock_auth.return_value = True
            mock_forum.return_value = forum_data

            result = await service.start_scan(session_num=1, course_id="45934", dry_run=False)
            assert result.get("status") == "started"
            await service.task

            assert service.is_running is False
            assert service.progress == 100
            assert service.error is None

            # Verify students and submissions were stored in DB
            students = db.get_students(course_id="45934")
            assert len(students) >= 1
            assert any(s["nim"] == "041234567" for s in students)

            subs = db.get_submissions(course_id="45934", session_num=1)
            assert len(subs) >= 1
            assert subs[0]["student_nim"] == "041234567"
            assert subs[0]["score"] == 88

    asyncio.run(_test())


def test_scanner_service_mocked_assignment_scan():
    async def _test():
        db = Database(":memory:")
        db.init_db()
        service = ScannerService(db=db)

        mock_playwright_cm = AsyncMock()
        mock_pw_inst = AsyncMock()
        mock_playwright_cm.__aenter__.return_value = mock_pw_inst
        mock_playwright_cm.__aexit__.return_value = None

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_pw_inst.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        assign_data = {
            "course": {"id": "45934", "code": "MKWN4108.12", "name": "MKWN4108 PBIN Sesi 3"},
            "session": 3,
            "submissions": [
                {
                    "author": "Siti Rahma (049876543)",
                    "fileText": "Tugas 1 MKWN4108 Bahasa Indonesia",
                    "id": "sub123",
                }
            ],
        }

        with patch("tuton.scanner_service.async_playwright", return_value=mock_playwright_cm), \
             patch("tuton.scanner_service.ensure_authenticated_page", new_callable=AsyncMock) as mock_auth, \
             patch("tuton.scanner_service.scrape_session_assign", new_callable=AsyncMock) as mock_assign:

            mock_auth.return_value = True
            mock_assign.return_value = assign_data

            result = await service.start_scan(session_num=3, course_id="45934", dry_run=False)
            assert result.get("status") == "started"
            await service.task

            assert service.is_running is False
            assert service.progress == 100
            assert service.error is None

            students = db.get_students(course_id="45934")
            assert len(students) >= 1
            assert any(s["nim"] == "049876543" for s in students)

            subs = db.get_submissions(course_id="45934", session_num=3)
            assert len(subs) >= 1
            assert subs[0]["student_nim"] == "049876543"
            assert subs[0]["score"] is not None

    asyncio.run(_test())


def test_module_singleton():
    assert isinstance(scanner_service, ScannerService)


def test_scanner_service_uses_bundled_chromium_when_chrome_path_missing():
    async def _test():
        db = Database(":memory:")
        db.init_db()
        service = ScannerService(db=db)

        mock_playwright_cm = AsyncMock()
        mock_pw_inst = AsyncMock()
        mock_playwright_cm.__aenter__.return_value = mock_pw_inst
        mock_playwright_cm.__aexit__.return_value = None

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_pw_inst.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        with patch("tuton.scanner_service.CHROME_PATH", "/nonexistent/chromium/binary"), \
             patch("tuton.scanner_service.async_playwright", return_value=mock_playwright_cm), \
             patch("tuton.scanner_service.ensure_authenticated_page", new_callable=AsyncMock) as mock_auth, \
             patch("tuton.scanner_service.scrape_session_assign", new_callable=AsyncMock) as mock_assign:

            mock_auth.return_value = True
            mock_assign.return_value = {"submissions": []}

            await service.start_scan(session_num=3, course_id="45934", dry_run=False)
            await service.task

            launch_call_kwargs = mock_pw_inst.chromium.launch.call_args.kwargs
            assert "executable_path" not in launch_call_kwargs
            assert launch_call_kwargs.get("headless") is True
            assert "--no-sandbox" in launch_call_kwargs.get("args", [])

    asyncio.run(_test())
