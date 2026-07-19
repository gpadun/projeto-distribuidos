"""Resolve the current ADM leader URL for HTTP clients."""

import os

import httpx

MAPA_ADM_PADRAO = {
    "adm-1": "http://127.0.0.1:8001",
    "adm-2": "http://127.0.0.1:8002",
    "adm-3": "http://127.0.0.1:8003",
}


def carregar_adm_urls() -> list[str]:
    """Return ADM base URLs used to discover the cluster leader."""
    raw = os.getenv("ADM_URLS", "")
    if raw.strip():
        return [url.strip() for url in raw.split(",") if url.strip()]

    fallback = os.getenv("ADM_URL")
    if fallback:
        return [fallback.strip()]

    return list(MAPA_ADM_PADRAO.values())


def url_do_adm(id_adm: str, adm_urls: list[str] | None = None) -> str | None:
    """Map an ADM id such as adm-2 to its configured base URL."""
    candidatos = adm_urls or carregar_adm_urls()
    for url in candidatos:
        for id_padrao, url_padrao in MAPA_ADM_PADRAO.items():
            if id_adm == id_padrao and url.rstrip("/") == url_padrao.rstrip("/"):
                return url
            if id_adm == id_padrao and url_padrao.rsplit(":", 1)[-1] in url:
                return url
    return MAPA_ADM_PADRAO.get(id_adm)


def resolver_adm_lider_url(
    adm_url: str | None = None,
    adm_urls: list[str] | None = None,
    timeout: float = 2.0,
) -> str:
    """Discover the ADM leader by querying /infra/lider on reachable peers."""
    if adm_url and adm_url.strip():
        return adm_url.strip()

    candidatos = adm_urls or carregar_adm_urls()
    for url in candidatos:
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(f"{url.rstrip('/')}/infra/lider")
                response.raise_for_status()
                lider = response.json()
        except httpx.HTTPError:
            continue

        if lider.get("souLider"):
            return url

        id_lider = lider.get("liderAtual")
        if id_lider:
            url_lider = url_do_adm(id_lider, candidatos)
            if url_lider:
                return url_lider

    if candidatos:
        return candidatos[-1]

    return MAPA_ADM_PADRAO["adm-3"]
