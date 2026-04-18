from datetime import datetime, timedelta

from backend.config.database import SessionLocal
from backend.models import Shift, User


def _payload(user_id: int, **overrides):
    base = {
        "user_id": user_id,
        "weekday": 0,
        "shift_label": "12H DIA",
        "start_time": "08:00",
        "end_time": "20:00",
        "start_date": "2026-04-01",
        "months_ahead": 2,
        "notes": "recorrencia teste",
    }
    base.update(overrides)
    return base


def test_recurring_preview_does_not_create_shifts(client, admin_headers):
    db = SessionLocal()
    alice = db.query(User).filter(User.email == "alice@agentescala.com").first()
    before = db.query(Shift).filter(Shift.agent_id == alice.id).count()

    response = client.post("/admin/recurring-shifts/preview", headers=admin_headers, json=_payload(alice.id))
    assert response.status_code == 200
    data = response.json()
    assert data["total_generated"] > 0

    after = db.query(Shift).filter(Shift.agent_id == alice.id).count()
    assert after == before
    db.close()


def test_recurring_preview_caps_months_to_six(client, admin_headers):
    db = SessionLocal()
    alice = db.query(User).filter(User.email == "alice@agentescala.com").first()

    response = client.post(
        "/admin/recurring-shifts/preview",
        headers=admin_headers,
        json=_payload(alice.id, months_ahead=6),
    )
    assert response.status_code == 200
    data = response.json()
    start = datetime.fromisoformat(f"{data['interval_start']}T00:00:00")
    end = datetime.fromisoformat(f"{data['interval_end']}T00:00:00")
    assert (end - start).days <= 186
    db.close()


def test_recurring_night_shift_crosses_day(client, admin_headers):
    db = SessionLocal()
    alice = db.query(User).filter(User.email == "alice@agentescala.com").first()

    response = client.post(
        "/admin/recurring-shifts/preview",
        headers=admin_headers,
        json=_payload(alice.id, shift_label="12H NOITE", start_time="20:00", end_time="08:00"),
    )
    assert response.status_code == 200
    item = response.json()["items"][0]
    start_dt = datetime.fromisoformat(item["start_datetime"])
    end_dt = datetime.fromisoformat(item["end_datetime"])
    assert end_dt.date() >= (start_dt + timedelta(days=1)).date()
    assert item["duration_hours"] == 12.0
    db.close()


def test_recurring_detects_duplicate_and_conflict(client, admin_headers):
    db = SessionLocal()
    alice = db.query(User).filter(User.email == "alice@agentescala.com").first()

    # cria um turno exatamente igual ao esperado para segunda-feira 2026-04-06
    shift = Shift(
        agent_id=alice.id,
        user_id=alice.id,
        start_time=datetime.fromisoformat("2026-04-06T08:00:00"),
        end_time=datetime.fromisoformat("2026-04-06T20:00:00"),
        title="12H DIA",
    )
    conflict = Shift(
        agent_id=alice.id,
        user_id=alice.id,
        start_time=datetime.fromisoformat("2026-04-13T09:00:00"),
        end_time=datetime.fromisoformat("2026-04-13T12:00:00"),
        title="Conflito",
    )
    db.add_all([shift, conflict])
    db.commit()

    response = client.post("/admin/recurring-shifts/preview", headers=admin_headers, json=_payload(alice.id, months_ahead=1))
    assert response.status_code == 200
    data = response.json()
    assert data["total_duplicates"] >= 1
    assert data["total_conflicts"] >= 1
    db.close()


def test_recurring_confirm_creates_batch(client, admin_headers):
    db = SessionLocal()
    bob = db.query(User).filter(User.email == "bob@agentescala.com").first()

    preview_resp = client.post("/admin/recurring-shifts/preview", headers=admin_headers, json=_payload(bob.id, months_ahead=1))
    assert preview_resp.status_code == 200
    batch_id = preview_resp.json()["batch_id"]

    before = db.query(Shift).filter(Shift.agent_id == bob.id).count()
    confirm_resp = client.post(
        "/admin/recurring-shifts/confirm",
        headers=admin_headers,
        json={**_payload(bob.id, months_ahead=1), "batch_id": batch_id},
    )
    assert confirm_resp.status_code == 200
    result = confirm_resp.json()
    assert result["total_created"] >= 1

    after = db.query(Shift).filter(Shift.agent_id == bob.id).count()
    assert after > before

    list_resp = client.get("/admin/recurring-shifts", headers=admin_headers)
    assert list_resp.status_code == 200
    assert any(item["batch_id"] == batch_id for item in list_resp.json())

    get_resp = client.get(f"/admin/recurring-shifts/{batch_id}", headers=admin_headers)
    assert get_resp.status_code == 200

    shifts_resp = client.get(
        f"/shifts/agent/{bob.id}",
        headers=admin_headers,
        params={"start_date": "2026-04-01", "end_date": "2026-10-01"},
    )
    assert shifts_resp.status_code == 200
    assert len(shifts_resp.json()) >= after
    db.close()


def test_document_import_route_still_works(client, admin_headers):
    payload = {
        "source_filename": "compat.json",
        "payload": {
            "pages": [{"page_number": 1, "tables": [{"title": "MARÇO/2026", "headers": ["Profissional", "Data", "Entrada", "Saída"], "rows": [["Alice Silva", "01/03/2026", "08:00", "20:00"]]}]}]
        },
    }
    response = client.post("/admin/imports/parse-ocr-payload", headers=admin_headers, json=payload)
    assert response.status_code == 201
