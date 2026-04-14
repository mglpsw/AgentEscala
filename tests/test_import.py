"""Testes para importação de escala base.

Cobre:
- parsing de turno diurno padrão
- parsing de turno noturno com virada de dia
- parsing de exceções reais de horário
- detecção de sobreposição intra-lote
- importação de arquivo com linhas mistas (válidas e inválidas)
- endpoints protegidos exigindo autenticação e papel admin
- fluxo completo: upload → summary → confirm → verificar shifts criados
"""
from __future__ import annotations

import io
import json
from datetime import date, time
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


# ─── Testes unitários do serviço ──────────────────────────────────────────────

class TestParseDate:
    def test_br_format(self):
        from backend.services.import_service import _parse_date
        assert _parse_date("01/03/2026") == date(2026, 3, 1)

    def test_iso_format(self):
        from backend.services.import_service import _parse_date
        assert _parse_date("2026-03-01") == date(2026, 3, 1)

    def test_invalid_returns_none(self):
        from backend.services.import_service import _parse_date
        assert _parse_date("não-é-data") is None
        assert _parse_date(None) is None
        assert _parse_date("") is None


class TestParseTime:
    def test_hhmm(self):
        from backend.services.import_service import _parse_time
        assert _parse_time("08:00") == time(8, 0)
        assert _parse_time("20:00") == time(20, 0)

    def test_hhmmss(self):
        from backend.services.import_service import _parse_time
        assert _parse_time("08:00:00") == time(8, 0, 0)

    def test_invalid_returns_none(self):
        from backend.services.import_service import _parse_time
        assert _parse_time("25:00") is None
        assert _parse_time(None) is None


class TestNormalizeShift:
    def test_daytime_standard(self):
        from backend.services.import_service import _normalize_shift
        start, end, dur, overnight, std = _normalize_shift(
            date(2026, 3, 1), time(8, 0), time(20, 0)
        )
        assert overnight is False
        assert std is True
        assert dur == 12 * 60
        assert start.date() == end.date()

    def test_overnight_standard(self):
        from backend.services.import_service import _normalize_shift
        start, end, dur, overnight, std = _normalize_shift(
            date(2026, 3, 1), time(20, 0), time(8, 0)
        )
        assert overnight is True
        assert std is True
        assert dur == 12 * 60
        assert end.date().day == start.date().day + 1

    def test_exception_short(self):
        """Exceção real: 10:00–17:30 (7h30)"""
        from backend.services.import_service import _normalize_shift
        start, end, dur, overnight, std = _normalize_shift(
            date(2026, 3, 4), time(10, 0), time(17, 30)
        )
        assert overnight is False
        assert std is False
        assert dur == 7 * 60 + 30

    def test_exception_late_start(self):
        """Exceção real: 13:30–22:00"""
        from backend.services.import_service import _normalize_shift
        _, _, dur, overnight, std = _normalize_shift(
            date(2026, 3, 5), time(13, 30), time(22, 0)
        )
        assert overnight is False
        assert std is False
        assert dur == 8 * 60 + 30

    def test_exception_late_start_alt(self):
        """Exceção real: 11:00–22:00"""
        from backend.services.import_service import _normalize_shift
        _, _, dur, overnight, std = _normalize_shift(
            date(2026, 3, 7), time(11, 0), time(22, 0)
        )
        assert overnight is False
        assert std is False
        assert dur == 11 * 60


class TestDetectDuplicatesAndOverlaps:
    def _make_row(self, row_num, agent_id, start, end):
        from datetime import datetime
        from backend.models import RowStatus
        return {
            "row_number": row_num,
            "agent_id": agent_id,
            "normalized_start": datetime.combine(date(2026, 3, 1), start),
            "normalized_end": datetime.combine(date(2026, 3, 1) if end > start else date(2026, 3, 2), end),
            "row_status": RowStatus.VALID,
            "issues": None,
            "is_duplicate": False,
            "has_overlap": False,
        }

    def test_exact_duplicate_flagged(self):
        from backend.services.import_service import _detect_duplicates_and_overlaps
        rows = [
            self._make_row(2, 1, time(8, 0), time(20, 0)),
            self._make_row(3, 1, time(8, 0), time(20, 0)),
        ]
        result = _detect_duplicates_and_overlaps(rows)
        assert result[1]["is_duplicate"] is True
        assert result[0]["is_duplicate"] is False

    def test_overlap_flagged(self):
        from backend.services.import_service import _detect_duplicates_and_overlaps
        from backend.models import RowStatus
        rows = [
            self._make_row(2, 1, time(8, 0), time(20, 0)),
            self._make_row(3, 1, time(10, 0), time(22, 0)),   # overlaps with row above
        ]
        result = _detect_duplicates_and_overlaps(rows)
        assert result[0]["has_overlap"] is True
        assert result[1]["has_overlap"] is True

    def test_no_overlap_different_agents(self):
        from backend.services.import_service import _detect_duplicates_and_overlaps
        rows = [
            self._make_row(2, 1, time(8, 0), time(20, 0)),
            self._make_row(3, 2, time(8, 0), time(20, 0)),   # same time, different agent
        ]
        result = _detect_duplicates_and_overlaps(rows)
        assert result[0]["has_overlap"] is False
        assert result[1]["has_overlap"] is False


# ─── Testes de integração via API ─────────────────────────────────────────────

def _csv_upload(client, headers, csv_path: Path, period="2026-03"):
    with open(csv_path, "rb") as f:
        return client.post(
            "/schedule-imports/",
            headers=headers,
            files={"file": (csv_path.name, f, "text/csv")},
            data={"reference_period": period},
        )


def test_import_endpoint_requires_auth(client):
    csv_path = FIXTURES / "escala_exemplo.csv"
    with open(csv_path, "rb") as f:
        resp = client.post(
            "/schedule-imports/",
            files={"file": ("escala_exemplo.csv", f, "text/csv")},
            data={"reference_period": "2026-03"},
        )
    assert resp.status_code == 401


def test_import_endpoint_requires_admin(client, agent_headers):
    csv_path = FIXTURES / "escala_exemplo.csv"
    with open(csv_path, "rb") as f:
        resp = client.post(
            "/schedule-imports/",
            headers=agent_headers,
            files={"file": ("escala_exemplo.csv", f, "text/csv")},
            data={"reference_period": "2026-03"},
        )
    assert resp.status_code == 403


def test_import_valid_csv(client, admin_headers):
    resp = _csv_upload(client, admin_headers, FIXTURES / "escala_exemplo.csv")
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["total_rows"] == 10
    assert data["invalid_rows"] == 0
    assert data["importable_rows"] > 0
    assert data["confirmed"] is False


def test_import_csv_with_errors(client, admin_headers):
    resp = _csv_upload(client, admin_headers, FIXTURES / "escala_com_erros.csv")
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["total_rows"] == 10
    # Linhas com data inválida e hora inválida devem ser INVALID
    assert data["invalid_rows"] >= 2
    # Duplicata deve ser detectada
    assert data["duplicate_rows"] >= 1
    # Divergência de horas deve gerar WARNING
    assert data["warning_rows"] >= 1


def test_list_imports(client, admin_headers):
    _csv_upload(client, admin_headers, FIXTURES / "escala_exemplo.csv")
    resp = client.get("/schedule-imports/", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_import_summary(client, admin_headers):
    upload = _csv_upload(client, admin_headers, FIXTURES / "escala_exemplo.csv")
    import_id = upload.json()["import_id"]

    resp = client.get(f"/schedule-imports/{import_id}/summary", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["import_id"] == import_id


def test_get_import_rows_filter(client, admin_headers):
    upload = _csv_upload(client, admin_headers, FIXTURES / "escala_com_erros.csv")
    import_id = upload.json()["import_id"]

    resp = client.get(f"/schedule-imports/{import_id}/rows?row_status=invalid", headers=admin_headers)
    assert resp.status_code == 200
    rows = resp.json()
    assert all(r["row_status"] == "invalid" for r in rows)


def test_confirm_import_creates_shifts(client, admin_headers):
    upload = _csv_upload(client, admin_headers, FIXTURES / "escala_exemplo.csv")
    import_id = upload.json()["import_id"]

    # Confirmar a importação
    resp = client.post(f"/schedule-imports/{import_id}/confirm", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["confirmed"] is True

    # Turnos devem ter sido criados
    shifts_resp = client.get("/shifts", headers=admin_headers)
    assert shifts_resp.status_code == 200
    # O conftest cria 3 shifts; agora devem existir mais
    assert len(shifts_resp.json()) > 3


def test_confirm_import_idempotent_error(client, admin_headers):
    """Segunda confirmação deve retornar 409."""
    upload = _csv_upload(client, admin_headers, FIXTURES / "escala_exemplo.csv")
    import_id = upload.json()["import_id"]
    client.post(f"/schedule-imports/{import_id}/confirm", headers=admin_headers)
    resp = client.post(f"/schedule-imports/{import_id}/confirm", headers=admin_headers)
    assert resp.status_code == 409


def test_export_issues_report(client, admin_headers):
    upload = _csv_upload(client, admin_headers, FIXTURES / "escala_com_erros.csv")
    import_id = upload.json()["import_id"]

    resp = client.get(f"/schedule-imports/{import_id}/report", headers=admin_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    content = resp.content.decode("utf-8-sig")
    assert "linha" in content.lower()


def test_existing_routes_unaffected(client, agent_headers, admin_headers):
    """Garante que as rotas existentes continuam funcionando após a adição do novo router."""
    assert client.get("/health").status_code == 200
    assert client.get("/shifts", headers=agent_headers).status_code == 200
    assert client.get("/shifts/export/excel", headers=agent_headers).status_code == 200
    assert client.get("/shifts/export/ics", headers=agent_headers).status_code == 200
    assert client.get("/users", headers=admin_headers).status_code == 200
