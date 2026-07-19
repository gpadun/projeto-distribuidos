"""Tests for ADM leader URL resolution."""

import httpx

from src.infra.adm_lider import resolver_adm_lider_url, url_do_adm


def test_url_do_adm_mapeia_portas_padrao():
    urls = [
        "http://127.0.0.1:8001",
        "http://127.0.0.1:8002",
        "http://127.0.0.1:8003",
    ]

    assert url_do_adm("adm-2", urls) == "http://127.0.0.1:8002"


def test_resolver_adm_lider_url_usa_url_explicita():
    assert resolver_adm_lider_url("http://127.0.0.1:8002") == "http://127.0.0.1:8002"


def test_resolver_adm_lider_url_descobre_lider(monkeypatch):
    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, timeout):
            del timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url):
            if url.endswith(":8001/infra/lider"):
                return FakeResponse({"souLider": False, "liderAtual": "adm-2"})
            if url.endswith(":8002/infra/lider"):
                return FakeResponse({"souLider": True, "liderAtual": "adm-2"})
            raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "Client", FakeClient)

    url = resolver_adm_lider_url(
        adm_urls=["http://127.0.0.1:8001", "http://127.0.0.1:8002", "http://127.0.0.1:8003"],
    )

    assert url == "http://127.0.0.1:8002"
