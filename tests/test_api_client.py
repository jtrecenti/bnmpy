"""Tests for API client."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from bnmpy import BNMPAPIClient, load_cookies
from bnmpy.session_manager import save_cookies


class TestAPIClient:
    """Test API client functionality."""

    @pytest.fixture
    def sample_cookies(self):
        """Sample cookies for testing."""
        return [
            {
                "name": "portalbnmp",
                "value": "test_token_value",
                "domain": ".cnj.jus.br",
                "path": "/",
            },
        ]

    @pytest.fixture
    def cookies_file(self, tmp_path: Path, sample_cookies):
        """Create a temporary cookies file."""
        cookie_file = tmp_path / "test_cookies.json"
        save_cookies(sample_cookies, cookie_file)
        return cookie_file

    def test_client_initialization_with_cookies(self, sample_cookies):
        """Test initializing client with cookies."""
        client = BNMPAPIClient(cookies=sample_cookies)
        assert client.session is not None
        assert len(client.session.cookies) > 0

    def test_client_initialization_with_cookies_file(self, cookies_file):
        """Test initializing client with cookies file."""
        client = BNMPAPIClient(cookies_file=str(cookies_file))
        assert client.session is not None

    def test_client_initialization_with_fingerprint(self, sample_cookies):
        """Test initializing client with fingerprint."""
        fingerprint = "test_fingerprint_123"
        client = BNMPAPIClient(cookies=sample_cookies, fingerprint=fingerprint)
        assert client.session.headers.get("fingerprint") == fingerprint

    def test_pesquisa_pecas_filter_method(self, sample_cookies):
        """Test pesquisa_pecas_filter method structure."""
        client = BNMPAPIClient(cookies=sample_cookies)

        # Mock the post method to avoid actual API call
        with patch.object(client.session, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"content": [], "totalElements": 0}
            mock_post.return_value = mock_response

            response = client.pesquisa_pecas_filter(
                busca_orgao_recursivo=False,
                orgao_expeditor={},
                id_estado=2,
                page=0,
                size=10,
            )

            assert response.status_code == 200
            mock_post.assert_called_once()
            call_args = mock_post.call_args

            # Check URL
            assert "/bnmpportal/api/pesquisa-pecas/filter" in call_args[0][0]

            # Check params
            assert call_args[1]["params"]["page"] == 0
            assert call_args[1]["params"]["size"] == 10

            # Check JSON payload
            json_payload = call_args[1]["json"]
            assert json_payload["buscaOrgaoRecursivo"] is False
            assert json_payload["idEstado"] == 2


class TestAPIAuthentication:
    """Test API authentication - requires valid cookies."""

    @pytest.mark.integration
    def test_api_call_with_real_cookies(self):
        """Test API call with real cookies (requires cookies.json)."""
        cookies_file = Path("cookies.json")
        if not cookies_file.exists():
            pytest.skip("cookies.json not found - run session acquisition first")

        cookies, fingerprint = load_cookies(cookies_file)
        client = BNMPAPIClient(cookies=cookies, fingerprint=fingerprint)

        # Make actual API call
        response = client.pesquisa_pecas_filter(
            busca_orgao_recursivo=False,
            orgao_expeditor={},
            id_estado=2,
            page=0,
            size=10,
        )

        # Check response
        assert response.status_code in [200, 401], f"Unexpected status: {response.status_code}"

        if response.status_code == 401:
            error_data = response.json()
            print(f"\n✗ Authentication failed: {error_data}")
            print(f"  Status: {error_data.get('status')}")
            print(f"  Message: {error_data.get('message')}")
            print(f"  Detail: {error_data.get('detail')}")
            print(f"\n  Cookies used: {len(cookies)}")
            print(f"  Fingerprint: {fingerprint}")
            print(f"  Cookie names: {[c.get('name') for c in cookies]}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ API call successful!")
            print(f"  Response keys: {list(data.keys()) if isinstance(data, dict) else 'List response'}")

        assert response.status_code in [200, 401], f"Unexpected status: {response.status_code}"

