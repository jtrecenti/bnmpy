"""Script to download CSV files for each UF and merge them into a single file."""

import csv
import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from bnmpy import BNMPAPIClient, load_cookies


def load_estados(metadata_dir: Path) -> list[dict[str, Any]]:
    """Load estados from metadata file."""
    estados_file = metadata_dir / "estados.json"
    if not estados_file.exists():
        raise FileNotFoundError(f"Estados file not found: {estados_file}")

    with open(estados_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("estados", [])


def download_csv_for_uf(
    client: BNMPAPIClient,
    uf_id: int,
    uf_sigla: str,
    output_dir: Path,
    delay: float = 0.5,
) -> Path | None:
    """
    Download CSV file for a specific UF.

    Args:
        client: BNMP API client
        uf_id: UF ID
        uf_sigla: UF abbreviation (e.g., "SP")
        output_dir: Directory to save CSV files
        delay: Delay between requests in seconds

    Returns:
        Path to downloaded CSV file, or None if download failed
    """
    csv_filename = f"uf_{uf_id}_{uf_sigla}.csv"
    csv_path = output_dir / csv_filename

    # Skip if already downloaded
    if csv_path.exists():
        print(f"  [SKIP] CSV already exists: {csv_filename}")
        return csv_path

    print(f"  Downloading CSV for UF {uf_sigla} (ID: {uf_id})...")

    try:
        response = client.download_csv(id_estado=uf_id)

        if response.status_code == 200:
            # Save CSV file
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(csv_path, "wb") as f:
                f.write(response.content)

            # Check if CSV is not empty
            if len(response.content) > 0:
                print(f"  [OK] Downloaded: {csv_filename} ({len(response.content)} bytes)")
                time.sleep(delay)
                return csv_path
            else:
                print(f"  [WARN] Empty CSV for UF {uf_sigla}")
                csv_path.unlink()  # Delete empty file
                return None
        else:
            print(
                f"  [ERROR] Failed to download CSV for UF {uf_sigla}: "
                f"HTTP {response.status_code}"
            )
            if response.text:
                print(f"  Response: {response.text[:200]}")
            return None

    except Exception as e:
        print(f"  [ERROR] Exception downloading CSV for UF {uf_sigla}: {e}")
        return None


def merge_csvs(csv_dir: Path, output_file: Path) -> None:
    """
    Merge all CSV files into a single file, adding a UF column.

    Args:
        csv_dir: Directory containing CSV files
        output_file: Path to save merged CSV file
    """
    print("\n" + "=" * 60)
    print("Merging CSV files...")
    print("=" * 60)

    csv_files = sorted(csv_dir.glob("uf_*.csv"))

    if not csv_files:
        print("[ERROR] No CSV files found to merge!")
        return

    print(f"Found {len(csv_files)} CSV files to merge")

    all_dataframes = []

    for csv_file in csv_files:
        # Extract UF info from filename: uf_{id}_{sigla}.csv
        parts = csv_file.stem.split("_")
        if len(parts) >= 3:
            uf_id = parts[1]
            uf_sigla = parts[2]
        else:
            uf_id = "unknown"
            uf_sigla = "unknown"

        print(f"  Reading {csv_file.name}...")

        try:
            # First, try to read CSV with pandas, handling bad lines gracefully
            # Use the csv module to read first and determine the correct number of columns
            expected_cols = None
            with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
                # Read first few lines to determine expected column count
                sample_lines = []
                for i, line in enumerate(f):
                    if i >= 10:  # Sample first 10 lines
                        break
                    sample_lines.append(line)
                
                # Try to parse header
                if sample_lines:
                    header_reader = csv.reader([sample_lines[0]], delimiter=",", quotechar='"')
                    header = next(header_reader)
                    expected_cols = len(header)
            
            # Now try pandas with on_bad_lines, using Python engine for better error handling
            try:
                df = pd.read_csv(
                    csv_file,
                    encoding="utf-8",
                    low_memory=False,
                    engine="python",  # Use Python engine for better error tolerance
                    on_bad_lines="skip",  # Skip malformed lines
                    quoting=csv.QUOTE_MINIMAL,
                    escapechar="\\",
                )
            except TypeError:
                # Older pandas versions don't have on_bad_lines
                try:
                    df = pd.read_csv(
                        csv_file,
                        encoding="utf-8",
                        low_memory=False,
                        engine="python",  # Use Python engine
                        error_bad_lines=False,  # Skip malformed lines
                        warn_bad_lines=True,
                        quoting=csv.QUOTE_MINIMAL,
                        escapechar="\\",
                    )
                except (TypeError, ValueError):
                    # Fallback: read with basic settings and Python engine
                    df = pd.read_csv(
                        csv_file,
                        encoding="utf-8",
                        low_memory=False,
                        engine="python",
                        sep=",",
                        quotechar='"',
                        escapechar="\\",
                    )

            # Add UF columns
            df["uf_id"] = uf_id
            df["uf_sigla"] = uf_sigla

            # Reorder columns to put UF info first
            cols = ["uf_id", "uf_sigla"] + [c for c in df.columns if c not in ["uf_id", "uf_sigla"]]
            df = df[cols]

            all_dataframes.append(df)
            print(f"    [OK] {len(df)} rows")

        except Exception as e:
            print(f"    [ERROR] Failed to read {csv_file.name}: {e}")
            # Try alternative method: read line by line and fix manually
            try:
                print(f"    [RETRY] Trying alternative CSV reading method...")
                rows = []
                with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
                    # Use csv.reader with proper quoting to handle commas in fields
                    reader = csv.reader(f, quotechar='"', delimiter=",", escapechar="\\")
                    header = next(reader)  # Get header
                    expected_cols = len(header)
                    
                    for line_num, row in enumerate(reader, start=2):
                        # Try to fix rows with wrong number of fields
                        if len(row) > expected_cols:
                            # Merge extra fields into the last field (likely unquoted comma)
                            row = row[: expected_cols - 1] + [", ".join(row[expected_cols - 1 :])]
                        elif len(row) < expected_cols:
                            # Pad with empty strings
                            row = row + [""] * (expected_cols - len(row))
                        
                        # Only add if we have the right number of columns now
                        if len(row) == expected_cols:
                            rows.append(row)
                        else:
                            # Skip malformed rows
                            if line_num <= 10:  # Only warn for first few errors
                                print(f"      [WARN] Skipping malformed row {line_num} (expected {expected_cols} cols, got {len(row)})")

                if rows:
                    df = pd.DataFrame(rows, columns=header)
                    df["uf_id"] = uf_id
                    df["uf_sigla"] = uf_sigla
                    cols = ["uf_id", "uf_sigla"] + [c for c in df.columns if c not in ["uf_id", "uf_sigla"]]
                    df = df[cols]
                    all_dataframes.append(df)
                    print(f"    [OK] {len(df)} rows (alternative method)")
                else:
                    print(f"    [ERROR] No valid rows found in {csv_file.name}")
            except Exception as e2:
                print(f"    [ERROR] Alternative method also failed: {e2}")
            continue

    if not all_dataframes:
        print("[ERROR] No valid CSV files to merge!")
        return

    # Concatenate all dataframes
    print("\nConcatenating dataframes...")
    merged_df = pd.concat(all_dataframes, ignore_index=True)

    # Save merged CSV
    output_file.parent.mkdir(parents=True, exist_ok=True)
    merged_df.to_csv(output_file, index=False, encoding="utf-8")

    print(f"\n[SUCCESS] Merged CSV saved to: {output_file}")
    print(f"  Total rows: {len(merged_df)}")
    print(f"  Total columns: {len(merged_df.columns)}")
    print(f"  File size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")


def main():
    """Main function to download and merge CSV files."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download CSV files for each UF and merge them into a single file"
    )
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
        help="Directory containing data (default: data-raw)",
    )
    parser.add_argument(
        "--csv-dir",
        type=str,
        default=None,
        help="Directory to save individual CSV files (default: data-dir/csvs)",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Path to save merged CSV file (default: data-dir/csvs_merged.csv)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--start-uf",
        type=int,
        default=None,
        help="UF ID to start from (for resuming)",
    )
    parser.add_argument(
        "--skip-merge",
        action="store_true",
        help="Skip merging step, only download CSVs",
    )

    args = parser.parse_args()

    # Setup paths
    data_dir = Path(args.data_dir)
    metadata_dir = data_dir / "json" / "metadata"
    csv_dir = Path(args.csv_dir) if args.csv_dir else data_dir / "csvs"
    output_file = (
        Path(args.output_file)
        if args.output_file
        else data_dir / "csvs_merged.csv"
    )

    # Load cookies
    print("Loading cookies...")
    try:
        cookies, fingerprint = load_cookies(args.cookies_file)
        print(f"[OK] Loaded cookies from {args.cookies_file}")
    except Exception as e:
        print(f"[ERROR] Failed to load cookies: {e}")
        return

    # Create API client
    client = BNMPAPIClient(cookies=cookies, fingerprint=fingerprint)

    # Load estados
    print("Loading estados...")
    try:
        estados = load_estados(metadata_dir)
        print(f"[OK] Loaded {len(estados)} estados")
    except Exception as e:
        print(f"[ERROR] Failed to load estados: {e}")
        return

    # Filter estados if start-uf is specified
    if args.start_uf:
        estados = [e for e in estados if e["id"] >= args.start_uf]
        print(f"Starting from UF ID {args.start_uf}: {len(estados)} estados remaining")

    # Download CSVs for each UF
    print("\n" + "=" * 60)
    print("Downloading CSV files for each UF...")
    print("=" * 60)

    csv_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    skipped = 0
    failed = 0

    for estado in estados:
        uf_id = estado["id"]
        uf_nome = estado["nome"]
        uf_sigla = estado["sigla"]

        print(f"\nProcessing UF: {uf_nome} ({uf_sigla}, ID: {uf_id})")

        result = download_csv_for_uf(
            client=client,
            uf_id=uf_id,
            uf_sigla=uf_sigla,
            output_dir=csv_dir,
            delay=args.delay,
        )

        if result:
            downloaded += 1
        elif result is None and (csv_dir / f"uf_{uf_id}_{uf_sigla}.csv").exists():
            skipped += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print("Download Summary")
    print("=" * 60)
    print(f"  Downloaded: {downloaded}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(estados)}")

    # Merge CSVs if not skipped
    if not args.skip_merge:
        merge_csvs(csv_dir, output_file)
    else:
        print("\n[Skipping merge step as requested]")


if __name__ == "__main__":
    main()

