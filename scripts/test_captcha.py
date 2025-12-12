"""Test script to verify captcha page loads correctly."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright

BNMP_PORTAL_URL = "https://portalbnmp.cnj.jus.br/#/pesquisa-peca"


def main():
    """Test if captcha page loads correctly."""
    print("=" * 60)
    print("Captcha Page Load Test")
    print("=" * 60)
    print("\nThis will test if the captcha page loads correctly.")
    print("The browser will stay open for 30 seconds so you can inspect it.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        print("Loading page...")
        try:
            page.goto(BNMP_PORTAL_URL, wait_until="networkidle", timeout=60000)
            print("[OK] Page loaded")
        except Exception as e:
            print(f"[ERROR] Failed to load page: {e}")
            browser.close()
            return

        print("\nChecking page elements...")
        
        # Check for reCAPTCHA
        try:
            recaptcha_iframe = page.query_selector("iframe[src*='recaptcha']")
            if recaptcha_iframe:
                print("[OK] reCAPTCHA iframe found")
            else:
                print("[WARN] reCAPTCHA iframe not found")
        except Exception as e:
            print(f"[WARN] Could not check for reCAPTCHA iframe: {e}")

        # Check for reCAPTCHA container
        try:
            recaptcha_container = page.query_selector(".g-recaptcha, [data-sitekey], #recaptcha")
            if recaptcha_container:
                print("[OK] reCAPTCHA container found")
            else:
                print("[WARN] reCAPTCHA container not found")
        except Exception as e:
            print(f"[WARN] Could not check for reCAPTCHA container: {e}")

        # Check page title
        title = page.title()
        print(f"\nPage title: {title}")

        # Check URL
        url = page.url
        print(f"Current URL: {url}")

        # Wait a bit and check if page is interactive
        print("\nWaiting 2 seconds for page to stabilize...")
        page.wait_for_timeout(2000)

        # Check if page is ready
        try:
            page.evaluate("document.readyState")
            print("[OK] Page is interactive")
        except Exception as e:
            print(f"[WARN] Page might not be fully interactive: {e}")

        print("\n" + "=" * 60)
        print("Browser will stay open for 30 seconds for inspection...")
        print("=" * 60)
        print("\nLook for:")
        print("1. The reCAPTCHA checkbox")
        print("2. Any error messages")
        print("3. If the page looks fully loaded")
        print("\n")

        # Keep browser open for inspection
        page.wait_for_timeout(30000)

        print("\nClosing browser...")
        browser.close()
        print("[OK] Test complete")


if __name__ == "__main__":
    main()

