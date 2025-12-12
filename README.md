# BNMP Scraper Usage Guide

## Overview

The BNMP scraper downloads all data from the BNMP portal:
1. Iterates through all states (UFs) and municipalities
2. Downloads all filter results (max 10000 per UF+municipality combination)
3. Downloads all PDF certificates (one per person)

## Setup

This project uses [uv](https://github.com/astral-sh/uv) for package management.

### Install uv

If you don't have uv installed:

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install Dependencies

```bash
# Install project dependencies
uv sync

# Or install in editable mode (recommended for development)
uv pip install -e .
```

### Install Playwright Browsers

After installing dependencies, install the Chromium browser:

```bash
uv run playwright install chromium
```

## Quick Start

### 1. Get Authentication Session

First, you need to get a valid session by solving the captcha:

```bash
python main.py
```

This will:
- Open a browser
- Navigate to the portal
- Wait for you to solve the captcha
- Save cookies and fingerprint to `cookies.json`

### 2. Run the Scraper

```bash
python scripts/run_scraper.py
```

This will start scraping all data. The scraper will:
- Create `data-raw/` directory structure
- Download JSON files with filter results
- Download PDF files for each person
- Skip already downloaded files (resume capability)

------------------------------------

## Directory Structure

The scraper creates the following structure:

```
data-raw/
├── json/                          # JSON files with filter results
│   ├── uf_2_page_0_size_100.json
│   ├── uf_2_municipio_123_page_0_size_100.json
│   └── ...
├── pdfs/                          # PDF certificates
│   ├── certidao_192556728_tipo_10.pdf
│   └── ...
└── metadata/                       # Metadata files
    ├── estados.json               # List of all states
    └── municipios_uf_2.json      # Municipalities for each UF
```

## File Naming Convention

### JSON Files
- `uf_{uf_id}_page_{page}_size_{size}.json` - Results for a UF
- `uf_{uf_id}_municipio_{municipio_id}_page_{page}_size_{size}.json` - Results for UF+municipality

### PDF Files
- `certidao_{certidao_id}_tipo_{id_tipo_peca}.pdf` - Certificate PDF

This naming ensures:
- No duplicate downloads
- Easy to resume if interrupted
- Clear organization by UF and municipality

## Command Line Options

```bash
python scripts/run_scraper.py [OPTIONS]
```

Options:
- `--cookies-file PATH` - Path to cookies file (default: cookies.json)
- `--data-dir PATH` - Directory to save data (default: data-raw)
- `--page-size SIZE` - Results per page (default: 30, will auto-reduce if needed)
- `--max-results N` - Max results per UF+municipality (default: 10000)
- `--delay SECONDS` - Delay between requests (default: 0.5)
- `--workers N` - Number of parallel workers for downloads (default: 1 = sequential)
- `--start-uf ID` - UF ID to start from (for resuming)
- `--start-municipio ID` - Municipality ID to start from (for resuming)
- `--no-skip-small` - Don't skip municipality iteration for small UFs


## Optimization Tips

### Page Size
Test different page sizes for faster downloads:
- Default: 30 (good balance)
- Minimum: 10 (slower but safer)

```bash
python scripts/run_scraper.py --page-size 30
```

### Delay Between Requests

Adjust delay to avoid rate limiting:
- Default: 0.5 seconds
- Increase if getting blocked: `--delay 1.0`
- Decrease for faster scraping: `--delay 0.2` (risky)

### Parallel Downloads

Use multiple workers to speed up downloads:
- Default: 1 worker (sequential)
- Recommended: 3-10 workers for faster downloads
- Example: `--workers 10`

**Note:** Parallel downloads are much faster but use more of your session time. Use with caution to avoid exhausting your authentication session too quickly.

### Skip Small UFs
For UFs with < 10000 results, the scraper skips municipality iteration by default. To disable:

```bash
python scripts/run_scraper.py --no-skip-small
```

## Programmatic Usage

You can also use the scraper programmatically:

```python
from bnmpy import BNMPAPIClient, load_cookies
from bnmpy.scraper import BNMPScraper

# Load cookies
cookies, fingerprint = load_cookies("cookies.json")

# Create client
client = BNMPAPIClient(cookies=cookies, fingerprint=fingerprint)

# Create scraper
scraper = BNMPScraper(
    client=client,
    data_dir="data-raw",
    page_size=30,
    max_results_per_combination=10000,
    delay_between_requests=0.5,
    max_workers=5,  # Use parallel downloads
)

# Run scraper
scraper.scrape_all()
```

## Monitoring Progress

The scraper prints progress information:
- Current UF and municipality being processed
- Page numbers and results count
- PDF download progress
- Error messages if any

Example output:
```
============================================================
Processing UF: São Paulo (ID: 2)
============================================================
Checking total results for UF...
Downloading results for UF São Paulo (ID: 2)...
  Fetching page 0 (size: 30)...
  Page 0: 30 items (total: 5000, pages: 167)
  ...
  Downloaded 5000 total results

  Downloading PDFs for 5000 results...
    Progress: 100/5000 (downloaded: 95, skipped: 5, errors: 0)
    ...
```

## Troubleshooting

### Authentication Errors
If you get 401 errors:
1. Check if cookies are expired: `python scripts/test_authentication.py`
2. Get fresh session: Run the captcha solving step again

### Rate Limiting
If requests are being blocked:
1. Increase delay: `--delay 1.0` or higher
2. Reduce page size: `--page-size 50`
3. Wait and resume later

### Missing PDFs
Some PDFs might fail to download. The scraper continues and reports errors. You can:
1. Check the error messages in the output
2. Manually retry failed downloads later
3. The scraper will skip already downloaded PDFs

## Data Format

### JSON Results
Each JSON file contains:
```json
{
  "content": [...],           // Array of results
  "totalElements": 5000,      // Total number of results
  "totalPages": 50,           // Total number of pages
  "size": 30,                 // Page size
  "number": 0                 // Current page number
}
```

### PDF Files
PDF files are binary and contain the certificate document for each person.

## Notes

- The scraper respects the 10000 results limit per UF+municipality combination
- Files are organized to avoid duplicates
- The scraper can be safely interrupted and resumed
- All data is saved in `data-raw/` directory (gitignored)

