"""Script to run the BNMP scraper."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bnmpy import BNMPAPIClient, load_cookies
from bnmpy.scraper import BNMPScraper


def main():
    """Run the scraper."""
    parser = argparse.ArgumentParser(description="BNMP Portal Scraper")
    parser.add_argument(
        "--cookies-file",
        type=str,
        default="cookies.json",
        help="Path to cookies file (default: cookies.json)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data-raw",
        help="Directory to save data (default: data-raw)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=30,
        help="Number of results per page (default: 30, will auto-reduce if needed)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=10000,
        help="Maximum results per UF+municipality combination (default: 10000)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers for downloads (default: 1 = sequential)",
    )
    parser.add_argument(
        "--start-uf",
        type=int,
        help="UF ID to start from (for resuming)",
    )
    parser.add_argument(
        "--start-municipio",
        type=int,
        help="Municipality ID to start from (for resuming)",
    )
    parser.add_argument(
        "--no-skip-small",
        action="store_true",
        help="Don't skip municipality iteration for small UFs",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("BNMP Portal Scraper")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Cookies file: {args.cookies_file}")
    print(f"  Data directory: {args.data_dir}")
    print(f"  Page size: {args.page_size}")
    print(f"  Max results per combination: {args.max_results}")
    print(f"  Delay between requests: {args.delay}s")
    print(f"  Parallel workers: {args.workers}")
    if args.start_uf:
        print(f"  Starting from UF ID: {args.start_uf}")
    if args.start_municipio:
        print(f"  Starting from Municipality ID: {args.start_municipio}")
    print(f"  Skip small UFs: {not args.no_skip_small}")
    print()

    # Load cookies
    cookies_file = Path(args.cookies_file)
    if not cookies_file.exists():
        print(f"[ERROR] Cookies file not found: {cookies_file}")
        print("\nTo create it:")
        print(
            "  python -c 'from bnmpy import get_session_with_playwright, save_cookies; c,f=get_session_with_playwright(); save_cookies(c,\"cookies.json\",f)'"
        )
        return 1

    print(f"[OK] Loading cookies from {cookies_file}")
    cookies, fingerprint = load_cookies(cookies_file)
    print(f"  Cookies: {len(cookies)}")
    print(f"  Fingerprint: {fingerprint or 'Not set'}")

    # Create API client
    print("\n[OK] Creating API client...")
    client = BNMPAPIClient(cookies=cookies, fingerprint=fingerprint)

    # Create scraper
    print("[OK] Creating scraper...")
    scraper = BNMPScraper(
        client=client,
        data_dir=args.data_dir,
        page_size=args.page_size,
        max_results_per_combination=args.max_results,
        delay_between_requests=args.delay,
        max_workers=args.workers,
    )

    # Run scraper
    print("\n" + "=" * 60)
    print("Starting scrape...")
    print("=" * 60 + "\n")

    try:
        scraper.scrape_all(
            start_uf_id=args.start_uf,
            start_municipio_id=args.start_municipio,
            skip_small_ufs=not args.no_skip_small,
        )
        print("\n" + "=" * 60)
        print("[SUCCESS] Scraping completed!")
        print("=" * 60)
        return 0
    except KeyboardInterrupt:
        print("\n\n[INFO] Scraping interrupted by user")
        print("You can resume by using --start-uf and --start-municipio options")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Scraping failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

