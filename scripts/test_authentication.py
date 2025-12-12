"""Quick script to test authentication and debug issues."""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bnmpy import BNMPAPIClient, load_cookies


def main():
    """Test authentication with current cookies."""
    print("=" * 60)
    print("BNMP Authentication Test")
    print("=" * 60)

    cookies_file = Path("cookies.json")
    if not cookies_file.exists():
        print("\n[ERROR] cookies.json not found!")
        print("\nTo create it:")
        print("  1. Run: python -c 'from bnmpy import get_session_with_playwright, save_cookies; c,f=get_session_with_playwright(); save_cookies(c,\"cookies.json\",f)'")
        print("  2. Solve the captcha when browser opens")
        print("  3. Press ENTER when done")
        return False

    # Load cookies
    print(f"\n[OK] Loading cookies from {cookies_file}")
    cookies, fingerprint = load_cookies(cookies_file)
    print(f"  Cookies: {len(cookies)}")
    print(f"  Cookie names: {[c.get('name') for c in cookies]}")
    print(f"  Fingerprint: {fingerprint or 'Not set'}")

    # Check for portalbnmp cookie
    portalbnmp_cookie = next((c for c in cookies if c.get('name') == 'portalbnmp'), None)
    if portalbnmp_cookie:
        token = portalbnmp_cookie.get('value', '')
        print(f"\n[OK] Found portalbnmp cookie (token length: {len(token)})")
        
        # Try to decode JWT to check expiration
        try:
            import base64
            parts = token.split('.')
            if len(parts) == 3:
                payload = parts[1]
                payload += '=' * (4 - len(payload) % 4)
                decoded = json.loads(base64.urlsafe_b64decode(payload))
                import time
                exp = decoded.get('exp', 0)
                if exp < time.time():
                    print(f"  [WARN] Token expired at {exp} (current: {time.time()})")
                    print(f"  [WARN] You need to get a fresh session!")
                else:
                    print(f"  [OK] Token valid until {exp}")
        except Exception as e:
            print(f"  Could not decode token: {e}")
    else:
        print(f"\n[ERROR] portalbnmp cookie not found!")
        print(f"  This cookie is required for authentication")

    # Create client
    print(f"\n[OK] Creating API client...")
    client = BNMPAPIClient(cookies=cookies, fingerprint=fingerprint)

    # Show request details
    print(f"\nRequest Headers:")
    important_headers = ['fingerprint', 'cookie', 'authorization', 'referer', 'origin']
    for key in important_headers:
        if key in client.session.headers:
            value = client.session.headers[key]
            if len(str(value)) > 80:
                value = str(value)[:80] + "..."
            print(f"  {key}: {value}")

    # Make API call
    print(f"\n" + "=" * 60)
    print("Making API Call")
    print("=" * 60)
    print(f"\nCalling pesquisa_pecas_filter...")

    try:
        response = client.pesquisa_pecas_filter(
            busca_orgao_recursivo=False,
            orgao_expeditor={},
            id_estado=2,
            page=0,
            size=10,
        )

        print(f"\nStatus Code: {response.status_code}")
        print(f"Response URL: {response.url}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n[SUCCESS] API call worked!")
            print(f"\nResponse data:")
            if isinstance(data, dict):
                print(f"  Keys: {list(data.keys())}")
                if 'content' in data:
                    print(f"  Content items: {len(data.get('content', []))}")
                if 'totalElements' in data:
                    print(f"  Total elements: {data.get('totalElements')}")
            else:
                print(f"  Type: {type(data)}")
                print(f"  Preview: {str(data)[:200]}")
            return True

        elif response.status_code == 401:
            error_data = response.json()
            print(f"\n[ERROR] AUTHENTICATION FAILED")
            print(f"\nError details:")
            print(f"  Status: {error_data.get('status')}")
            print(f"  Title: {error_data.get('title')}")
            print(f"  Detail: {error_data.get('detail')}")
            print(f"  Message: {error_data.get('message')}")

            print(f"\nTroubleshooting:")
            print(f"  1. Check if cookies are expired (see above)")
            print(f"  2. Run: python scripts/inspect_browser.py")
            print(f"     This will capture what the browser actually sends")
            print(f"  3. Run: python scripts/compare_requests.py")
            print(f"     This will compare your request with browser request")
            return False

        else:
            print(f"\n[ERROR] Unexpected status: {response.status_code}")
            print(f"  Response: {response.text[:500]}")
            return False

    except Exception as e:
        print(f"\n[ERROR] Error making API call: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

