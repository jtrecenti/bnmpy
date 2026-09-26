"""API client for BNMP portal using requests."""

import base64
import json
from typing import Any
from urllib.parse import unquote

import requests

from bnmpy.session_manager import create_session_from_cookies, load_cookies

BNMP_API_BASE_URL = "https://portalbnmp.cnj.jus.br"
BNMP_COOKIE_DOMAIN = "portalbnmp.cnj.jus.br"
AUTH_COOKIE_NAME = "portalbnmp"


def normalize_token(token: str) -> str:
    """Return the bare JWT from a token, cookie value or Authorization header."""
    token = unquote(token.strip())
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


def token_expiration(token: str) -> int | None:
    """Return the ``exp`` claim (unix timestamp) of a JWT, or None if unreadable."""
    try:
        payload = normalize_token(token).split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("exp")
    except (IndexError, ValueError):
        return None


class BNMPAPIClient:
    """Client for interacting with BNMP portal API using requests."""

    def __init__(
        self,
        cookies: list[dict[str, Any]] | None = None,
        cookies_file: str | None = None,
        session: requests.Session | None = None,
        fingerprint: str | None = None,
        token: str | None = None,
    ):
        """
        Initialize the API client with cookies.

        Args:
            cookies: List of cookie dictionaries (from Playwright)
            cookies_file: Path to a JSON file containing cookies
            session: Optional pre-configured requests.Session
            fingerprint: Optional fingerprint header value (extracted from browser)
            token: Optional JWT issued after solving the captcha (value of the
                ``portalbnmp`` cookie). It expires about 5 minutes after issue.
        """
        if session is not None:
            self.session = session
        elif cookies is not None:
            self.session = create_session_from_cookies(cookies)
        elif cookies_file is not None:
            loaded_cookies, loaded_fingerprint = load_cookies(cookies_file)
            self.session = create_session_from_cookies(loaded_cookies)
            # Use loaded fingerprint if fingerprint not explicitly provided
            if fingerprint is None:
                fingerprint = loaded_fingerprint
        elif token is not None:
            self.session = requests.Session()
        else:
            raise ValueError(
                "Must provide either cookies, cookies_file, session, or token"
            )

        if token is not None:
            self.set_token(token)

        # Set default headers
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
                "Content-Type": "application/json;charset=UTF-8",
                "Referer": "https://portalbnmp.cnj.jus.br/",
                "Origin": "https://portalbnmp.cnj.jus.br",
                "DNT": "1",
                "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
            }
        )

        # Set fingerprint if provided
        if fingerprint:
            self.session.headers["fingerprint"] = fingerprint

    def set_token(self, token: str) -> None:
        """Set the authentication token (``portalbnmp`` cookie)."""
        jwt = normalize_token(token)
        for cookie in list(self.session.cookies):
            if cookie.name == AUTH_COOKIE_NAME:
                self.session.cookies.clear(cookie.domain, cookie.path, cookie.name)
        self.session.cookies.set(
            AUTH_COOKIE_NAME,
            jwt,
            domain=BNMP_COOKIE_DOMAIN,
            path="/",
        )

    @property
    def token(self) -> str | None:
        """Current JWT, if any."""
        for cookie in self.session.cookies:
            if cookie.name == AUTH_COOKIE_NAME and cookie.value:
                return normalize_token(cookie.value)
        return None

    @property
    def token_expiration(self) -> int | None:
        """Expiration (unix timestamp) of the current token, if known."""
        token = self.token
        return token_expiration(token) if token else None

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """
        Make a GET request.

        Args:
            url: URL to request (can be relative or absolute)
            **kwargs: Additional arguments passed to requests.get

        Returns:
            Response object
        """
        if not url.startswith("http"):
            url = f"{BNMP_API_BASE_URL}{url}"
        return self.session.get(url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        """
        Make a POST request.

        Args:
            url: URL to request (can be relative or absolute)
            **kwargs: Additional arguments passed to requests.post

        Returns:
            Response object
        """
        if not url.startswith("http"):
            url = f"{BNMP_API_BASE_URL}{url}"
        return self.session.post(url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> requests.Response:
        """
        Make a PUT request.

        Args:
            url: URL to request (can be relative or absolute)
            **kwargs: Additional arguments passed to requests.put

        Returns:
            Response object
        """
        if not url.startswith("http"):
            url = f"{BNMP_API_BASE_URL}{url}"
        return self.session.put(url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> requests.Response:
        """
        Make a DELETE request.

        Args:
            url: URL to request (can be relative or absolute)
            **kwargs: Additional arguments passed to requests.delete

        Returns:
            Response object
        """
        if not url.startswith("http"):
            url = f"{BNMP_API_BASE_URL}{url}"
        return self.session.delete(url, **kwargs)

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """
        Make a request with the specified method.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: URL to request (can be relative or absolute)
            **kwargs: Additional arguments passed to requests.request

        Returns:
            Response object
        """
        if not url.startswith("http"):
            url = f"{BNMP_API_BASE_URL}{url}"
        return self.session.request(method, url, **kwargs)

    def pesquisa_pecas_filter(
        self,
        busca_orgao_recursivo: bool = False,
        orgao_expeditor: dict[str, Any] | None = None,
        id_estado: int | None = None,
        id_municipio: int | None = None,
        numero_processo: str | None = None,
        page: int = 0,
        size: int = 10,
        sort: str = "",
        **kwargs: Any,
    ) -> requests.Response:
        """
        Search for pieces (pecas) using the filter endpoint.

        Args:
            busca_orgao_recursivo: Whether to search recursively in organs
            orgao_expeditor: Dictionary with organ expeditor filters
            id_estado: State ID filter
            id_municipio: Optional municipality ID filter
            numero_processo: Process number filter
            page: Page number (default: 0)
            size: Page size (default: 10)
            sort: Sort parameter (default: empty string)
            **kwargs: Additional arguments passed to requests.post

        Returns:
            Response object with search results
        """
        url = "/bnmpportal/api/pesquisa-pecas/filter"
        params = {"page": page, "size": size, "sort": sort}

        payload: dict[str, Any] = {
            "buscaOrgaoRecursivo": busca_orgao_recursivo,
            "orgaoExpeditor": orgao_expeditor or {},
        }

        if id_estado is not None:
            payload["idEstado"] = id_estado

        if id_municipio is not None:
            payload["idMunicipio"] = id_municipio

        if numero_processo is not None:
            payload["numeroProcesso"] = numero_processo

        return self.post(url, params=params, json=payload, **kwargs)

    def get_estados(self) -> requests.Response:
        """
        Get list of all states (UFs).

        Returns:
            Response object with list of states
        """
        url = "/bnmpportal/api/dominio/estados"
        return self.get(url)

    def get_municipios_por_uf(self, uf_id: int) -> requests.Response:
        """
        Get list of municipalities for a specific UF.

        Args:
            uf_id: State ID

        Returns:
            Response object with list of municipalities
        """
        url = f"/bnmpportal/api/dominio/por-uf/{uf_id}"
        return self.get(url)

    def download_pdf(self, certidao_id: int, id_tipo_peca: int) -> requests.Response:
        """
        Download PDF certificate for a specific person.

        Args:
            certidao_id: Certificate ID (the 'id' field from filter results)
            id_tipo_peca: Type of piece ID (the 'idTipoPeca' field from filter results)

        Returns:
            Response object with PDF content
        """
        # The old endpoint (/certidaos/relatorio/{id}/{idTipoPeca}) now returns 500
        url = "/bnmpportal/api/pesquisa-pecas/emitir-documento"
        return self.post(url, json={"id": certidao_id, "idTipoPeca": id_tipo_peca})

    def download_csv(
        self,
        id_estado: int | None = None,
        id_municipio: int | None = None,
        busca_orgao_recursivo: bool = False,
        orgao_expeditor: dict[str, Any] | None = None,
        numero_processo: str = "",
        id_sexo: int | None = None,
    ) -> requests.Response:
        """
        Download CSV file with all results for a query (e.g., for a UF).

        Args:
            id_estado: State ID filter
            id_municipio: Optional municipality ID filter
            busca_orgao_recursivo: Whether to search recursively in organs
            orgao_expeditor: Dictionary with organ expeditor filters
            numero_processo: Process number filter
            id_sexo: Gender ID filter

        Returns:
            Response object with CSV content
        """
        url = "/bnmpportal/api/pesquisa-pecas/csv"

        payload: dict[str, Any] = {
            "buscaOrgaoRecursivo": busca_orgao_recursivo,
            "orgaoExpeditor": orgao_expeditor or {},
            "numeroProcesso": numero_processo,
        }

        if id_estado is not None:
            payload["idEstado"] = id_estado

        if id_municipio is not None:
            payload["idMunicipio"] = id_municipio

        if id_sexo is not None:
            payload["idSexo"] = id_sexo

        return self.post(url, json=payload)

