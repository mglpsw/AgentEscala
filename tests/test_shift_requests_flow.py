from datetime import date, datetime, time, timedelta

from backend.config.database import SessionLocal
from backend.models import Shift, User, UserRole
from backend.utils.auth import get_password_hash
from datetime import date, timedelta


def _login(client, email):
    response = client.post('/auth/login', json={'email': email, 'password': 'CHANGE_ME_TEST_PASSWORD'})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def test_day_config_returns_dynamic_slots(client, agent_headers):
    today = date.today()
    response = client.get(
        '/shifts/day-config',
        headers=agent_headers,
        params={'start_date': today.isoformat(), 'end_date': (today + timedelta(days=2)).isoformat()},
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert 'date' in payload[0]
    assert 'slots' in payload[0]


def test_shift_request_flow_target_user_then_admin(client, admin_headers):
    alice_headers = _login(client, 'alice@agentescala.com')
    bob_headers = _login(client, 'bob@agentescala.com')

    db = SessionLocal()
    try:
        bob = db.query(User).filter(User.email == "bob@agentescala.com").first()
        assert bob is not None
        requested_date_obj = date.today() + timedelta(days=4)
        bob_shift = Shift(
            agent_id=bob.id,
            user_id=bob.id,
            start_time=datetime.combine(requested_date_obj, time(20, 0)),
            end_time=datetime.combine(requested_date_obj + timedelta(days=1), time(8, 0)),
            title="Turno Bob Noite",
            description="Turno de referência para troca",
            location="Hospital",
        )
        db.add(bob_shift)
        db.commit()
        db.refresh(bob_shift)
        requested_date = requested_date_obj.isoformat()
        target_shift_id = bob_shift.id
    finally:
        db.close()
    create = client.post(
        '/shift-requests/',
        headers=alice_headers,
        json={
            'requested_date': requested_date,
            'shift_period': '12H NOITE',
            'note': 'Quero cobrir este turno',
            'target_shift_id': target_shift_id,
        },
    )
    assert create.status_code == 201
    request_id = create.json()['id']

    target_accept = client.post(
        f'/shift-requests/{request_id}/respond',
        headers=bob_headers,
        json={'accept': True, 'note': 'pode assumir'},
    )
    assert target_accept.status_code == 200
    assert target_accept.json()['status'] == 'pending_admin'

    admin_approve = client.post(
        f'/shift-requests/{request_id}/admin-review',
        headers=admin_headers,
        json={'approve': True, 'admin_notes': 'aprovado em teste'},
    )
    assert admin_approve.status_code == 200
    assert admin_approve.json()['status'] == 'approved'


def test_only_target_user_can_respond_shift_request(client):
    alice_headers = _login(client, 'alice@agentescala.com')

    requested_date = (date.today() + timedelta(days=1)).isoformat()
    create = client.post(
        '/shift-requests/',
        headers=alice_headers,
        json={'requested_date': requested_date, 'shift_period': '12H NOITE'},
    )
    request_id = create.json()['id']

    denied = client.post(
        f'/shift-requests/{request_id}/respond',
        headers=alice_headers,
        json={'accept': True},
    )
    assert denied.status_code == 400
    assert 'usuário alvo' in denied.json()['detail']


def test_legacy_admin_can_list_and_review_shift_requests(client):
    db = SessionLocal()
    try:
        legacy_admin = User(
            email="legacy.admin@agentescala.com",
            name="Legacy Admin",
            hashed_password=get_password_hash("CHANGE_ME_TEST_PASSWORD"),
            role=UserRole.AGENT,
            is_admin=True,
            is_active=True,
        )
        db.add(legacy_admin)
        db.commit()
    finally:
        db.close()

    legacy_admin_headers = _login(client, "legacy.admin@agentescala.com")
    alice_headers = _login(client, "alice@agentescala.com")

    requested_date = (date.today() + timedelta(days=3)).isoformat()
    created = client.post(
        "/shift-requests/",
        headers=alice_headers,
        json={"requested_date": requested_date, "shift_period": "12H NOITE"},
    )
    assert created.status_code == 201
    request_id = created.json()["id"]

    listed = client.get("/shift-requests/", headers=legacy_admin_headers)
    assert listed.status_code == 200
    assert any(item["id"] == request_id for item in listed.json())

    reviewed = client.post(
        f"/shift-requests/{request_id}/admin-review",
        headers=legacy_admin_headers,
        json={"approve": True, "admin_notes": "legacy admin aprovou"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "approved"


def test_shift_request_rejects_mismatched_target_shift(client):
    alice_headers = _login(client, "alice@agentescala.com")

    db = SessionLocal()
    try:
        bob_shift = (
            db.query(Shift)
            .join(User, Shift.agent_id == User.id)
            .filter(User.email == "bob@agentescala.com")
            .first()
        )
        assert bob_shift is not None
        target_shift_id = bob_shift.id
    finally:
        db.close()

    mismatch_date = (date.today() + timedelta(days=10)).isoformat()
    created = client.post(
        "/shift-requests/",
        headers=alice_headers,
        json={
            "requested_date": mismatch_date,
            "shift_period": "12H NOITE",
            "target_shift_id": target_shift_id,
        },
    )
    assert created.status_code == 400
    assert "não corresponde à data/período" in created.json()["detail"]
