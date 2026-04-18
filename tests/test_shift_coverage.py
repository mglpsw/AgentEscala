from datetime import datetime, timedelta


def _first_agent_id(client, admin_headers):
    resp = client.get('/users/agents', headers=admin_headers)
    assert resp.status_code == 200
    return resp.json()[0]['id']


def _create_agent(client, admin_headers, idx):
    resp = client.post(
        '/admin/users',
        headers=admin_headers,
        json={
            'email': f'agente{idx}@agentescala.com',
            'name': f'Agente {idx}',
            'password': 'CHANGE_ME_TEST_PASSWORD',
            'role': 'medico',
            'is_active': True,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()['id']


def test_coverage_flags_endpoint_returns_daily_flags(client, admin_headers):
    today = datetime.utcnow().date().isoformat()
    resp = client.get('/shifts/coverage/flags', headers=admin_headers, params={'start_date': today, 'end_date': today})
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 1
    assert payload[0]['date'] == today
    assert 'complete' in payload[0]
    assert 'missing' in payload[0]


def test_coverage_flags_marks_complete_when_required_shifts_exist(client, admin_headers):
    agent_ids = [
        _first_agent_id(client, admin_headers),
        _create_agent(client, admin_headers, 2),
        _create_agent(client, admin_headers, 3),
        _create_agent(client, admin_headers, 4),
    ]
    base_day = datetime.utcnow().date() + timedelta(days=5)
    day = base_day.isoformat()
    next_day = (base_day + timedelta(days=1)).isoformat()

    shifts = [
        (agent_ids[0], '12H DIA', f'{day}T08:00:00', f'{day}T20:00:00'),
        (agent_ids[1], '12H DIA', f'{day}T08:00:00', f'{day}T20:00:00'),
        (agent_ids[2], '10-22H', f'{day}T10:00:00', f'{day}T22:00:00'),
        (agent_ids[3], '12H NOITE', f'{day}T20:00:00', f'{next_day}T08:00:00'),
    ]

    for agent_id, title, start_time, end_time in shifts:
        create_resp = client.post(
            '/shifts/',
            headers=admin_headers,
            json={
                'agent_id': agent_id,
                'user_id': agent_id,
                'title': title,
                'start_time': start_time,
                'end_time': end_time,
            },
        )
        assert create_resp.status_code == 201, create_resp.text

    coverage = client.get(
        '/shifts/coverage/flags',
        headers=admin_headers,
        params={'start_date': day, 'end_date': day},
    )
    assert coverage.status_code == 200
    item = coverage.json()[0]
    assert item['complete'] is True
    assert item['missing']['12H DIA'] == 0
    assert item['missing']['10-22H'] == 0
    assert item['missing']['12H NOITE'] == 0
