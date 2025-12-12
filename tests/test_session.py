"""Tests for session management."""

import json
from pathlib import Path

import pytest

from bnmpy import load_cookies, save_cookies
from bnmpy.session_manager import create_session_from_cookies


class TestSessionManagement:
    """Test session management functions."""

    def test_save_and_load_cookies(self, tmp_path: Path):
        """Test saving and loading cookies."""
        cookies = [
            {"name": "test_cookie", "value": "test_value", "domain": "example.com", "path": "/"},
        ]
        fingerprint = "test_fingerprint_123"

        cookie_file = tmp_path / "test_cookies.json"
        save_cookies(cookies, cookie_file, fingerprint)

        assert cookie_file.exists()

        loaded_cookies, loaded_fingerprint = load_cookies(cookie_file)
        assert len(loaded_cookies) == 1
        assert loaded_cookies[0]["name"] == "test_cookie"
        assert loaded_fingerprint == fingerprint

    def test_load_cookies_old_format(self, tmp_path: Path):
        """Test loading cookies in old format (just list)."""
        cookies = [
            {"name": "test_cookie", "value": "test_value", "domain": "example.com", "path": "/"},
        ]

        cookie_file = tmp_path / "test_cookies_old.json"
        with open(cookie_file, "w") as f:
            json.dump(cookies, f)

        loaded_cookies, fingerprint = load_cookies(cookie_file)
        assert len(loaded_cookies) == 1
        assert fingerprint is None

    def test_create_session_from_cookies(self):
        """Test creating requests session from cookies."""
        cookies = [
            {
                "name": "test_cookie",
                "value": "test_value",
                "domain": ".example.com",
                "path": "/",
            },
        ]

        session = create_session_from_cookies(cookies)
        assert session is not None
        assert len(session.cookies) > 0

