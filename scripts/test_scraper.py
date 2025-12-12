"""Test the scraper with a small dataset."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bnmpy import BNMPAPIClient, load_cookies
from bnmpy.scraper import BNMPScraper


def main():
    """Test scraper with a single UF."""
    print("=" * 60)
    print("BNMP Scraper Test")
    print("=" * 60)

    # Load cookies
    cookies_file = Path("cookies.json")
    if not cookies_file.exists():
        print("[ERROR] cookies.json not found!")
        return 1

    print("[OK] Loading cookies...")
    cookies, fingerprint = load_cookies(cookies_file)

    # Create client
    print("[OK] Creating API client...")
    client = BNMPAPIClient(cookies=cookies, fingerprint=fingerprint)

    # Test API endpoints
    print("\nTesting API endpoints...")

    # Test get_estados
    print("\n1. Testing get_estados()...")
    try:
        response = client.get_estados()
        if response.status_code == 200:
            estados = response.json()
            print(f"   [OK] Found {len(estados)} states")
            if estados:
                first_uf = estados[0]
                print(f"   Example: {first_uf.get('nome', 'N/A')} (ID: {first_uf.get('id')})")
        else:
            print(f"   [ERROR] Status {response.status_code}")
            return 1
    except Exception as e:
        print(f"   [ERROR] {e}")
        return 1

    # Test get_municipios
    print("\n2. Testing get_municipios_por_uf()...")
    try:
        # Use first UF ID
        uf_id = estados[0].get("id")
        response = client.get_municipios_por_uf(uf_id)
        if response.status_code == 200:
            municipios = response.json()
            print(f"   [OK] Found {len(municipios)} municipalities for UF {uf_id}")
            if municipios:
                first_municipio = municipios[0]
                print(f"   Example: {first_municipio.get('nome', 'N/A')} (ID: {first_municipio.get('id')})")
        else:
            print(f"   [ERROR] Status {response.status_code}")
            return 1
    except Exception as e:
        print(f"   [ERROR] {e}")
        return 1

    # Test pesquisa_pecas_filter
    print("\n3. Testing pesquisa_pecas_filter()...")
    try:
        response = client.pesquisa_pecas_filter(
            busca_orgao_recursivo=False,
            orgao_expeditor={},
            id_estado=uf_id,
            page=0,
            size=10,
        )
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", [])
            print(f"   [OK] Found {len(content)} results (total: {data.get('totalElements', 0)})")
            if content:
                first_result = content[0]
                certidao_id = first_result.get("id") or first_result.get("idCertidao")
                print(f"   Example: Result ID {certidao_id} (field: 'id')")
        else:
            print(f"   [ERROR] Status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return 1
    except Exception as e:
        print(f"   [ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Test scraper with small dataset
    print("\n" + "=" * 60)
    print("Testing scraper with small dataset...")
    print("=" * 60)

    scraper = BNMPScraper(
        client=client,
        data_dir="data-raw-test",
        page_size=10,  # Small page size for testing
        max_results_per_combination=50,  # Limit for testing
        delay_between_requests=0.5,
    )

    # Save estados metadata
    print(f"\nSaving estados metadata...")
    scraper.save_json(
        {"estados": estados, "total": len(estados)},
        "metadata/estados.json",
    )
    print(f"[OK] Metadata saved")

    print(f"\nTesting download_filter_results for UF {uf_id}...")
    results = scraper.download_filter_results(
        uf_id=uf_id,
        municipio_id=None,
        uf_name=estados[0].get("nome", f"UF_{uf_id}"),
        municipio_name="",
    )

    print(f"\n[OK] Downloaded {len(results)} results")
    
    # Test PDF download if we have results
    if results:
        first_result = results[0]
        # The API returns 'id' and 'idTipoPeca' fields
        certidao_id = first_result.get("id")
        id_tipo_peca = first_result.get("idTipoPeca")
        
        if certidao_id and id_tipo_peca:
            print(f"\nTesting PDF download for certidao {certidao_id} (tipo: {id_tipo_peca})...")
            success = scraper.download_pdf_for_person(certidao_id, id_tipo_peca, uf_id)
            if success:
                print(f"[OK] PDF downloaded successfully")
            else:
                print(f"[WARN] PDF download failed or already exists")
        else:
            print(f"\n[WARN] Missing required fields in first result")
            print(f"  id: {certidao_id}, idTipoPeca: {id_tipo_peca}")
            print(f"  Available fields: {list(first_result.keys())}")
    else:
        print(f"\n[WARN] No results to test PDF download")
    
    print(f"\n[OK] Test complete! Check data-raw-test/ directory")

    print("\n" + "=" * 60)
    print("[SUCCESS] All tests passed!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

