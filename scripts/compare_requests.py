"""Compare our API request with browser request to debug authentication."""

import json
import sys
from pathlib import Path

import requests

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bnmpy import BNMPAPIClient, load_cookies


def compare_requests():
    """Compare our request with browser request."""
    print("=" * 60)
    print("Request Comparison Tool")
    print("=" * 60)

    # Load cookies
    cookies_file = Path("cookies.json")
    if not cookies_file.exists():
        print("✗ cookies.json not found")
        return

    cookies, fingerprint = load_cookies(cookies_file)
    print(f"\n✓ Loaded {len(cookies)} cookies")
    print(f"  Fingerprint: {fingerprint}")

    # Load browser inspection if available
    inspection_file = Path("browser_inspection.json")
    browser_request = None
    if inspection_file.exists():
        with open(inspection_file) as f:
            inspection = json.load(f)
            browser_request = inspection.get("captured_request")
            print(f"\n✓ Loaded browser inspection data")

    # Create our client
    client = BNMPAPIClient(cookies=cookies, fingerprint=fingerprint)

    # Make request
    print("\n" + "=" * 60)
    print("Making API Request")
    print("=" * 60)

    response = client.pesquisa_pecas_filter(
        busca_orgao_recursivo=False,
        orgao_expeditor={},
        id_estado=2,
        page=0,
        size=10,
    )

    print(f"\nStatus Code: {response.status_code}")

    if response.status_code == 401:
        error_data = response.json()
        print(f"\n✗ Authentication Failed")
        print(f"  Error: {error_data.get('detail', 'Unknown error')}")

    # Compare headers
    print("\n" + "=" * 60)
    print("Request Headers Comparison")
    print("=" * 60)

    our_headers = dict(client.session.headers)
    print(f"\nOur Headers ({len(our_headers)}):")
    for key, value in sorted(our_headers.items()):
        display_value = value[:80] + "..." if len(str(value)) > 80 else value
        print(f"  {key}: {display_value}")

    if browser_request:
        browser_headers = browser_request.get("headers", {})
        print(f"\nBrowser Headers ({len(browser_headers)}):")
        for key, value in sorted(browser_headers.items()):
            display_value = value[:80] + "..." if len(str(value)) > 80 else value
            print(f"  {key}: {display_value}")

        # Find differences
        print("\n" + "=" * 60)
        print("Differences")
        print("=" * 60)

        our_keys = set(our_headers.keys())
        browser_keys = set(browser_headers.keys())

        missing_in_ours = browser_keys - our_keys
        extra_in_ours = our_keys - browser_keys
        different_values = {
            k: (our_headers[k], browser_headers[k])
            for k in our_keys & browser_keys
            if our_headers[k] != browser_headers[k]
        }

        if missing_in_ours:
            print(f"\n✗ Headers missing in our request:")
            for key in missing_in_ours:
                print(f"  {key}: {browser_headers[key][:80]}")

        if extra_in_ours:
            print(f"\n⚠ Headers extra in our request:")
            for key in extra_in_ours:
                print(f"  {key}: {our_headers[key][:80]}")

        if different_values:
            print(f"\n⚠ Headers with different values:")
            for key, (our_val, browser_val) in different_values.items():
                print(f"  {key}:")
                print(f"    Our:     {our_val[:80]}")
                print(f"    Browser: {browser_val[:80]}")

    # Compare cookies
    print("\n" + "=" * 60)
    print("Cookies Comparison")
    print("=" * 60)

    our_cookies = {c.name: c.value for c in client.session.cookies}
    print(f"\nOur Cookies ({len(our_cookies)}):")
    for name, value in sorted(our_cookies.items()):
        display_value = value[:50] + "..." if len(value) > 50 else value
        print(f"  {name}: {display_value}")

    if browser_request:
        browser_cookies_str = browser_headers.get("cookie", "")
        browser_cookies = {}
        if browser_cookies_str:
            for item in browser_cookies_str.split("; "):
                if "=" in item:
                    name, value = item.split("=", 1)
                    browser_cookies[name] = value

        print(f"\nBrowser Cookies ({len(browser_cookies)}):")
        for name, value in sorted(browser_cookies.items()):
            display_value = value[:50] + "..." if len(value) > 50 else value
            print(f"  {name}: {display_value}")

        # Find cookie differences
        our_cookie_names = set(our_cookies.keys())
        browser_cookie_names = set(browser_cookies.keys())

        missing_cookies = browser_cookie_names - our_cookie_names
        if missing_cookies:
            print(f"\n✗ Cookies missing in our request:")
            for name in missing_cookies:
                print(f"  {name}: {browser_cookies[name][:50]}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    compare_requests()

