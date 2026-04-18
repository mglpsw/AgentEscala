from backend.services.document_normalization_service import _parse_date_with_context, normalize_ocr_payload_document
from backend.config.database import SessionLocal


def _sample_payload():
    return {
        "pages": [
            {
                "page_number": 1,
                "tables": [
                    {
                        "title": "MARÇO/2026",
                        "headers": ["Profissional", "Data", "Entrada", "Saída", "Total de Horas"],
                        "rows": [
                            ["Mariana Koppe Pereira 11999998888", "01/03/2026", "08:00", "20:00", "12"],
                            ["Carlos Silva Faturamento", "01/03/2026", "20:00", "08:00", "12"],
                        ],
                        "confidence": 0.93,
                    }
                ],
            }
        ]
    }


def test_normalize_ocr_payload_handles_noise_and_overnight():
    db = SessionLocal()
    doc = normalize_ocr_payload_document(db, _sample_payload(), "escala.pdf")

    assert doc["source_type"] == "pdf"
    assert doc["detected_months"][0]["month"] == 3
    assert len(doc["rows"]) == 2

    first = doc["rows"][0]
    assert first["professional_name_normalized"] == "Mariana Koppe Pereira"
    assert first["match_status"] in {"new_user_candidate", "matched", "ambiguous"}

    second = doc["rows"][1]
    assert second["professional_name_normalized"] == "Carlos Silva"
    assert second["end_datetime"] > second["start_datetime"]
    assert second["duration_hours"] == 12.0
    db.close()


def test_admin_document_import_endpoints_flow(client, admin_headers):
    parse_resp = client.post(
        "/admin/imports/parse-ocr-payload",
        headers=admin_headers,
        json={"source_filename": "escala_marco.json", "payload": _sample_payload()},
    )
    assert parse_resp.status_code == 201
    parsed = parse_resp.json()
    assert parsed["total_rows"] == 2
    assert parsed["document_import_id"]

    import_id = parsed["document_import_id"]
    preview_resp = client.get(f"/admin/imports/{import_id}/normalized-preview", headers=admin_headers)
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["source_filename"] == "escala_marco.json"
    assert len(preview["rows"]) == 2

    staging_resp = client.post(f"/admin/imports/{import_id}/apply-to-staging", headers=admin_headers)
    assert staging_resp.status_code == 200
    staging = staging_resp.json()
    assert staging["schedule_import_id"] > 0

    confirm_resp = client.post(f"/admin/imports/{import_id}/confirm", headers=admin_headers)
    assert confirm_resp.status_code == 200
    confirmed = confirm_resp.json()
    assert confirmed["created_shifts"] >= 0


def test_parse_date_with_context_handles_excel_datetime_text():
    parsed = _parse_date_with_context("2026-03-01 00:00:00", None, None)
    assert parsed is not None
    assert parsed.isoformat() == "2026-03-01"


def test_create_missing_users_empty_selection_is_noop(client, admin_headers):
    parse_resp = client.post(
        "/admin/imports/parse-ocr-payload",
        headers=admin_headers,
        json={
            "source_filename": "new_user.json",
            "payload": {
                "pages": [
                    {
                        "page_number": 1,
                        "tables": [
                            {
                                "title": "ABRIL/2026",
                                "headers": ["Profissional", "Data", "Entrada", "Saída"],
                                "rows": [["Novo Médico Teste", "01/04/2026", "08:00", "20:00"]],
                            }
                        ],
                    }
                ]
            },
        },
    )
    assert parse_resp.status_code == 201
    import_id = parse_resp.json()["document_import_id"]

    create_resp = client.post(
        f"/admin/imports/{import_id}/create-missing-users",
        headers=admin_headers,
        json={"create_for_row_indexes": []},
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["created_user_ids"] == []


def test_document_confirm_returns_409_on_repeat(client, admin_headers):
    parse_resp = client.post(
        "/admin/imports/parse-ocr-payload",
        headers=admin_headers,
        json={"source_filename": "escala_marco.json", "payload": _sample_payload()},
    )
    import_id = parse_resp.json()["document_import_id"]
    client.post(f"/admin/imports/{import_id}/apply-to-staging", headers=admin_headers)
    first = client.post(f"/admin/imports/{import_id}/confirm", headers=admin_headers)
    assert first.status_code == 200
    second = client.post(f"/admin/imports/{import_id}/confirm", headers=admin_headers)
    assert second.status_code == 409


def test_apply_to_staging_uses_inferred_times(client, admin_headers):
    payload = {
        "pages": [
            {
                "page_number": 1,
                "tables": [
                    {
                        "title": "ABRIL/2026",
                        "headers": ["Profissional", "Data", "Turno"],
                        "rows": [["Alice Silva", "07/04/2026", "20:00-08:00"]],
                    }
                ],
            }
        ]
    }
    parse_resp = client.post(
        "/admin/imports/parse-ocr-payload",
        headers=admin_headers,
        json={"source_filename": "infer_time.json", "payload": payload},
    )
    assert parse_resp.status_code == 201
    import_id = parse_resp.json()["document_import_id"]
    staging_resp = client.post(f"/admin/imports/{import_id}/apply-to-staging", headers=admin_headers)
    assert staging_resp.status_code == 200
    assert staging_resp.json()["invalid_rows"] == 0
