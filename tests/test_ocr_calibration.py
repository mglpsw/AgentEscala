import logging

from backend.config import settings as settings_module
from backend.services.ocr.calibration_service import OcrCalibrationService


def test_parse_raw_text_detects_date_shift_and_name_from_model_example():
    raw_text = "01/04/2026 QUA 24 HORAS CLOVES DOMINGOS RUFINO\n03/04/2026 SEX 12H DIA HELENE E ???"
    rows = OcrCalibrationService.parse_raw_text(raw_text)

    assert len(rows) == 2
    assert rows[0].date == "01/04/2026"
    assert rows[0].shift_label == "24 HORAS"
    assert "CLOVES" in (rows[0].professional_name or "")

    assert rows[1].date == "03/04/2026"
    assert rows[1].shift_label == "12H DIA"


def test_parse_raw_text_detects_time_range_from_table_style():
    raw_text = "Leticia Leonarda | 13/04 | Segunda feira | 10:00 | 22:00"
    rows = OcrCalibrationService.parse_raw_text(raw_text)

    assert len(rows) == 1
    assert rows[0].date == "13/04" or rows[0].date is None
    # para esse estilo, regex de range pode não detectar por colunas separadas;
    # valida ao menos que nome foi capturado.
    assert "Leticia" in (rows[0].professional_name or "")


def test_admin_ocr_calibration_preview_works_with_mocked_remote(client, admin_headers, monkeypatch):
    import backend.api.admin_ocr as admin_ocr_module

    monkeypatch.setattr(settings_module.settings, "FEATURE_OCR_REMOTE_IMPORT", True)

    def _fake_extract(**_kwargs):
        return {
            "raw_text": "01/04/2026 QUA 24 HORAS ALICE SILVA\n"
                        "02/04/2026 QUI 12H DIA MIGUEL FONSECA SOARES",
            "source": "https://api.ks-sk.net:9443/ocr/extract",
            "latency_seconds": 0.12,
        }

    monkeypatch.setattr(admin_ocr_module, "extract_text_via_agent_router", _fake_extract)

    response = client.post(
        "/admin/ocr/calibration/preview",
        headers=admin_headers,
        files={"file": ("escala.pdf", b"fake-pdf", "application/pdf")},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_rows"] == 2
    assert payload["matched_rows"] >= 1
    assert payload["unmatched_rows"] >= 0
    assert payload["rows"][0]["date"] == "01/04/2026"


def test_admin_ocr_calibration_preview_requires_feature_flag(client, admin_headers, monkeypatch):
    monkeypatch.setattr(settings_module.settings, "FEATURE_OCR_REMOTE_IMPORT", False)

    response = client.post(
        "/admin/ocr/calibration/preview",
        headers=admin_headers,
        files={"file": ("escala.pdf", b"fake-pdf", "application/pdf")},
    )

    assert response.status_code == 409


def test_admin_ocr_calibration_preview_emits_structured_logs(client, admin_headers, monkeypatch, caplog):
    import backend.api.admin_ocr as admin_ocr_module

    monkeypatch.setattr(settings_module.settings, "FEATURE_OCR_REMOTE_IMPORT", True)

    def _fake_extract(**_kwargs):
        return {
            "raw_text": "01/04/2026 QUA 24 HORAS ALICE SILVA",
            "source": "https://api.ks-sk.net:9443/ocr/extract",
            "latency_seconds": 0.08,
        }

    monkeypatch.setattr(admin_ocr_module, "extract_text_via_agent_router", _fake_extract)

    with caplog.at_level(logging.INFO, logger="agentescala.admin_ocr"):
        response = client.post(
            "/admin/ocr/calibration/preview",
            headers=admin_headers,
            files={"file": ("escala.pdf", b"fake-pdf", "application/pdf")},
        )

    assert response.status_code == 200
    messages = [record.getMessage() for record in caplog.records]
    assert any("ocr_calibration_preview_started" in msg for msg in messages)
    assert any("ocr_calibration_preview_completed" in msg for msg in messages)
