"""Scraper for downloading BNMP data."""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from bnmpy.api_client import BNMPAPIClient


class BNMPScraper:
    """Scraper for downloading BNMP portal data."""

    def __init__(
        self,
        client: BNMPAPIClient,
        data_dir: str | Path = "data-raw",
        page_size: int = 30,
        max_results_per_combination: int = 10000,
        delay_between_requests: float = 0.5,
        max_workers: int = 1,
    ):
        """
        Initialize the scraper.

        Args:
            client: BNMPAPIClient instance
            data_dir: Directory to save downloaded data
            page_size: Number of results per page (test different values)
            max_results_per_combination: Maximum results per UF+municipality combination
            delay_between_requests: Delay in seconds between API requests
            max_workers: Number of parallel workers for downloads (1 = sequential)
        """
        self.client = client
        self.data_dir = Path(data_dir)
        self.page_size = page_size
        self.max_results_per_combination = max_results_per_combination
        self.delay_between_requests = delay_between_requests
        self.max_workers = max_workers

        # Create data directory structure
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "json").mkdir(exist_ok=True)
        (self.data_dir / "pdfs").mkdir(exist_ok=True)
        (self.data_dir / "metadata").mkdir(exist_ok=True)

        # Thread lock for file operations
        self.file_lock = threading.Lock()

    def get_estados(self) -> list[dict[str, Any]]:
        """Get list of all states."""
        print("Fetching list of states (UFs)...")
        response = self.client.get_estados()
        response.raise_for_status()
        estados = response.json()
        print(f"Found {len(estados)} states")
        return estados

    def get_municipios(self, uf_id: int) -> list[dict[str, Any]]:
        """Get list of municipalities for a UF."""
        response = self.client.get_municipios_por_uf(uf_id)
        response.raise_for_status()
        municipios = response.json()
        return municipios

    def save_json(self, data: dict[str, Any], filename: str) -> Path:
        """Save JSON data to file."""
        filepath = self.data_dir / "json" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with self.file_lock:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath

    def save_pdf(self, content: bytes, filename: str) -> Path:
        """Save PDF content to file."""
        filepath = self.data_dir / "pdfs" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with self.file_lock:
            with open(filepath, "wb") as f:
                f.write(content)
        return filepath

    def file_exists(self, subdir: str, filename: str) -> bool:
        """Check if a file already exists."""
        filepath = self.data_dir / subdir / filename
        return filepath.exists()

    def _download_single_page(
        self,
        uf_id: int,
        municipio_id: int | None,
        page: int,
        effective_page_size: int,
        filename_prefix: str,
    ) -> tuple[int, dict[str, Any] | None, Exception | None]:
        """
        Download a single page (for parallel execution).

        Returns:
            Tuple of (page_number, page_data or None, error or None)
        """
        filename = f"{filename_prefix}_page_{page}_size_{effective_page_size}.json"
        filename_original = f"{filename_prefix}_page_{page}_size_{self.page_size}.json"

        # Check if file already exists
        if self.file_exists("json", filename) or self.file_exists("json", filename_original):
            if self.file_exists("json", filename):
                filepath = self.data_dir / "json" / filename
            else:
                filepath = self.data_dir / "json" / filename_original

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    page_data = json.load(f)
                return (page, page_data, None)
            except Exception as e:
                return (page, None, e)

        # Make API request
        try:
            filter_kwargs = {
                "busca_orgao_recursivo": False,
                "orgao_expeditor": {},
                "id_estado": uf_id,
                "page": page,
                "size": effective_page_size,
            }
            if municipio_id is not None:
                filter_kwargs["id_municipio"] = municipio_id

            response = self.client.pesquisa_pecas_filter(**filter_kwargs)

            if response.status_code == 200:
                page_data = response.json()
                # Save the file
                self.save_json(page_data, filename)
                time.sleep(self.delay_between_requests)
                return (page, page_data, None)
            elif response.status_code == 400 and effective_page_size > 10:
                # Try with smaller size
                filter_kwargs["size"] = 10
                response = self.client.pesquisa_pecas_filter(**filter_kwargs)
                if response.status_code == 200:
                    page_data = response.json()
                    filename = f"{filename_prefix}_page_{page}_size_10.json"
                    self.save_json(page_data, filename)
                    time.sleep(self.delay_between_requests)
                    return (page, page_data, None)
                else:
                    error_msg = f"Status {response.status_code}"
                    return (page, None, Exception(error_msg))
            else:
                error_msg = f"Status {response.status_code}"
                return (page, None, Exception(error_msg))

        except Exception as e:
            return (page, None, e)

    def download_filter_results(
        self,
        uf_id: int,
        municipio_id: int | None = None,
        uf_name: str = "",
        municipio_name: str = "",
    ) -> list[dict[str, Any]]:
        """
        Download all filter results for a UF and optionally a municipality.

        Args:
            uf_id: State ID
            municipio_id: Optional municipality ID
            uf_name: State name (for file naming)
            municipio_name: Municipality name (for file naming)

        Returns:
            List of all results
        """
        # Build filename prefix
        if municipio_id is not None:
            filename_prefix = f"uf_{uf_id}_municipio_{municipio_id}"
            display_name = f"UF {uf_name} (ID: {uf_id}), Município {municipio_name} (ID: {municipio_id})"
        else:
            filename_prefix = f"uf_{uf_id}"
            display_name = f"UF {uf_name} (ID: {uf_id})"

        print(f"\nDownloading results for {display_name}...")

        # First, get the first page to determine total pages and effective page size
        print("  Fetching first page to determine total pages...")
        first_page_result = self._download_single_page(
            uf_id, municipio_id, 0, self.page_size, filename_prefix
        )

        page_num, first_page_data, error = first_page_result

        if error or not first_page_data:
            if error:
                print(f"  [ERROR] Failed to get first page: {error}")
            else:
                print(f"  [ERROR] No data returned from first page")
            return []

        total_pages = first_page_data.get("totalPages", 1)
        total_elements = first_page_data.get("totalElements", 0)
        effective_page_size = len(first_page_data.get("content", []))

        print(f"  Total: {total_elements} elements, {total_pages} pages")
        print(f"  Effective page size: {effective_page_size}")

        # Check if we've reached the max results limit
        if total_elements >= self.max_results_per_combination:
            print(f"  [WARN] Total ({total_elements}) exceeds max ({self.max_results_per_combination})")
            total_pages = (self.max_results_per_combination + effective_page_size - 1) // effective_page_size

        all_results: list[dict[str, Any]] = []
        all_results.extend(first_page_data.get("content", []))

        # Download remaining pages
        if total_pages > 1:
            pages_to_download = list(range(1, total_pages))
            
            if self.max_workers > 1 and len(pages_to_download) > 1:
                # Parallel download
                print(f"  Downloading {len(pages_to_download)} pages in parallel ({self.max_workers} workers)...")
                page_results: dict[int, dict[str, Any]] = {}
                errors: list[tuple[int, Exception]] = []

                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {
                        executor.submit(
                            self._download_single_page,
                            uf_id,
                            municipio_id,
                            page,
                            effective_page_size,
                            filename_prefix,
                        ): page
                        for page in pages_to_download
                    }

                    for future in as_completed(futures):
                        page_num, page_data, error = future.result()
                        if error:
                            errors.append((page_num, error))
                            print(f"  [ERROR] Page {page_num}: {error}")
                        elif page_data:
                            page_results[page_num] = page_data
                            content_len = len(page_data.get("content", []))
                            print(f"  [OK] Page {page_num}: {content_len} items")

                # Sort results by page number
                for page_num in sorted(page_results.keys()):
                    all_results.extend(page_results[page_num].get("content", []))

                if errors:
                    print(f"  [WARN] {len(errors)} pages failed to download")

            else:
                # Sequential download
                print(f"  Downloading {len(pages_to_download)} pages sequentially...")
                for page in pages_to_download:
                    if len(all_results) >= self.max_results_per_combination:
                        break

                    page_num, page_data, error = self._download_single_page(
                        uf_id, municipio_id, page, effective_page_size, filename_prefix
                    )

                    if error:
                        print(f"  [ERROR] Page {page}: {error}")
                        break
                    elif page_data:
                        content = page_data.get("content", [])
                        print(f"  Page {page}: {len(content)} items")
                        all_results.extend(content)

        print(f"  Downloaded {len(all_results)} total results")
        return all_results

    def download_pdf_for_person(
        self, certidao_id: int, id_tipo_peca: int, uf_id: int | None = None, person_name: str = ""
    ) -> bool:
        """
        Download PDF for a specific person.

        Args:
            certidao_id: Certificate ID (the 'id' field from filter results)
            id_tipo_peca: Type of piece ID (the 'idTipoPeca' field from filter results)
            uf_id: Optional State ID (for file naming only)
            person_name: Optional person name for file naming

        Returns:
            True if downloaded successfully, False otherwise
        """
        # Use id_tipo_peca in filename instead of uf_id
        filename = f"certidao_{certidao_id}_tipo_{id_tipo_peca}.pdf"

        # Check if already downloaded
        if self.file_exists("pdfs", filename):
            return True

        try:
            response = self.client.download_pdf(certidao_id, id_tipo_peca)

            if response.status_code == 200:
                # Check if response is actually PDF
                content_type = response.headers.get("content-type", "")
                if "pdf" in content_type.lower() or response.content[:4] == b"%PDF":
                    self.save_pdf(response.content, filename)
                    time.sleep(self.delay_between_requests)
                    return True
                else:
                    return False
            else:
                return False

        except Exception as e:
            return False

    def _download_pdfs_for_results(
        self, results: list[dict[str, Any]], uf_id: int
    ) -> None:
        """Download PDFs for all results."""
        if not results:
            print(f"\n  No results to download PDFs for")
            return

        print(f"\n  Downloading PDFs for {len(results)} results...")

        if self.max_workers > 1:
            # Parallel PDF download
            print(f"  Using {self.max_workers} parallel workers...")
            downloaded = 0
            skipped = 0
            errors = 0

            def download_pdf_task(result: dict[str, Any]) -> tuple[bool, bool, bool]:
                """Download a single PDF. Returns (downloaded, skipped, error)."""
                certidao_id = result.get("id")
                id_tipo_peca = result.get("idTipoPeca")

                if not certidao_id or id_tipo_peca is None:
                    return (False, False, True)

                filename = f"certidao_{certidao_id}_tipo_{id_tipo_peca}.pdf"
                if self.file_exists("pdfs", filename):
                    return (False, True, False)

                if self.download_pdf_for_person(certidao_id, id_tipo_peca, uf_id):
                    return (True, False, False)
                else:
                    return (False, False, True)

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(download_pdf_task, result): i for i, result in enumerate(results)}

                completed = 0
                for future in as_completed(futures):
                    completed += 1
                    d, s, e = future.result()
                    if d:
                        downloaded += 1
                    elif s:
                        skipped += 1
                    elif e:
                        errors += 1

                    if completed % 100 == 0:
                        print(f"    Progress: {completed}/{len(results)} (downloaded: {downloaded}, skipped: {skipped}, errors: {errors})")

            print(
                f"  PDF download complete: {downloaded} downloaded, {skipped} skipped, {errors} errors"
            )
        else:
            # Sequential PDF download
            downloaded = 0
            skipped = 0
            errors = 0

            for i, result in enumerate(results):
                # The API requires 'id' and 'idTipoPeca' fields
                certidao_id = result.get("id")
                id_tipo_peca = result.get("idTipoPeca")

                if not certidao_id:
                    errors += 1
                    continue

                if id_tipo_peca is None:
                    errors += 1
                    continue

                person_name = result.get("nomePessoa", "")

                if self.download_pdf_for_person(certidao_id, id_tipo_peca, uf_id, person_name):
                    downloaded += 1
                elif self.file_exists("pdfs", f"certidao_{certidao_id}_tipo_{id_tipo_peca}.pdf"):
                    skipped += 1
                else:
                    errors += 1

                if (i + 1) % 100 == 0:
                    print(
                        f"    Progress: {i+1}/{len(results)} (downloaded: {downloaded}, skipped: {skipped}, errors: {errors})"
                    )

            print(
                f"  PDF download complete: {downloaded} downloaded, {skipped} skipped, {errors} errors"
            )

    def scrape_all(
        self,
        start_uf_id: int | None = None,
        start_municipio_id: int | None = None,
        skip_small_ufs: bool = True,
    ) -> None:
        """
        Scrape all data: UFs, municipalities, filter results, and PDFs.

        Args:
            start_uf_id: Optional UF ID to start from (for resuming)
            start_municipio_id: Optional municipality ID to start from (for resuming)
            skip_small_ufs: If True, skip municipality iteration for UFs with < 10000 results
        """
        estados = self.get_estados()

        # Save estados metadata
        self.save_json(
            {"estados": estados, "total": len(estados)},
            "metadata/estados.json",
        )

        start_processing = start_uf_id is None

        for estado in estados:
            uf_id = estado.get("id")
            uf_name = estado.get("nome", estado.get("sigla", f"UF_{uf_id}"))

            if not start_processing:
                if uf_id == start_uf_id:
                    start_processing = True
                else:
                    continue

            print(f"\n{'='*60}")
            print(f"Processing UF: {uf_name} (ID: {uf_id})")
            print(f"{'='*60}")

            # First, check total results for this UF
            print("Checking total results for UF...")
            try:
                test_results = self.download_filter_results(
                    uf_id=uf_id,
                    municipio_id=None,
                    uf_name=uf_name,
                    municipio_name="",
                )

                total_results_uf = len(test_results)
            except Exception as e:
                print(f"  [ERROR] Failed to get results for UF {uf_name}: {e}")
                import traceback
                traceback.print_exc()
                total_results_uf = 0
                test_results = []

            if skip_small_ufs and total_results_uf < self.max_results_per_combination:
                print(
                    f"  UF has {total_results_uf} results (< {self.max_results_per_combination}), skipping municipality iteration"
                )
                # Download PDFs for this UF
                self._download_pdfs_for_results(test_results, uf_id)
            else:
                # Get municipalities for this UF
                print(f"\nFetching municipalities for UF {uf_name}...")
                municipios = self.get_municipios(uf_id)
                print(f"Found {len(municipios)} municipalities")

                # Save municipios metadata
                self.save_json(
                    {
                        "uf_id": uf_id,
                        "uf_name": uf_name,
                        "municipios": municipios,
                        "total": len(municipios),
                    },
                    f"metadata/municipios_uf_{uf_id}.json",
                )

                start_municipio_processing = (
                    start_municipio_id is None or start_uf_id != uf_id
                )

                for municipio in municipios:
                    municipio_id = municipio.get("id")
                    municipio_name = municipio.get("nome", f"Municipio_{municipio_id}")

                    if not start_municipio_processing:
                        if municipio_id == start_municipio_id:
                            start_municipio_processing = True
                        else:
                            continue

                    print(f"\n  Processing Município: {municipio_name} (ID: {municipio_id})")

                    # Download filter results
                    results = self.download_filter_results(
                        uf_id=uf_id,
                        municipio_id=municipio_id,
                        uf_name=uf_name,
                        municipio_name=municipio_name,
                    )

                    # Download PDFs
                    self._download_pdfs_for_results(results, uf_id)

            print(f"\nCompleted UF {uf_name}")
