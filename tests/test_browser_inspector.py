"""Tests for browser inspector."""

import json
from pathlib import Path

import pytest

from bnmpy.browser_inspector import inspect_browser_session


class TestBrowserInspector:
    """Test browser inspection functionality."""

    @pytest.mark.browser
    def test_inspect_browser_session(self, tmp_path: Path):
        """
        Test browser inspection (requires manual interaction).

        This test opens a browser and requires manual captcha solving.
        Mark with @pytest.mark.browser to run separately.
        """
        result_file = tmp_path / "inspection_result.json"

        # This will open browser and wait for user interaction
        result = inspect_browser_session(result_file)

        assert result is not None
        assert "cookies" in result
        assert isinstance(result["cookies"], list)

        if result_file.exists():
            with open(result_file) as f:
                saved_result = json.load(f)
            assert saved_result["cookies"] == result["cookies"]

