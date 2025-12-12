"""Example usage of BNMP portal scraper."""

import json
from pathlib import Path

from bnmpy import BNMPAPIClient, get_session_with_playwright, load_cookies, save_cookies

COOKIES_FILE = Path("cookies.json")


def main():
    """Demonstrate the workflow: get session, save cookies, use API client."""
    print("BNMP Portal Scraper - Example Usage\n")

    cookies = None
    fingerprint = None

    # Check if cookies file exists
    if COOKIES_FILE.exists():
        print(f"Found existing cookies file: {COOKIES_FILE}")
        use_existing = input(
            "Use existing cookies? (y/n, default: n): "
        ).strip().lower()

        if use_existing == "y":
            print("Loading cookies from file...")
            cookies, fingerprint = load_cookies(COOKIES_FILE)
            print(f"Loaded {len(cookies)} cookies.")
            if fingerprint:
                print(f"Loaded fingerprint: {fingerprint}")
            print()
        else:
            print("Getting new session with Playwright...")
            cookies, fingerprint = get_session_with_playwright()
            save_cookies(cookies, COOKIES_FILE, fingerprint)
    else:
        print("No existing cookies found.")
        print("Getting new session with Playwright...")
        cookies, fingerprint = get_session_with_playwright()
        save_cookies(cookies, COOKIES_FILE, fingerprint)

    # Create API client with cookies and fingerprint
    print("\nCreating API client...")
    client = BNMPAPIClient(cookies=cookies, fingerprint=fingerprint)

    # Example: Make the pesquisa-pecas filter API call
    print("\nMaking pesquisa-pecas filter API call...")
    print("Searching for pieces in state ID 2 (example)...")
    try:
        response = client.pesquisa_pecas_filter(
            busca_orgao_recursivo=False,
            orgao_expeditor={},
            id_estado=2,
            page=0,
            size=10,
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response URL: {response.url}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ API call successful!")
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'List response'}")
            
            # Pretty print a sample of the response
            print("\nResponse preview:")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
            if len(json.dumps(data, ensure_ascii=False)) > 500:
                print("... (truncated)")
        else:
            print(f"\n✗ API call failed with status {response.status_code}")
            print(f"Response: {response.text[:200]}")

    except Exception as e:
        print(f"\n✗ Error making API call: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("API Client ready! You can now use it to make API calls.")
    print("Example:")
    print("  client.pesquisa_pecas_filter(id_estado=2, page=0, size=10)")
    print("=" * 60)


if __name__ == "__main__":
    main()
