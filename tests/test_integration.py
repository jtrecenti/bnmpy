"""Integration tests that verify end-to-end functionality."""

import json
from pathlib import Path

import pytest

from bnmpy import BNMPAPIClient, get_session_with_playwright, load_cookies
from bnmpy.browser_inspector import capture_api_request


class TestIntegration:
    """Integration tests for full workflow."""

    @pytest.mark.integration
    def test_full_workflow_with_saved_cookies(self):
        """
        Test full workflow: load cookies -> create client -> make API call.

        Requires cookies.json file with valid session.
        """
        cookies_file = Path("cookies.json")
        if not cookies_file.exists():
            pytest.skip("cookies.json not found")

        # Load cookies
        cookies, fingerprint = load_cookies(cookies_file)
        assert len(cookies) > 0, "No cookies found"

        # Create client
        client = BNMPAPIClient(cookies=cookies, fingerprint=fingerprint)

        # Make API call
        response = client.pesquisa_pecas_filter(
            busca_orgao_recursivo=False,
            orgao_expeditor={},
            id_estado=2,
            page=0,
            size=10,
        )

        # Verify response
        assert response is not None
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(list(response.headers.items())[:5])}")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success! Response type: {type(data)}")
            if isinstance(data, dict):
                print(f"  Keys: {list(data.keys())}")
            return True
        elif response.status_code == 401:
            error_data = response.json()
            print(f"✗ Authentication failed")
            print(f"  Error: {error_data}")
            return False
        else:
            print(f"✗ Unexpected status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False

    @pytest.mark.browser
    @pytest.mark.integration
    def test_browser_inspection_captures_request(self):
        """
        Test that browser inspection can capture API requests.

        Requires manual browser interaction.
        """
        result = capture_api_request(wait_for_api_call=True)

        assert result is not None
        assert "cookies" in result
        assert len(result["cookies"]) > 0

        if result.get("captured_request"):
            req = result["captured_request"]
            print(f"\n✓ Captured request:")
            print(f"  URL: {req['url']}")
            print(f"  Method: {req['method']}")
            print(f"  Headers: {list(req['headers'].keys())}")

        return result

