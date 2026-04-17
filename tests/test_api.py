from datetime import datetime, timedelta

from backend.config.database import SessionLocal
from backend.models import Shift, User, UserRole
from backend.utils.auth import get_password_hash


def test_healthcheck_is_public(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_login_and_protected_route_require_auth(client, admin_headers):
    unauthorized = client.get("/users")
    assert unauthorized.status_code == 401

    authorized = client.get("/users", headers=admin_headers)
    assert authorized.status_code == 200
    assert len(authorized.json()) == 3


def test_export_routes_keep_priority_over_param_routes(client, agent_headers):
    excel_response = client.get("/shifts/export/excel", headers=agent_headers)
    assert excel_response.status_code == 200
    assert "spreadsheetml" in excel_response.headers["content-type"]

    ics_response = client.get("/shifts/export/ics", headers=agent_headers)
    assert ics_response.status_code == 200
    assert "text/calendar" in ics_response.headers["content-type"]
    assert b"BEGIN:VCALENDAR" in ics_response.content


def test_swap_flow_requires_authenticated_requester_and_admin_approval(
    client,
    admin_headers,
    agent_headers,
):
    shifts_response = client.get("/shifts", headers=agent_headers)
    assert shifts_response.status_code == 200
    shifts = shifts_response.json()

    origin_shift = next(shift for shift in shifts if shift["agent"]["email"] == "alice@agentescala.com")
    target_shift = next(shift for shift in shifts if shift["agent"]["email"] == "bob@agentescala.com")

    create_swap_response = client.post(
        "/swaps/",
        headers=agent_headers,
        json={
            "target_agent_id": target_shift["agent_id"],
            "origin_shift_id": origin_shift["id"],
            "target_shift_id": target_shift["id"],
            "reason": "Troca para teste",
        },
    )
    assert create_swap_response.status_code == 201
    swap = create_swap_response.json()
    assert swap["requester_id"] == origin_shift["agent_id"]

    forbidden_approve = client.post(
        f"/swaps/{swap['id']}/approve",
        headers=agent_headers,
        json={"admin_notes": "nao permitido"},
    )
    assert forbidden_approve.status_code == 403

    approve_response = client.post(
        f"/swaps/{swap['id']}/approve",
        headers=admin_headers,
        json={"admin_notes": "aprovado em teste"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    updated_origin_shift = client.get(f"/shifts/{origin_shift['id']}", headers=agent_headers)
    updated_target_shift = client.get(f"/shifts/{target_shift['id']}", headers=admin_headers)

    assert updated_origin_shift.status_code == 200
    assert updated_target_shift.status_code == 200
    assert updated_origin_shift.json()["agent_id"] == target_shift["agent_id"]
    assert updated_target_shift.json()["agent_id"] == origin_shift["agent_id"]


def test_me_endpoints_return_authenticated_user_and_only_user_shifts(client, agent_headers):
    me_response = client.get("/me", headers=agent_headers)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "alice@agentescala.com"
    assert "avatar_url" in me_response.json()

    shifts_response = client.get("/me/shifts", headers=agent_headers)
    assert shifts_response.status_code == 200
    shift_agent_ids = {shift["agent_id"] for shift in shifts_response.json()}
    assert shift_agent_ids == {me_response.json()["id"]}


def test_me_shifts_export_ics_works(client, agent_headers):
    response = client.get("/me/shifts/export.ics", headers=agent_headers)
    assert response.status_code == 200
    assert "text/calendar" in response.headers["content-type"]
    assert b"BEGIN:VCALENDAR" in response.content


def test_me_shifts_does_not_use_ambiguous_legacy_name_fallback(client, agent_headers):
    db = SessionLocal()
    try:
        duplicate = User(
            email="alice2@agentescala.com",
            name="Alice Silva",
            hashed_password=get_password_hash("password123"),
            role=UserRole.AGENT,
            is_active=True,
        )
        db.add(duplicate)
        db.commit()
        db.refresh(duplicate)

        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        ambiguous_shift = Shift(
            agent_id=duplicate.id,
            user_id=None,
            legacy_agent_name="Alice Silva",
            start_time=now + timedelta(days=3, hours=8),
            end_time=now + timedelta(days=3, hours=16),
            title="Plantão legado ambíguo",
        )
        db.add(ambiguous_shift)
        db.commit()
    finally:
        db.close()

    response = client.get("/me/shifts", headers=agent_headers)
    assert response.status_code == 200
    titles = [shift["title"] for shift in response.json()]
    assert "Plantão legado ambíguo" not in titles


def test_me_shifts_considers_agent_reassignment_even_with_user_id_filled(
    client,
    admin_headers,
    agent_headers,
):
    bob_login = client.post(
        "/auth/login",
        json={"email": "bob@agentescala.com", "password": "password123"},
    )
    assert bob_login.status_code == 200
    bob_headers = {"Authorization": f"Bearer {bob_login.json()['access_token']}"}

    shifts_response = client.get("/shifts", headers=agent_headers)
    assert shifts_response.status_code == 200
    shifts = shifts_response.json()
    origin_shift = next(shift for shift in shifts if shift["agent"]["email"] == "alice@agentescala.com")
    target_shift = next(shift for shift in shifts if shift["agent"]["email"] == "bob@agentescala.com")

    create_swap_response = client.post(
        "/swaps/",
        headers=agent_headers,
        json={
            "target_agent_id": target_shift["agent_id"],
            "origin_shift_id": origin_shift["id"],
            "target_shift_id": target_shift["id"],
            "reason": "troca para validar /me/shifts",
        },
    )
    assert create_swap_response.status_code == 201
    swap_id = create_swap_response.json()["id"]

    approve_response = client.post(
        f"/swaps/{swap_id}/approve",
        headers=admin_headers,
        json={"admin_notes": "ok"},
    )
    assert approve_response.status_code == 200

    alice_me_shifts = client.get("/me/shifts", headers=agent_headers)
    bob_me_shifts = client.get("/me/shifts", headers=bob_headers)
    assert alice_me_shifts.status_code == 200
    assert bob_me_shifts.status_code == 200

    alice_shift_ids = {shift["id"] for shift in alice_me_shifts.json()}
    bob_shift_ids = {shift["id"] for shift in bob_me_shifts.json()}

    assert origin_shift["id"] not in alice_shift_ids
    assert origin_shift["id"] in bob_shift_ids


def test_me_shifts_invalid_month_returns_400(client, agent_headers):
    response = client.get("/me/shifts?month=2026-13", headers=agent_headers)
    assert response.status_code == 400
    assert "Mês inválido" in response.json()["detail"]


def test_me_profile_update_and_avatar_upload(client, agent_headers):
    update_payload = {
        "name": "Alice Silva Atualizada",
        "phone": "+55 11 99999-1111",
        "specialty": "Cardiologia",
        "profile_notes": "Perfil atualizado em teste.",
    }
    update_response = client.put("/me", headers=agent_headers, json=update_payload)
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["name"] == update_payload["name"]
    assert data["phone"] == update_payload["phone"]
    assert data["specialty"] == update_payload["specialty"]

    fake_png = b"\\x89PNG\\r\\n\\x1a\\n" + b"0" * 64
    avatar_response = client.post(
        "/me/avatar",
        headers=agent_headers,
        files={"file": ("avatar.png", fake_png, "image/png")},
    )
    assert avatar_response.status_code == 200
    assert avatar_response.json()["avatar_url"].startswith("/media/avatars/")

    refreshed = client.get("/me", headers=agent_headers)
    assert refreshed.status_code == 200
    assert refreshed.json()["avatar_url"] is not None
