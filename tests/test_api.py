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

    shifts_response = client.get("/me/shifts", headers=agent_headers)
    assert shifts_response.status_code == 200
    shift_agent_ids = {shift["agent_id"] for shift in shifts_response.json()}
    assert shift_agent_ids == {me_response.json()["id"]}


def test_me_shifts_export_ics_works(client, agent_headers):
    response = client.get("/me/shifts/export.ics", headers=agent_headers)
    assert response.status_code == 200
    assert "text/calendar" in response.headers["content-type"]
    assert b"BEGIN:VCALENDAR" in response.content
