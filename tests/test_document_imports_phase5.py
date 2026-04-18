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


def test_detects_avive_layout_ignores_initial_zeros_and_classifies_shift():
    db = SessionLocal()
    payload = {
        "pages": [
            {
                "page_number": 1,
                "tables": [
                    {
                        "title": "ABRIL/2026",
                        "headers": ["Cidade", "Estado", "Empresa", "Unidade", "Especialidade", "Profissional", "Data", "Dia", "H1", "H2", "H3", "H4"],
                        "rows": [
                            ["POA", "RS", "Avive", "PA", "Clinico", "Joel Dahne 51 99911-6562", "10/04/2026", "SEX", "00:00", "00:00", "10:00", "22:00"],
                        ],
                    }
                ],
            }
        ]
    }

    doc = normalize_ocr_payload_document(db, payload, "avive.pdf")
    row = doc["rows"][0]
    assert row["source_layout_type"] == "avive_tabular"
    assert row["start_time_raw"] == "10:00"
    assert row["end_time_raw"] == "22:00"
    assert row["shift_kind"] == "intermediate"
    assert row["canonical_name"] == "Joel Soares Dahne"
    db.close()


def test_detects_pa24h_and_splits_multiple_professionals_and_crm():
    db = SessionLocal()
    payload = {
        "pages": [
            {
                "page_number": 1,
                "tables": [
                    {
                        "title": "PA 24H",
                        "headers": ["DATA", "DIA", "PLANTÃO", "CRM", "NOME COMPLETO"],
                        "rows": [["11/04/2026", "SAB", "12H NOITE", "55597 e 42143", "LETICIA E JEAN"]],
                    }
                ],
            }
        ]
    }

    doc = normalize_ocr_payload_document(db, payload, "pa24h.pdf")
    assert len(doc["rows"]) == 2
    assert all(row["source_layout_type"] == "pa24h_block" for row in doc["rows"])
    assert all(row["multiple_professionals_detected"] for row in doc["rows"])
    assert {row["crm_detected"] for row in doc["rows"]} == {"55597", "42143"}
    assert len({row["day_group_id"] for row in doc["rows"]}) == 1
    db.close()


def test_name_cleaning_removes_faturamento_and_phone():
    db = SessionLocal()
    payload = {
        "pages": [{"page_number": 1, "tables": [{"title": "ABRIL/2026", "headers": ["Profissional", "Data", "Entrada", "Saída"], "rows": [["Daniel Pires 51 99140-4656 Faturamento", "12/04/2026", "08:00", "20:00"]]}]}]
    }
    doc = normalize_ocr_payload_document(db, payload, "noise.pdf")
    row = doc["rows"][0]
    assert row["professional_name_normalized"] == "Daniel Pires"
    assert row["canonical_name"] == "Daniel Pires"
    db.close()


def test_grouped_day_validation_and_metadata_counts():
    db = SessionLocal()
    payload = {
        "pages": [{"page_number": 1, "tables": [{"title": "ABRIL/2026", "headers": ["DATA", "DIA", "PLANTÃO", "CRM", "NOME COMPLETO"], "rows": [["14/04/2026", "TER", "12H DIA", "", "HELENE E ???"]]}]}]
    }
    doc = normalize_ocr_payload_document(db, payload, "grouped.pdf")
    assert doc["metadata"]["layout_counts"]["pa24h_block"] >= 1
    assert any("CRM ausente" in item for item in doc["rows"][0]["grouped_day_validation"])
    db.close()


def test_shift_label_fallback_supports_manha_and_tarde():
    db = SessionLocal()
    payload = {
        "pages": [
            {
                "page_number": 1,
                "tables": [
                    {
                        "title": "ABRIL/2026",
                        "headers": ["Profissional", "Data", "Turno"],
                        "rows": [
                            ["Alice Silva", "15/04/2026", "MANHÃ"],
                            ["Bob Santos", "15/04/2026", "TARDE"],
                        ],
                    }
                ],
            }
        ]
    }
    doc = normalize_ocr_payload_document(db, payload, "fallback_labels.pdf")
    assert doc["rows"][0]["start_datetime"] is not None
    assert doc["rows"][0]["end_datetime"] is not None
    assert doc["rows"][1]["start_datetime"] is not None
    assert doc["rows"][1]["end_datetime"] is not None
    db.close()


def test_pa24h_split_rows_have_unique_source_row_index():
    db = SessionLocal()
    payload = {
        "pages": [
            {
                "page_number": 1,
                "tables": [
                    {
                        "title": "PA 24H",
                        "headers": ["DATA", "DIA", "PLANTÃO", "CRM", "NOME COMPLETO"],
                        "rows": [["16/04/2026", "QUI", "12H NOITE", "55597 e 42143", "LETICIA E JEAN"]],
                    }
                ],
            }
        ]
    }
    doc = normalize_ocr_payload_document(db, payload, "split_index.pdf")
    indexes = [row["source_row_index"] for row in doc["rows"]]
    assert len(indexes) == len(set(indexes))
    db.close()


def test_apply_to_staging_respects_preview_edits(client, admin_headers):
    payload = {
        "pages": [
            {
                "page_number": 1,
                "tables": [
                    {
                        "title": "ABRIL/2026",
                        "headers": ["Profissional", "Data", "Entrada", "Saída"],
                        "rows": [["Alice Silva", "18/04/2026", "08:00", "20:00"]],
                    }
                ],
            }
        ]
    }
    parse_resp = client.post(
        "/admin/imports/parse-ocr-payload",
        headers=admin_headers,
        json={"source_filename": "edited_preview.json", "payload": payload},
    )
    assert parse_resp.status_code == 201
    import_id = parse_resp.json()["document_import_id"]

    preview_resp = client.get(f"/admin/imports/{import_id}/normalized-preview", headers=admin_headers)
    row_index = preview_resp.json()["rows"][0]["source_row_index"]

    staging_resp = client.post(
        f"/admin/imports/{import_id}/apply-to-staging",
        headers=admin_headers,
        json={
            "edited_rows": [
                {
                    "source_row_index": row_index,
                    "professional_name_raw": "Alice Silva Corrigida",
                    "start_time_raw": "10:00",
                    "end_time_raw": "22:00",
                }
            ]
        },
    )
    assert staging_resp.status_code == 200
    schedule_import_id = staging_resp.json()["schedule_import_id"]
    rows_resp = client.get(f"/schedule-imports/{schedule_import_id}/rows", headers=admin_headers)
    assert rows_resp.status_code == 200
    imported_row = rows_resp.json()[0]
    assert imported_row["raw_professional"] == "Alice Silva Corrigida"
    assert imported_row["raw_start_time"] == "10:00"
    assert imported_row["raw_end_time"] == "22:00"


def test_apply_to_staging_uses_source_row_key_to_avoid_cross_page_collisions(client, admin_headers):
    payload = {
        "pages": [
            {
                "page_number": 1,
                "tables": [
                    {
                        "title": "ABRIL/2026",
                        "headers": ["Profissional", "Data", "Entrada", "Saída"],
                        "rows": [["Alice P1", "19/04/2026", "08:00", "20:00"]],
                    }
                ],
            },
            {
                "page_number": 2,
                "tables": [
                    {
                        "title": "ABRIL/2026",
                        "headers": ["Profissional", "Data", "Entrada", "Saída"],
                        "rows": [["Alice P2", "19/04/2026", "08:00", "20:00"]],
                    }
                ],
            },
        ]
    }
    parse_resp = client.post(
        "/admin/imports/parse-ocr-payload",
        headers=admin_headers,
        json={"source_filename": "multi_page_same_index.json", "payload": payload},
    )
    assert parse_resp.status_code == 201
    import_id = parse_resp.json()["document_import_id"]

    preview_resp = client.get(f"/admin/imports/{import_id}/normalized-preview", headers=admin_headers)
    rows = preview_resp.json()["rows"]
    assert len(rows) == 2
    assert rows[0]["source_row_index"] == rows[1]["source_row_index"]
    assert rows[0]["source_page"] != rows[1]["source_page"]

    target_row = next((row for row in rows if row["source_page"] == 2), rows[1])
    source_sheet = target_row.get("source_sheet") or "no-sheet"
    source_page = target_row.get("source_page") or "no-page"
    source_table = target_row.get("source_table_index") or "no-table"
    source_row_key = f"{source_sheet}::{source_page}::{source_table}::{target_row['source_row_index']}"

    staging_resp = client.post(
        f"/admin/imports/{import_id}/apply-to-staging",
        headers=admin_headers,
        json={
            "edited_rows": [
                {
                    "source_row_index": target_row["source_row_index"],
                    "source_row_key": source_row_key,
                    "professional_name_raw": "Alice P2 Corrigida",
                }
            ]
        },
    )
    assert staging_resp.status_code == 200
    schedule_import_id = staging_resp.json()["schedule_import_id"]
    rows_resp = client.get(f"/schedule-imports/{schedule_import_id}/rows", headers=admin_headers)
    assert rows_resp.status_code == 200
    imported_names = {row["raw_professional"] for row in rows_resp.json()}
    assert "Alice P2 Corrigida" in imported_names
    assert "Alice P1" in imported_names
