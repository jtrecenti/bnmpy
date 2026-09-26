"""Smoke test of the BNMP API using a JWT token obtained after solving the captcha.

The token is the value of the ``portalbnmp`` cookie (or the ``Authorization``
header returned by ``POST /api/recaptcha``). It expires about 5 minutes after
being issued, so run this right after getting it.

Usage:
    uv run python scripts/smoke_test_token.py <token>
"""

import sys
import time

from bnmpy import BNMPAPIClient
from bnmpy.api_client import token_expiration


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    token = sys.argv[1]
    exp = token_expiration(token)
    if exp is not None:
        print(f"Token expires in {exp - time.time():.0f}s")

    client = BNMPAPIClient(token=token)
    ok = True

    def step(name, fn):
        nonlocal ok
        t0 = time.perf_counter()
        r = fn()
        dt = time.perf_counter() - t0
        print(f"[{r.status_code}] {name} ({dt:.2f}s, {len(r.content)} bytes)")
        if r.status_code != 200:
            print("    ", r.text[:300])
            ok = False
        return r

    r = step("estados", client.get_estados)
    if r.status_code != 200:
        return 1
    estados = r.json()
    uf = next(e for e in estados if e.get("sigla") == "AC")

    step(f"municipios {uf['sigla']}", lambda: client.get_municipios_por_uf(uf["id"]))
    r = step(
        f"filter {uf['sigla']}",
        lambda: client.pesquisa_pecas_filter(id_estado=uf["id"], page=0, size=10),
    )
    if r.status_code == 200:
        data = r.json()
        print(f"     totalElements={data.get('totalElements')}")
        content = data.get("content") or []
        if content:
            first = content[0]
            print(f"     first keys: {sorted(first.keys())}")
            step(
                "pdf certidao",
                lambda: client.download_pdf(first["id"], first["idTipoPeca"]),
            )
    step(f"csv {uf['sigla']}", lambda: client.download_csv(id_estado=uf["id"]))

    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
