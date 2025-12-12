"""Test script to check the correct format for numeroProcesso parameter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bnmpy import BNMPAPIClient, load_cookies


def test_numero_processo_formats():
    """Test different formats of numeroProcesso."""
    # Load cookies
    cookies, fingerprint = load_cookies("cookies.json")
    client = BNMPAPIClient(cookies=cookies, fingerprint=fingerprint)
    
    # Example number from CSV
    numero_exemplo = "0001070-63.2015.8.10.0037.01.0001-26"
    
    # Test different formats
    formats = [
        ("Original (first 25 chars)", numero_exemplo[:25]),
        ("Normalized (first 25 chars)", numero_exemplo.replace(".", "").replace("-", "")[:25]),
        ("Normalized full", numero_exemplo.replace(".", "").replace("-", "")),
        ("Original full", numero_exemplo),
    ]
    
    print("Testing different numeroProcesso formats:")
    print(f"Original number: {numero_exemplo}\n")
    
    for desc, numero_processo in formats:
        print(f"Testing: {desc}")
        print(f"  Value: {numero_processo} (length: {len(numero_processo)})")
        
        try:
            response = client.pesquisa_pecas_filter(
                busca_orgao_recursivo=False,
                orgao_expeditor={},
                numero_processo=numero_processo,
                page=0,
                size=10,
            )
            
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                total = data.get("totalElements", 0)
                print(f"  ✓ SUCCESS! Found {total} results")
                if total > 0:
                    print(f"  First result: {data.get('content', [{}])[0].get('nomePessoa', 'N/A')}")
            else:
                print(f"  ✗ FAILED: {response.text[:200]}")
        except Exception as e:
            print(f"  ✗ EXCEPTION: {e}")
        
        print()


if __name__ == "__main__":
    test_numero_processo_formats()

