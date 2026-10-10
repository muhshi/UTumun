import pytest
from tuton.auth import is_session_expired_indicator

def test_session_expired_indicator_detection():
    assert is_session_expired_indicator("Sesi Anda telah habis. Silakan masuk lagi.") is True
    assert is_session_expired_indicator("Peringatan: sesi anda telah habis") is True
    assert is_session_expired_indicator("Selamat datang di Elearning UT") is False
    assert is_session_expired_indicator("") is False
