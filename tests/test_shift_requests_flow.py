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

    shifts = client.get('/shifts', headers=alice_headers).json()
    bob_shift = next(item for item in shifts if item['agent']['email'] == 'bob@agentescala.com')
    requested_date = bob_shift['start_time'][:10]

    create = client.post(
        '/shift-requests/',
        headers=alice_headers,
        json={
            'requested_date': requested_date,
            'shift_period': '12H NOITE',
            'note': 'Quero cobrir este turno',
            'target_shift_id': bob_shift['id'],
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
