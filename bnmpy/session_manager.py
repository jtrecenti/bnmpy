"""Session management for BNMP portal using Playwright."""

import json
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

BNMP_PORTAL_URL = "https://portalbnmp.cnj.jus.br/#/pesquisa-peca"


def get_session_with_playwright(
    headless: bool = False,
    timeout: int = 300000,  # 5 minutes default timeout
    extract_fingerprint: bool = True,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Open browser, navigate to BNMP portal, wait for manual captcha solve, and extract cookies.

    Args:
        headless: Whether to run browser in headless mode (default: False for manual captcha)
        timeout: Maximum time to wait for user to solve captcha (default: 5 minutes)
        extract_fingerprint: Whether to try extracting fingerprint from browser (default: True)

    Returns:
        Tuple of (list of cookie dictionaries, fingerprint string or None)
    """
    fingerprint = None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            slow_mo=100,  # Slow down operations slightly for better visibility
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
        )

        page = context.new_page()
        
        print("\n" + "=" * 60)
        print("Opening browser...")
        print("=" * 60 + "\n")
        
        # Navigate and wait for page to be fully loaded
        print("Loading page...")
        page.goto(BNMP_PORTAL_URL, wait_until="networkidle", timeout=60000)
        
        # Wait for page to be interactive
        print("Waiting for page to be ready...")
        try:
            page.wait_for_load_state("domcontentloaded", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=30000)
            
            # Try to wait for captcha iframe or reCAPTCHA element
            print("Waiting for captcha to load...")
            try:
                page.wait_for_selector("iframe[src*='recaptcha']", timeout=10000, state="attached")
                print("[OK] Captcha iframe detected")
            except Exception:
                try:
                    page.wait_for_selector(".g-recaptcha, [data-sitekey], #recaptcha", timeout=10000)
                    print("[OK] Captcha container detected")
                except Exception:
                    print("[INFO] Captcha element not found, but page should be ready")
            
            # Give page a moment to fully render
            page.wait_for_timeout(2000)
            
        except Exception as e:
            print(f"[WARN] Could not wait for all elements: {e}")
            print("[INFO] Proceeding anyway - page should be ready")

        print("\n" + "=" * 60)
        print("Browser opened. Please solve the captcha manually.")
        print("=" * 60)
        print("\nInstructions:")
        print("1. Look for the reCAPTCHA checkbox in the browser")
        print("2. Click on 'I'm not a robot' checkbox")
        print("3. Complete any image challenges if they appear")
        print("4. Wait for the captcha to be solved (checkmark should appear)")
        print("5. Then press ENTER here\n")

        # Wait for user to solve captcha
        input(
            "Press ENTER after you have solved the captcha and the page has loaded..."
        )

        # Extract cookies from the context
        cookies = context.cookies()

        # Try to extract fingerprint from browser
        if extract_fingerprint:
            try:
                # Try to get fingerprint from localStorage or window object
                fingerprint = page.evaluate(
                    """
                    () => {
                        // Try localStorage first
                        if (window.localStorage && window.localStorage.getItem('fingerprint')) {
                            return window.localStorage.getItem('fingerprint');
                        }
                        // Try window.fingerprint
                        if (window.fingerprint) {
                            return window.fingerprint;
                        }
                        // Try to find it in the page context
                        return null;
                    }
                    """
                )
                if fingerprint:
                    print(f"Extracted fingerprint: {fingerprint}")
            except Exception as e:
                print(f"Could not extract fingerprint automatically: {e}")
                print("You may need to set it manually when creating the API client.")

        print(f"\nExtracted {len(cookies)} cookies from the session.")
        print("Closing browser...\n")

        browser.close()

        return cookies, fingerprint


def save_cookies(
    cookies: list[dict[str, Any]],
    filepath: str | Path,
    fingerprint: str | None = None,
) -> None:
    """
    Save cookies and optionally fingerprint to a JSON file.

    Args:
        cookies: List of cookie dictionaries
        filepath: Path to save the cookies file
        fingerprint: Optional fingerprint to save alongside cookies
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {"cookies": cookies}
    if fingerprint:
        data["fingerprint"] = fingerprint

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Cookies saved to {filepath}")
    if fingerprint:
        print(f"Fingerprint saved: {fingerprint}")


def load_cookies(filepath: str | Path) -> tuple[list[dict[str, Any]], str | None]:
    """
    Load cookies and optionally fingerprint from a JSON file.

    Args:
        filepath: Path to the cookies file

    Returns:
        Tuple of (list of cookie dictionaries, fingerprint string or None)
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Cookies file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Support both old format (just cookies list) and new format (dict with cookies and fingerprint)
    if isinstance(data, list):
        return data, None
    else:
        return data.get("cookies", []), data.get("fingerprint")


def create_session_from_cookies(cookies: list[dict[str, Any]]) -> "requests.Session":
    """
    Create a requests.Session with cookies loaded from Playwright cookies.

    Args:
        cookies: List of cookie dictionaries from Playwright

    Returns:
        requests.Session configured with the cookies
    """
    import requests

    session = requests.Session()

    # Convert Playwright cookies to requests-compatible format
    # Playwright cookies have: name, value, domain, path, expires, httpOnly, secure, sameSite
    # requests.cookies need: name, value, domain, path
    cookie_dict = {}
    for cookie in cookies:
        # Create a cookie string for the Cookie header
        cookie_dict[cookie["name"]] = cookie["value"]

    # Set cookies in the session
    # We'll use the domain and path from the cookies
    for cookie in cookies:
        session.cookies.set(
            name=cookie["name"],
            value=cookie["value"],
            domain=cookie.get("domain", ""),
            path=cookie.get("path", "/"),
        )

    return session

