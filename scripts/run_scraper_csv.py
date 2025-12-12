"""Script to download PDFs and JSONs from CSV merged file."""

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bnmpy import BNMPAPIClient, load_cookies


def normalize_case_id(numero: str) -> str:
    """
    Normalize case ID by removing dots and dashes.
    
    Args:
        numero: Case number (e.g., "0001070-63.2015.8.10.0037.01.0001-26")
    
    Returns:
        Normalized case ID (e.g., "0001070632015810003701000126")
    """
    return numero.replace(".", "").replace("-", "")


def get_process_number_first_25(numero: str) -> str:
    """
    Get first 20 numeric digits of the process number for API search.
    
    Format example: "0001070-63.2015.8.10.0037.01.0001-26"
    Extract only digits: "0001070632015810003701000126"
    First 20 digits: "00010706320158100037"
    
    Args:
        numero: Full case number (e.g., "0001070-63.2015.8.10.0037.01.0001-26")
    
    Returns:
        First 20 numeric digits (process number for API)
    """
    # Extract only numeric digits
    digits_only = ''.join(c for c in numero if c.isdigit())
    # Take first 20 digits
    return digits_only[:20]


def download_json_for_case(
    client: BNMPAPIClient,
    numero_processo: str,
    numero_completo: str,
    json_dir: Path,
    delay: float = 0.5,
) -> Path | None:
    """
    Download JSON for a specific case using numeroProcesso filter.
    
    Args:
        client: BNMP API client
        numero_processo: Process number normalized (first 25 chars, no dots/dashes) for API
        numero_completo: Full case number for filename
        json_dir: Directory to save JSON files
        delay: Delay between requests in seconds
    
    Returns:
        Path to saved JSON file, or None if download failed
    """
    # Normalize case ID for filename using full number
    case_id = normalize_case_id(numero_completo)
    json_filename = f"{case_id}.json"
    json_path = json_dir / json_filename
    
    # Skip if already downloaded
    if json_path.exists():
        return json_path
    
    try:
        # Validate numero_processo
        if not numero_processo or len(numero_processo) != 20 or not numero_processo.isdigit():
            print(f"    [ERROR] Invalid numero_processo format: '{numero_processo}' (length: {len(numero_processo) if numero_processo else 0})")
            return None
        
        # Make API request with numeroProcesso filter
        # numero_processo should be exactly 20 numeric digits
        # Start with size=10 (same as curl example), then we can paginate if needed
        response = client.pesquisa_pecas_filter(
            busca_orgao_recursivo=False,
            orgao_expeditor={},
            numero_processo=numero_processo,
            page=0,
            size=10,  # Start with 10 (same as curl example)
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Save JSON file
            json_dir.mkdir(parents=True, exist_ok=True)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            time.sleep(delay)
            return json_path
        else:
            print(f"    [ERROR] Failed to download JSON for {numero_processo}: HTTP {response.status_code}")
            if response.text:
                print(f"      Response: {response.text[:500]}")
            return None
    
    except Exception as e:
        print(f"    [ERROR] Exception downloading JSON for {numero_processo}: {e}")
        return None


def download_pdf_for_result(
    client: BNMPAPIClient,
    result: dict[str, Any],
    pdf_dir: Path,
    delay: float = 0.5,
) -> bool:
    """
    Download PDF for a single result.
    
    Args:
        client: BNMP API client
        result: Result dictionary from API response
        pdf_dir: Directory to save PDF files
        delay: Delay between requests in seconds
    
    Returns:
        True if downloaded successfully, False otherwise
    """
    certidao_id = result.get("id")
    id_tipo_peca = result.get("idTipoPeca")
    
    if not certidao_id or id_tipo_peca is None:
        return False
    
    # Use same naming scheme as run_scraper.py
    pdf_filename = f"certidao_{certidao_id}_tipo_{id_tipo_peca}.pdf"
    pdf_path = pdf_dir / pdf_filename
    
    # Skip if already exists
    if pdf_path.exists():
        return True
    
    try:
        response = client.download_pdf(certidao_id, id_tipo_peca)
        
        if response.status_code == 200:
            # Check if response is actually PDF
            content_type = response.headers.get("content-type", "")
            if "pdf" in content_type.lower() or response.content[:4] == b"%PDF":
                pdf_dir.mkdir(parents=True, exist_ok=True)
                with open(pdf_path, "wb") as f:
                    f.write(response.content)
                time.sleep(delay)
                return True
            else:
                return False
        else:
            return False
    
    except Exception as e:
        return False


def process_single_case(
    row_data: tuple[int, dict[str, Any]],
    cookies: list[dict[str, Any]],
    fingerprint: str | None,
    data_dir: Path,
    delay: float,
    total_rows: int,
    counters: dict[str, int],
    lock: threading.Lock,
) -> None:
    """
    Process a single case (row) from CSV.
    
    Args:
        row_data: Tuple of (row_number, row_dict)
        cookies: Cookies for API client
        fingerprint: Fingerprint for API client
        data_dir: Base data directory
        delay: Delay between requests
        total_rows: Total number of rows (for progress display)
        counters: Dictionary with counters (json_downloaded, json_skipped, etc.)
        lock: Thread lock for thread-safe counter updates
    """
    row_num, row = row_data
    json_dir = data_dir / "json_ids"
    pdf_dir = data_dir / "pdfs"
    
    # Create client for this thread
    client = BNMPAPIClient(cookies=cookies, fingerprint=fingerprint)
    
    numero = str(row.get("Número", "")).strip()
    
    if not numero or numero == "nan" or numero == "None":
        with lock:
            print(f"[{row_num}/{total_rows}] Skipping row with empty Número")
        return
    
    # Get process number for API search (first 20 digits of normalized number)
    numero_processo = get_process_number_first_25(numero)
    case_id = normalize_case_id(numero)
    
    # Validate that we have exactly 20 digits
    if len(numero_processo) != 20:
        with lock:
            print(f"[{row_num}/{total_rows}] [ERROR] Invalid process number length: {numero_processo} (length: {len(numero_processo)})")
            counters["json_failed"] += 1
        return
    
    with lock:
        print(f"[{row_num}/{total_rows}] Processing case: {numero}")
        print(f"  Process number (first 20 digits): {numero_processo}")
        print(f"  Case ID: {case_id}")
    
    # Download JSON
    json_path = download_json_for_case(
        client=client,
        numero_processo=numero_processo,
        numero_completo=numero,
        json_dir=json_dir,
        delay=delay,
    )
    
    if json_path:
        if json_path.exists() and json_path.stat().st_size > 0:
            with lock:
                counters["json_downloaded"] += 1
                print(f"  [OK] JSON downloaded: {json_path.name}")
            
            # Load JSON to get results
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                
                results = json_data.get("content", [])
                total_results = json_data.get("totalElements", 0)
                
                with lock:
                    print(f"  Found {total_results} results in JSON")
                
                # Download PDFs for each result
                for result_idx, result in enumerate(results):
                    certidao_id = result.get("id")
                    id_tipo_peca = result.get("idTipoPeca")
                    nome_pessoa = result.get("nomePessoa", "Unknown")
                    
                    pdf_filename = f"certidao_{certidao_id}_tipo_{id_tipo_peca}.pdf"
                    
                    if pdf_dir.joinpath(pdf_filename).exists():
                        with lock:
                            counters["pdf_skipped"] += 1
                        continue
                    
                    with lock:
                        print(f"    Downloading PDF {result_idx + 1}/{len(results)}: {nome_pessoa} (ID: {certidao_id})")
                    
                    if download_pdf_for_result(client, result, pdf_dir, delay):
                        with lock:
                            counters["pdf_downloaded"] += 1
                            print(f"      [OK] PDF downloaded: {pdf_filename}")
                    else:
                        with lock:
                            counters["pdf_failed"] += 1
                            print(f"      [ERROR] Failed to download PDF")
            
            except Exception as e:
                with lock:
                    print(f"  [ERROR] Failed to read JSON file: {e}")
        else:
            with lock:
                counters["json_skipped"] += 1
    else:
        # Check if JSON already exists
        json_filename = f"{case_id}.json"
        json_path = json_dir / json_filename
        if json_path.exists():
            with lock:
                counters["json_skipped"] += 1
                print(f"  [SKIP] JSON already exists: {json_filename}")
            
            # Try to load existing JSON and download PDFs
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                
                results = json_data.get("content", [])
                with lock:
                    print(f"  Found {len(results)} results in existing JSON")
                
                for result in results:
                    certidao_id = result.get("id")
                    id_tipo_peca = result.get("idTipoPeca")
                    pdf_filename = f"certidao_{certidao_id}_tipo_{id_tipo_peca}.pdf"
                    
                    if pdf_dir.joinpath(pdf_filename).exists():
                        with lock:
                            counters["pdf_skipped"] += 1
                    else:
                        if download_pdf_for_result(client, result, pdf_dir, delay):
                            with lock:
                                counters["pdf_downloaded"] += 1
                        else:
                            with lock:
                                counters["pdf_failed"] += 1
            except Exception as e:
                with lock:
                    print(f"  [ERROR] Failed to read existing JSON: {e}")
        else:
            with lock:
                counters["json_failed"] += 1
    
    with lock:
        print()  # Empty line between cases


def process_csv(
    csv_file: Path,
    cookies: list[dict[str, Any]],
    fingerprint: str | None,
    data_dir: Path,
    delay: float = 0.5,
    start_row: int = 0,
    max_rows: int | None = None,
    max_workers: int = 1,
) -> None:
    """
    Process CSV file and download JSONs and PDFs for each case.
    
    Args:
        csv_file: Path to merged CSV file
        cookies: Cookies for API client
        fingerprint: Fingerprint for API client
        data_dir: Base data directory
        delay: Delay between requests in seconds
        start_row: Row to start from (for resuming)
        max_rows: Maximum number of rows to process (None = all)
        max_workers: Number of parallel workers (1 = sequential)
    """
    json_dir = data_dir / "json_ids"
    pdf_dir = data_dir / "pdfs"
    
    json_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading CSV file: {csv_file}")
    print(f"  JSON output directory: {json_dir}")
    print(f"  PDF output directory: {pdf_dir}")
    
    # Read CSV file
    try:
        df = pd.read_csv(csv_file, encoding="utf-8", low_memory=False)
    except Exception as e:
        print(f"[ERROR] Failed to read CSV file: {e}")
        return
    
    total_rows = len(df)
    print(f"Total rows in CSV: {total_rows}")
    
    # Filter rows if needed
    if start_row > 0:
        df = df.iloc[start_row:]
        print(f"Starting from row {start_row}")
    
    if max_rows is not None:
        df = df.head(max_rows)
        print(f"Processing up to {max_rows} rows")
    
    rows_to_process = len(df)
    print(f"Rows to process: {rows_to_process}")
    print(f"Parallel workers: {max_workers}")
    print()
    
    # Prepare row data
    row_data_list = []
    for idx, row in df.iterrows():
        row_num = idx + 1 + start_row
        row_data_list.append((row_num, row.to_dict()))
    
    # Thread-safe counters
    counters = {
        "json_downloaded": 0,
        "json_skipped": 0,
        "json_failed": 0,
        "pdf_downloaded": 0,
        "pdf_skipped": 0,
        "pdf_failed": 0,
    }
    lock = threading.Lock()
    
    if max_workers > 1:
        # Parallel processing
        print(f"Processing {rows_to_process} cases in parallel ({max_workers} workers)...\n")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    process_single_case,
                    row_data,
                    cookies,
                    fingerprint,
                    data_dir,
                    delay,
                    total_rows,
                    counters,
                    lock,
                ): row_data[0]
                for row_data in row_data_list
            }
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                row_num = futures[future]
                try:
                    future.result()
                except Exception as e:
                    with lock:
                        print(f"[{row_num}/{total_rows}] [ERROR] Exception processing case: {e}")
                        counters["json_failed"] += 1
                
                if completed % 10 == 0:
                    with lock:
                        print(f"\n[PROGRESS] Completed {completed}/{rows_to_process} cases\n")
    else:
        # Sequential processing
        print(f"Processing {rows_to_process} cases sequentially...\n")
        
        for row_data in row_data_list:
            try:
                process_single_case(
                    row_data,
                    cookies,
                    fingerprint,
                    data_dir,
                    delay,
                    total_rows,
                    counters,
                    lock,
                )
            except Exception as e:
                row_num = row_data[0]
                print(f"[{row_num}/{total_rows}] [ERROR] Exception processing case: {e}")
                counters["json_failed"] += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("Download Summary")
    print("=" * 60)
    print(f"JSON files:")
    print(f"  Downloaded: {counters['json_downloaded']}")
    print(f"  Skipped: {counters['json_skipped']}")
    print(f"  Failed: {counters['json_failed']}")
    print(f"PDF files:")
    print(f"  Downloaded: {counters['pdf_downloaded']}")
    print(f"  Skipped: {counters['pdf_skipped']}")
    print(f"  Failed: {counters['pdf_failed']}")
    print("=" * 60)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Download PDFs and JSONs from CSV merged file"
    )
    parser.add_argument(
        "--cookies-file",
        type=str,
        default="cookies.json",
        help="Path to cookies file (default: cookies.json)",
    )
    parser.add_argument(
        "--csv-file",
        type=str,
        default="data-raw/csvs_merged.csv",
        help="Path to merged CSV file (default: data-raw/csvs_merged.csv)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data-raw",
        help="Directory to save data (default: data-raw)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--start-row",
        type=int,
        default=0,
        help="Row number to start from (for resuming, default: 0)",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Maximum number of rows to process (default: all)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers for downloads (default: 1 = sequential)",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("BNMP CSV Scraper")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Cookies file: {args.cookies_file}")
    print(f"  CSV file: {args.csv_file}")
    print(f"  Data directory: {args.data_dir}")
    print(f"  Delay between requests: {args.delay}s")
    print(f"  Start row: {args.start_row}")
    print(f"  Max rows: {args.max_rows or 'all'}")
    print()
    
    # Load cookies
    cookies_file = Path(args.cookies_file)
    if not cookies_file.exists():
        print(f"[ERROR] Cookies file not found: {cookies_file}")
        return 1
    
    print(f"[OK] Loading cookies from {cookies_file}")
    cookies, fingerprint = load_cookies(cookies_file)
    print(f"  Cookies: {len(cookies)}")
    print(f"  Fingerprint: {fingerprint or 'Not set'}")
    
    # Process CSV
    csv_file = Path(args.csv_file)
    if not csv_file.exists():
        print(f"[ERROR] CSV file not found: {csv_file}")
        return 1
    
    data_dir = Path(args.data_dir)
    
    print("\n" + "=" * 60)
    print("Starting CSV processing...")
    print("=" * 60 + "\n")
    
    try:
        process_csv(
            csv_file=csv_file,
            cookies=cookies,
            fingerprint=fingerprint,
            data_dir=data_dir,
            delay=args.delay,
            start_row=args.start_row,
            max_rows=args.max_rows,
            max_workers=args.workers,
        )
        print("\n" + "=" * 60)
        print("[SUCCESS] CSV processing completed!")
        print("=" * 60)
        return 0
    except KeyboardInterrupt:
        print("\n\n[INFO] Processing interrupted by user")
        print("You can resume by using --start-row option")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

