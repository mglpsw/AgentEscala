from backend.services import import_service
from backend.services.import_service import _extract_text_from_ocr_payload, _parse_ocr_text_to_rows


def test_parse_ocr_text_to_rows_extracts_structured_fields():
    text = "Alice Silva 01/04/2026 08:00 20:00\nLinha sem data clara"
    headers, rows, errors = _parse_ocr_text_to_rows(text)

    assert headers[:4] == ["profissional", "data", "hora_inicio", "hora_fim"]
    assert rows[0]["profissional"] is not None
    assert rows[0]["data"] == "01/04/2026"
    assert rows[0]["hora_inicio"] == "08:00"
    assert rows[0]["hora_fim"] == "20:00"
    assert errors


def test_validate_import_endpoint_revalidates_staging(client, admin_headers):
    csv_content = (
        "profissional,data,hora_inicio,hora_fim,observacoes\n"
        "Alice Silva,01/04/2026,08:00,20:00,ok\n"
    )

    upload_response = client.post(
        "/schedule-imports/",
        headers=admin_headers,
        files={"file": ("escala.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert upload_response.status_code == 201
    import_id = upload_response.json()["import_id"]

    validate_response = client.post(f"/schedule-imports/{import_id}/validate", headers=admin_headers)
    assert validate_response.status_code == 200
    payload = validate_response.json()
    assert payload["import_id"] == import_id
    assert payload["total_rows"] == 1

    rows_response = client.get(f"/schedule-imports/{import_id}/rows", headers=admin_headers)
    assert rows_response.status_code == 200
    row = rows_response.json()[0]
    assert "confidence_score" in row
    assert "parse_status" in row
    assert "match_status" in row
    assert "validation_status" in row


def test_extract_text_from_ocr_payload_supports_nested_result():
    payload = {"result": {"lines": ["Alice Silva 01/04/2026 08:00 20:00"]}}
    text = _extract_text_from_ocr_payload(payload)
    assert "Alice Silva" in text


def test_read_ocr_via_api_uses_response_payload(monkeypatch):
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

    monkeypatch.setattr(import_service.httpx, "Client", lambda **_kwargs: _FakeClient())
    headers, rows, meta = import_service._read_ocr_via_api(b"pdf", "escala.pdf")

    assert headers[:4] == ["profissional", "data", "hora_inicio", "hora_fim"]
    assert len(rows) == 1
    assert "Alice Silva" in (rows[0]["profissional"] or "")
    assert "source" in meta


def test_read_ocr_via_api_raises_when_payload_has_no_text(monkeypatch):
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

    monkeypatch.setattr(import_service.httpx, "Client", lambda **_kwargs: _FakeClient())

    try:
        import_service._read_ocr_via_api(b"pdf", "escala.pdf")
        assert False, "Era esperado ValueError para payload OCR vazio"
    except ValueError as exc:
        assert "payload sem conteúdo textual" in str(exc)
