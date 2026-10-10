import pytest
from tuton.config import COURSES, get_forum_cmid, get_assign_cmid, get_course_info

def test_courses_registry():
    assert len(COURSES) == 4
    course_ids = [c["id"] for c in COURSES]
    assert "413073" in course_ids
    assert "413077" in course_ids
    assert "413081" in course_ids
    assert "411401" in course_ids

def test_get_forum_cmid():
    # Sesi 1 cmid check
    assert get_forum_cmid(course_id="413073", session_num=1) == "47302993"
    assert get_forum_cmid(course_id="413077", session_num=1) == "47303711"
    # Sesi 2 cmid check
    assert get_forum_cmid(course_id="413073", session_num=2) == "47303004"
    assert get_forum_cmid(course_id="411401", session_num=2) == "46978750"
    # Sesi 4 cmid check
    assert get_forum_cmid(course_id="413073", session_num=4) == "47303026"
    assert get_forum_cmid(course_id="411401", session_num=4) == "46978799"

def test_get_assign_cmid():
    # Sesi 3 assign cmid check
    assert get_assign_cmid(course_id="413073", session_num=3) == "47303015"
    assert get_assign_cmid(course_id="411401", session_num=3) == "46978783"

def test_get_course_info():
    info = get_course_info("413073")
    assert info is not None
    assert info["code"] == "MKWN4108.2137"
    assert get_course_info("999999") is None
