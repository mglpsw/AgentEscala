from backend.services.ocr.agent_router_client import OcrAgentRouterError, extract_text_via_agent_router


def test_extract_text_via_agent_router_reads_nested_data(monkeypatch):
    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"raw_text": "Alice Silva 01/04/2026 08:00 20:00"}}

    class _FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *_args, **_kwargs):
            return _FakeResponse()

    import backend.services.ocr.agent_router_client as client_mod

    monkeypatch.setattr(client_mod.httpx, "Client", lambda **_kwargs: _FakeClient())
    result = extract_text_via_agent_router(
        file_content=b"pdf",
        filename="escala.pdf",
        base_url="https://api.ks-sk.net:9443",
        timeout_seconds=10,
        verify_ssl=True,
    )

    assert "Alice Silva" in result["raw_text"]
    assert result["source"].startswith("https://api.ks-sk.net:9443")


def test_extract_text_via_agent_router_raises_on_empty_payload(monkeypatch):
    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"result": {"unexpected": "shape"}}

    class _FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *_args, **_kwargs):
            return _FakeResponse()

    import backend.services.ocr.agent_router_client as client_mod

    monkeypatch.setattr(client_mod.httpx, "Client", lambda **_kwargs: _FakeClient())

    try:
        extract_text_via_agent_router(
            file_content=b"img",
            filename="escala.jpeg",
            base_url="https://api.ks-sk.net:9443",
            timeout_seconds=10,
            verify_ssl=True,
        )
        assert False, "Era esperado OcrAgentRouterError"
    except OcrAgentRouterError as exc:
        assert "payload sem texto" in str(exc)


def test_extract_text_via_agent_router_falls_back_to_analyze_endpoint(monkeypatch):
    class _FakeResponse:
        def __init__(self, *, should_fail: bool):
            self._should_fail = should_fail

        def raise_for_status(self):
            if self._should_fail:
                raise ValueError("endpoint unavailable")
            return None

        def json(self):
            return {"text": "Alice Silva 01/04/2026 08:00 20:00"}

    class _FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, *_args, **_kwargs):
            calls.append(url)
            return _FakeResponse(should_fail=url.endswith("/ocr/extract"))

    import backend.services.ocr.agent_router_client as client_mod

    calls = []
    monkeypatch.setattr(client_mod.httpx, "Client", lambda **_kwargs: _FakeClient())
    result = extract_text_via_agent_router(
        file_content=b"img",
        filename="escala.jpeg",
        base_url="http://192.168.3.155:8010",
        timeout_seconds=10,
        verify_ssl=False,
    )

    assert calls[0].endswith("/ocr/extract")
    assert calls[1].endswith("/ocr/analyze")
    assert result["source"].endswith("/ocr/analyze")
