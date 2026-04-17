from backend.services.import_service import _parse_ocr_text_to_rows


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
