"""Script to inspect browser and capture API request details."""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bnmpy.browser_inspector import inspect_browser_session


def main():
    """Run browser inspection."""
    print("=" * 60)
    print("BNMP Browser Inspector")
    print("=" * 60)
    print("\nThis will:")
    print("1. Open a browser")
    print("2. Navigate to the BNMP portal")
    print("3. Wait for you to solve the captcha")
    print("4. Capture API request details when you make a search")
    print("\n")

    result_file = Path("browser_inspection.json")
    result = inspect_browser_session(result_file)

    print("\n" + "=" * 60)
    print("Inspection Complete")
    print("=" * 60)

    if result.get("captured_request"):
        req = result["captured_request"]
        print("\nCaptured API Request:")
        print(f"  URL: {req['url']}")
        print(f"  Method: {req['method']}")
        print(f"\n  Headers:")
        for key, value in req["headers"].items():
            if key.lower() in ["cookie", "authorization", "fingerprint"]:
                print(f"    {key}: {value[:100]}...")
            else:
                print(f"    {key}: {value}")

        if req.get("post_data"):
            try:
                post_data = json.loads(req["post_data"])
                print(f"\n  POST Data:")
                print(json.dumps(post_data, indent=2))
            except:
                print(f"\n  POST Data: {req['post_data']}")

    print(f"\n[OK] Full results saved to: {result_file}")
    print("\nYou can now use these details to debug authentication issues.")


if __name__ == "__main__":
    main()

