# BNMP Scraper Usage Guide

## Overview

The BNMP scraper downloads all data from the BNMP portal using two methods:

**Primary Method (Recommended):** CSV-based scraping
1. Downloads CSV files for each UF (state) from the portal
2. Merges all CSVs into a single file with UF identification
3. Downloads JSONs and PDFs for each case in the merged CSV

**Alternative Method:** Direct API scraping
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

## Quick Start (Primary Method - CSV-based)

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

### 2. Download CSV Files for Each UF

Download CSV files for all UFs and merge them:

```bash
python scripts/download_csvs.py
```

This will:
- Download CSV files for each UF from the portal
- Save individual CSVs in `data-raw/csvs/uf_{id}_{sigla}.csv`
- Merge all CSVs into `data-raw/csvs_merged.csv` with `uf_id` and `uf_sigla` columns
- Skip already downloaded files (resume capability)

**Options:**
```bash
python scripts/download_csvs.py \
  --cookies-file cookies.json \
  --data-dir data-raw \
  --delay 0.5 \
  --start-uf 26  # Resume from a specific UF
```

### 3. Download JSONs and PDFs from Merged CSV

Once you have the merged CSV file, download JSONs and PDFs for each case:

```bash
python scripts/run_scraper_csv.py
```

This will:
- Read the merged CSV file (`data-raw/csvs_merged.csv`)
- For each case, download JSON with search results
- Download PDFs for each result in the JSON
- Save JSONs in `data-raw/json_ids/<caseid>.json`
- Save PDFs in `data-raw/pdfs/certidao_<id>_tipo_<idTipo>.pdf`
- Skip already downloaded files (resume capability)

**Options:**
```bash
python scripts/run_scraper_csv.py \
  --cookies-file cookies.json \
  --csv-file data-raw/csvs_merged.csv \
  --data-dir data-raw \
  --delay 0.5 \
  --workers 5 \  # Use 5 parallel workers
  --start-row 0 \  # Resume from a specific row
  --max-rows 100  # Limit to first 100 rows (for testing)
```

## Building the Merged CSV File

The merged CSV file is created automatically by `download_csvs.py`, but here's how it works:

### Step 1: Download Individual CSV Files

The script downloads CSV files for each UF using the portal's CSV export endpoint:

```bash
python scripts/download_csvs.py
```

**What happens:**
- For each UF, makes a POST request to `/bnmpportal/api/pesquisa-pecas/csv`
- Saves each CSV as `data-raw/csvs/uf_{id}_{sigla}.csv`
- Each CSV contains all cases for that UF

### Step 2: Merge All CSVs

After downloading all individual CSVs, the script automatically merges them:

- Reads all CSV files from `data-raw/csvs/`
- Adds `uf_id` and `uf_sigla` columns to each row
- Combines all rows into a single CSV file
- Saves as `data-raw/csvs_merged.csv`

**CSV Format:**
```csv
uf_id,uf_sigla,Número,Nome,Alcunha,Nome da Mãe,Nome do Pai,Data de Nascimento,Situação,Data,Órgão Expedidor,Peça
10,MA,0001070-63.2015.8.10.0037.01.0001-26,ADRIEL SILVA,NÃO CONSTA,NÃO CONSTA,NÃO CONSTA, ,Pendente de Cumprimento,09/05/2023,2ª VARA DE GRAJAÚ,Mandado de Prisão
...
```

### Manual Merge (if needed)

If you need to manually merge CSVs or re-merge:

```bash
python scripts/download_csvs.py --skip-merge  # Only download, don't merge
# Then later:
python scripts/download_csvs.py  # Will merge existing CSVs
```

Or use the merge functionality directly by running without `--skip-merge` (it will skip downloads if files exist and just merge).

## Directory Structure

The scraper creates the following structure:

```
data-raw/
├── csvs/                              # Individual CSV files per UF
│   ├── uf_1_AC.csv
│   ├── uf_2_AL.csv
│   └── ...
├── csvs_merged.csv                   # Merged CSV with all cases
├── json_ids/                         # JSON files per case
│   ├── 0001070632015810003701000126.json
│   └── ...
├── pdfs/                             # PDF certificates
│   ├── certidao_192556728_tipo_10.pdf
│   └── ...
├── json/                             # JSON files (alternative method)
│   ├── uf_2_page_0_size_100.json
│   └── ...
└── metadata/                         # Metadata files
    ├── estados.json                  # List of all states
    └── municipios_uf_2.json         # Municipalities for each UF
```

## File Naming Convention

### CSV Files
- `uf_{uf_id}_{uf_sigla}.csv` - Individual CSV for each UF
- `csvs_merged.csv` - Merged CSV with all cases and UF identification

### JSON Files (CSV Method)
- `<caseid>.json` - JSON file for each case (caseid is normalized number without dots/dashes)

### JSON Files (Alternative Method)
- `uf_{uf_id}_page_{page}_size_{size}.json` - Results for a UF
- `uf_{uf_id}_municipio_{municipio_id}_page_{page}_size_{size}.json` - Results for UF+municipality

### PDF Files
- `certidao_{certidao_id}_tipo_{id_tipo_peca}.pdf` - Certificate PDF

This naming ensures:
- No duplicate downloads
- Easy to resume if interrupted
- Clear organization by UF and case

## Command Line Options

### CSV Download Script (`download_csvs.py`)

```bash
python scripts/download_csvs.py [OPTIONS]
```

Options:
- `--cookies-file PATH` - Path to cookies file (default: cookies.json)
- `--data-dir PATH` - Directory to save data (default: data-raw)
- `--csv-dir PATH` - Directory to save individual CSV files (default: data-dir/csvs)
- `--output-file PATH` - Path to save merged CSV (default: data-dir/csvs_merged.csv)
- `--delay SECONDS` - Delay between requests (default: 0.5)
- `--start-uf ID` - UF ID to start from (for resuming)
- `--skip-merge` - Skip merging step, only download CSVs

### CSV Scraper Script (`run_scraper_csv.py`)

```bash
python scripts/run_scraper_csv.py [OPTIONS]
```

Options:
- `--cookies-file PATH` - Path to cookies file (default: cookies.json)
- `--csv-file PATH` - Path to merged CSV file (default: data-raw/csvs_merged.csv)
- `--data-dir PATH` - Directory to save data (default: data-raw)
- `--delay SECONDS` - Delay between requests (default: 0.5)
- `--workers N` - Number of parallel workers for downloads (default: 1 = sequential)
- `--start-row N` - Row number to start from (for resuming, default: 0)
- `--max-rows N` - Maximum number of rows to process (default: all)

## Optimization Tips

### Parallel Processing

Use multiple workers to speed up downloads:

```bash
# Sequential (default)
python scripts/run_scraper_csv.py

# Parallel with 5 workers
python scripts/run_scraper_csv.py --workers 5

# Parallel with 10 workers (faster but uses more session time)
python scripts/run_scraper_csv.py --workers 10 --delay 0.2
```

**Note:** Parallel downloads are much faster but use more of your session time. Use with caution to avoid exhausting your authentication session too quickly.

### Delay Between Requests

Adjust delay to avoid rate limiting:
- Default: 0.5 seconds
- Increase if getting blocked: `--delay 1.0`
- Decrease for faster scraping: `--delay 0.2` (risky)

### Resuming

Both scripts support resuming:

```bash
# Resume CSV download from a specific UF
python scripts/download_csvs.py --start-uf 26

# Resume PDF/JSON download from a specific row
python scripts/run_scraper_csv.py --start-row 1000
```

## Alternative Method: Direct API Scraping

If you prefer to scrape directly from the API without using CSV files:

```bash
python scripts/run_scraper.py
```

This method:
- Iterates through all UFs and municipalities
- Downloads JSON files with filter results
- Downloads PDF files for each person
- Respects the 10000 results limit per UF+municipality combination

**Options:**
```bash
python scripts/run_scraper.py \
  --cookies-file cookies.json \
  --data-dir data-raw \
  --page-size 30 \
  --max-results 10000 \
  --delay 0.5 \
  --workers 5 \
  --start-uf 2 \
  --start-municipio 123
```

See the [Alternative Method Documentation](#alternative-method-details) section below for more details.

## Monitoring Progress

The scraper prints progress information:
- Current case/row being processed
- JSON download status
- PDF download progress
- Error messages if any

Example output:
```
[1/307621] Processing case: 0001070-63.2015.8.10.0037.01.0001-26
  Process number (first 20 digits): 00010706320158100037
  Case ID: 0001070632015810003701000126
  [OK] JSON downloaded: 0001070632015810003701000126.json
  Found 1 results in JSON
    Downloading PDF 1/1: ADRIEL SILVA (ID: 194830524)
      [OK] PDF downloaded: certidao_194830524_tipo_10.pdf

[PROGRESS] Completed 10/307621 cases
```

## Troubleshooting

### Authentication Errors
If you get 401 errors:
1. Check if cookies are expired: `python scripts/test_authentication.py`
2. Get fresh session: Run the captcha solving step again

### Rate Limiting
If requests are being blocked:
1. Increase delay: `--delay 1.0` or higher
2. Reduce number of workers: `--workers 1`
3. Wait and resume later

### Missing PDFs
Some PDFs might fail to download. The scraper continues and reports errors. You can:
1. Check the error messages in the output
2. Manually retry failed downloads later
3. The scraper will skip already downloaded PDFs

### CSV Merge Errors
If CSV merge fails due to malformed files:
- The script uses pandas with error handling to skip bad lines
- Check individual CSV files if merge consistently fails
- Re-download problematic CSVs: `python scripts/download_csvs.py --start-uf X`

## Data Format

### Merged CSV
The merged CSV contains all cases with UF identification:
- `uf_id`: State ID
- `uf_sigla`: State abbreviation (e.g., "SP", "RJ")
- `Número`: Case number (full format)
- `Nome`: Person name
- Other columns from the original CSV

### JSON Files (CSV Method)
Each JSON file contains search results for a specific case:
```json
{
  "content": [...],           // Array of results for this case
  "totalElements": 1,         // Total number of results
  "totalPages": 1,           // Total number of pages
  "size": 10,                // Page size
  "number": 0                // Current page number
}
```

### JSON Files (Alternative Method)
Each JSON file contains paginated results:
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

- The CSV method is recommended as it's faster and more reliable
- Files are organized to avoid duplicates
- The scraper can be safely interrupted and resumed
- All data is saved in `data-raw/` directory (gitignored)
- The CSV method processes cases sequentially by default, but supports parallel processing with `--workers`

---

## Alternative Method Details

### Direct API Scraping (`run_scraper.py`)

This method scrapes directly from the API without using CSV files. It's useful if you need more control over the scraping process or want to scrape specific UFs/municipalities.

**Command Line Options:**

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

### Programmatic Usage

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

### Skip Small UFs
For UFs with < 10000 results, the scraper skips municipality iteration by default. To disable:

```bash
python scripts/run_scraper.py --no-skip-small
```
