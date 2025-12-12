"""Browser inspector to capture network requests and extract authentication details."""

import json
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright

BNMP_PORTAL_URL = "https://portalbnmp.cnj.jus.br/#/pesquisa-peca"


def capture_api_request(
    headless: bool = False,
    wait_for_api_call: bool = True,
) -> dict[str, Any] | None:
    """
    Open browser, navigate to portal, and capture the actual API request details.

    Args:
        headless: Whether to run browser in headless mode
        wait_for_api_call: Whether to wait for an API call to be made

    Returns:
        Dictionary with request details (headers, cookies, body, url) or None
    """
    captured_request: dict[str, Any] | None = None
    fingerprint: str | None = None

    def handle_request(request: Any) -> None:
        """Capture API requests."""
        nonlocal captured_request, fingerprint
        url = request.url
        if "/api/pesquisa-pecas/filter" in url:
            print(f"\n[OK] Captured API request: {url}")
            headers_dict = dict(request.headers)
            captured_request = {
                "url": url,
                "method": request.method,
                "headers": headers_dict,
                "post_data": request.post_data,
            }
            print(f"  Method: {request.method}")
            
            # Extract fingerprint from headers if present
            fingerprint_from_header = headers_dict.get("fingerprint") or headers_dict.get("Fingerprint")
            if fingerprint_from_header:
                print(f"  [OK] Found fingerprint in headers: {fingerprint_from_header}")
                fingerprint = fingerprint_from_header

    def handle_response(response: Any) -> None:
        """Capture API responses."""
        url = response.url
        if "/api/pesquisa-pecas/filter" in url:
            print(f"\n[OK] Captured API response: {url}")
            print(f"  Status: {response.status}")
            try:
                body = response.body()
                print(f"  Body preview: {body[:200] if body else 'None'}")
            except Exception as e:
                print(f"  Could not read body: {e}")

    with sync_playwright() as p:
        # Launch browser with more visible window
        browser = p.chromium.launch(
            headless=headless,
            slow_mo=100,  # Slow down operations slightly for better visibility
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},  # Set a reasonable viewport size
        )

        page = context.new_page()

        # Set up request/response listeners
        page.on("request", handle_request)
        page.on("response", handle_response)

        print("\n" + "=" * 60)
        print("Opening browser to capture API requests...")
        print("Please solve the captcha and trigger an API call.")
        print("=" * 60 + "\n")

        # Navigate and wait for page to be fully loaded
        print("Loading page...")
        page.goto(BNMP_PORTAL_URL, wait_until="networkidle", timeout=60000)
        
        # Wait for page to be interactive
        print("Waiting for page to be ready...")
        try:
            # Wait for the page to be fully loaded
            page.wait_for_load_state("domcontentloaded", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=30000)
            
            # Try to wait for captcha iframe or reCAPTCHA element
            print("Waiting for captcha to load...")
            try:
                # Wait for reCAPTCHA iframe (common selectors)
                page.wait_for_selector("iframe[src*='recaptcha']", timeout=10000, state="attached")
                print("[OK] Captcha iframe detected")
            except Exception:
                try:
                    # Alternative: wait for reCAPTCHA container
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
        print("Page is ready!")
        print("=" * 60)
        print("\nInstructions:")
        print("1. Look for the reCAPTCHA checkbox in the browser")
        print("2. Click on 'I'm not a robot' checkbox")
        print("3. Complete any image challenges if they appear")
        print("4. Wait for the captcha to be solved (checkmark should appear)")
        print("5. If making a search: fill in search form and submit")
        print("6. Then press ENTER here\n")

        if wait_for_api_call:
            input(
                "Press ENTER after you have solved the captcha and made a search (API call should be captured)..."
            )
        else:
            input("Press ENTER after you have solved the captcha...")

        # Extract cookies
        cookies = context.cookies()

        # Fingerprint should already be set from handle_request if captured
        # If not, try to extract from captured request
        if not fingerprint and captured_request:
            headers = captured_request.get("headers", {})
            fingerprint = headers.get("fingerprint") or headers.get("Fingerprint")
            if fingerprint:
                print(f"[OK] Extracted fingerprint from request headers: {fingerprint}")

        # If not found in request, try to extract from page
        if not fingerprint:
            try:
                fingerprint = page.evaluate(
                    """
                    () => {
                        if (window.localStorage && window.localStorage.getItem('fingerprint')) {
                            return window.localStorage.getItem('fingerprint');
                        }
                        if (window.fingerprint) {
                            return window.fingerprint;
                        }
                        // Try to find fingerprint in window object
                        for (let key in window) {
                            if (key.toLowerCase().includes('fingerprint')) {
                                return window[key];
                            }
                        }
                        return null;
                    }
                    """
                )
                if fingerprint:
                    print(f"[OK] Extracted fingerprint from page: {fingerprint}")
            except Exception as e:
                print(f"Could not extract fingerprint from page: {e}")

        # Try to get Authorization header or token from localStorage/sessionStorage
        auth_token = None
        try:
            auth_token = page.evaluate(
                """
                () => {
                    if (window.localStorage) {
                        for (let i = 0; i < window.localStorage.length; i++) {
                            const key = window.localStorage.key(i);
                            if (key && (key.toLowerCase().includes('token') || key.toLowerCase().includes('auth'))) {
                                return window.localStorage.getItem(key);
                            }
                        }
                    }
                    if (window.sessionStorage) {
                        for (let i = 0; i < window.sessionStorage.length; i++) {
                            const key = window.sessionStorage.key(i);
                            if (key && (key.toLowerCase().includes('token') || key.toLowerCase().includes('auth'))) {
                                return window.sessionStorage.getItem(key);
                            }
                        }
                    }
                    return null;
                }
                """
            )
        except Exception as e:
            print(f"Could not extract auth token: {e}")

        result = {
            "cookies": cookies,
            "fingerprint": fingerprint,
            "auth_token": auth_token,
            "captured_request": captured_request,
        }

        print(f"\n[OK] Extracted {len(cookies)} cookies")
        if fingerprint:
            print(f"[OK] Extracted fingerprint: {fingerprint}")
        if auth_token:
            print(f"[OK] Extracted auth token: {auth_token[:50]}...")
        if captured_request:
            print(f"[OK] Captured API request details")

        browser.close()

        return result


def inspect_browser_session(filepath: str | Path | None = None) -> dict[str, Any]:
    """
    Inspect browser session and save details to file.

    Args:
        filepath: Optional path to save inspection results

    Returns:
        Dictionary with session details
    """
    result = capture_api_request()

    if filepath:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n[OK] Inspection results saved to {filepath}")

    return result

